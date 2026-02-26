import json
import tempfile
import unittest
from pathlib import Path

from application.run_issue_flow import IssueFlowConfig, IssueFlowDependencies, run_issue_flow
from domain.payload_parser import parse_payload
from infrastructure.observability.workflow_observer import classify_change_scope


def _crew_output_for_files(files_map: dict[str, str]) -> str:
    payload = {
        "files": files_map,
        "branch": "feature/integration-test",
        "commit": "feat(test): integration coverage",
        "pr_title": "Integration Test",
        "pr_body": "Testing run_issue_flow integration",
    }
    return json.dumps(payload)


class RunIssueFlowIntegrationTests(unittest.TestCase):
    def _run_scenario(self, files_map: dict[str, str]) -> tuple[str, str]:
        observed_scopes: list[str] = []
        with tempfile.TemporaryDirectory() as tmp_directory:
            repository_directory = Path(tmp_directory) / "repo"

            def clone_repo(_: str, __: str, repo_dir: Path) -> None:
                repo_dir.mkdir(parents=True, exist_ok=True)

            def git_setup(_: Path) -> None:
                return None

            def repo_tree_summary(_: Path) -> str:
                return ""

            def run_crew(_: str, __: str, ___: str) -> str:
                return _crew_output_for_files(files_map)

            def apply_files(_: Path, __: dict[str, str]) -> None:
                return None

            def publish_changes(_: Path, __: str, ___: str) -> None:
                return None

            def observe_change_set(change_set) -> None:
                observed_scopes.append(classify_change_scope(change_set.files))

            dependencies = IssueFlowDependencies(
                get_issue=lambda _: {"title": "Issue", "body": "Body"},
                create_pr=lambda **_: {"html_url": "https://example.com/pull/1"},
                clone_repo=clone_repo,
                git_setup=git_setup,
                repo_tree_summary=repo_tree_summary,
                run_crew=run_crew,
                parse_payload=parse_payload,
                apply_files=apply_files,
                publish_changes=publish_changes,
                remote_branch_exists=lambda *_: False,
                observe_change_set=observe_change_set,
            )

            config = IssueFlowConfig(
                issue_number=1,
                repository_owner="owner",
                repository_name="repo",
                base_branch="main",
                repository_directory=repository_directory,
                dry_run=False,
            )

            result = run_issue_flow(config, dependencies, raise_on_error=False)

        self.assertEqual(result.status, "success")
        self.assertTrue(observed_scopes)
        return result.message, observed_scopes[0]

    def test_integration_with_backend_only_changes(self) -> None:
        message, scope = self._run_scenario({"backend/app/service.py": "print('ok')"})
        self.assertIn("Branch pushed successfully", message)
        self.assertEqual(scope, "backend_only")

    def test_integration_with_frontend_only_changes(self) -> None:
        message, scope = self._run_scenario({"frontend/src/App.tsx": "export default function App() { return null }"})
        self.assertIn("Branch pushed successfully", message)
        self.assertEqual(scope, "frontend_only")

    def test_integration_with_fullstack_changes(self) -> None:
        message, scope = self._run_scenario(
            {
                "backend/app/api.py": "def run():\n    return 'ok'\n",
                "frontend/src/api.ts": "export const run = () => fetch('/workflow/run');",
            }
        )
        self.assertIn("Branch pushed successfully", message)
        self.assertEqual(scope, "fullstack")


if __name__ == "__main__":
    unittest.main()
