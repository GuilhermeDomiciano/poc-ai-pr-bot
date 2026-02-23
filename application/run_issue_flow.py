from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class IssueFlowConfig:
    issue_number: int
    repository_owner: str
    repository_name: str
    github_token: str
    base_branch: str
    repository_directory: Path
    dry_run: bool = False


@dataclass(frozen=True)
class IssueFlowDependencies:
    get_issue: Callable[[int], dict[str, Any]]
    create_pr: Callable[..., dict[str, Any]]
    clone_repo: Callable[[str, str, str, Path], None]
    git_setup: Callable[[Path], None]
    repo_tree_summary: Callable[[Path], str]
    run_crew: Callable[[str, str, str], str]
    parse_payload: Callable[[str], Any]
    apply_files: Callable[[Path, dict[str, str]], None]
    run_command: Callable[..., None]
    remote_branch_exists: Callable[[str, Path], bool]


@dataclass(frozen=True)
class IssueFlowResult:
    status: str
    message: str
    branch: str | None = None
    commit: str | None = None
    pr_title: str | None = None
    pr_url: str | None = None
    error: str | None = None


def run_issue_flow(
    config: IssueFlowConfig,
    dependencies: IssueFlowDependencies,
    *,
    raise_on_error: bool = True,
) -> IssueFlowResult:
    try:
        issue_data = dependencies.get_issue(config.issue_number)
        issue_title = issue_data["title"]
        issue_body = issue_data.get("body") or ""

        dependencies.clone_repo(
            config.repository_owner,
            config.repository_name,
            config.github_token,
            config.repository_directory,
        )
        dependencies.git_setup(config.repository_directory)

        repository_tree_summary = dependencies.repo_tree_summary(config.repository_directory)
        crew_output_text = dependencies.run_crew(issue_title, issue_body, repository_tree_summary)
        change_set = dependencies.parse_payload(crew_output_text)

        if config.dry_run:
            return IssueFlowResult(
                status="dry_run",
                message="Dry run completed with no repository or PR changes",
                branch=change_set.branch,
                commit=change_set.commit,
                pr_title=change_set.pr_title,
                pr_url=None,
            )

        dependencies.apply_files(config.repository_directory, change_set.files)

        dependencies.run_command(["git", "checkout", "-b", change_set.branch], cwd=config.repository_directory)
        dependencies.run_command(["git", "add", "."], cwd=config.repository_directory)
        dependencies.run_command(["git", "commit", "-m", change_set.commit], cwd=config.repository_directory)
        dependencies.run_command(["git", "push", "-u", "origin", change_set.branch], cwd=config.repository_directory)

        if not dependencies.remote_branch_exists(config.base_branch, config.repository_directory):
            print(
                f"Base branch '{config.base_branch}' does not exist on remote. "
                "Skipping PR creation (common for empty/new repositories)."
            )
            print(f"Branch pushed successfully: {change_set.branch}")
            return IssueFlowResult(
                status="success",
                branch=change_set.branch,
                commit=change_set.commit,
                pr_title=change_set.pr_title,
                pr_url=None,
                message=f"Branch pushed successfully: {change_set.branch}",
            )

        pull_request = dependencies.create_pr(
            head=change_set.branch,
            base=config.base_branch,
            title=change_set.pr_title,
            body=change_set.pr_body,
        )
        print("PR created:", pull_request["html_url"])
        return IssueFlowResult(
            status="success",
            branch=change_set.branch,
            commit=change_set.commit,
            pr_title=change_set.pr_title,
            pr_url=pull_request["html_url"],
            message="PR created successfully",
        )
    except Exception as error:
        if raise_on_error:
            raise
        return IssueFlowResult(
            status="error",
            message="Issue flow execution failed",
            error=str(error),
        )
