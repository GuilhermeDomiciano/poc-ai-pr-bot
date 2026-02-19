import os, re
from pathlib import Path
from dotenv import load_dotenv
from application.run_issue_flow import (
    IssueFlowConfig,
    IssueFlowDependencies,
    run_issue_flow,
)
from infrastructure.github.github_client import GitHubClient
from infrastructure.ai.crew_runner import run_crew
from domain.payload_parser import parse_payload
from infrastructure.repo.file_writer import apply_files
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    remote_branch_exists,
    repo_tree_summary,
    run,
)


load_dotenv()

WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"

def safe_slug(text: str) -> str:
    normalized_text = text.lower()
    normalized_text = re.sub(r"[^a-z0-9]+", "-", normalized_text).strip("-")
    return normalized_text[:50] or "change"

def main():
    github_client = GitHubClient()
    flow_config = IssueFlowConfig(
        issue_number=int(os.environ["ISSUE_NUMBER"]),
        repository_owner=os.environ["GH_OWNER"],
        repository_name=os.environ["GH_REPO"],
        github_token=os.environ["GITHUB_TOKEN"],
        base_branch=os.getenv("GH_BASE_BRANCH", "main"),
        repository_directory=REPODIR,
    )

    flow_dependencies = IssueFlowDependencies(
        github_client=github_client,
        clone_repo=clone_repo,
        git_setup=git_setup,
        repo_tree_summary=repo_tree_summary,
        run_crew=run_crew,
        parse_payload=parse_payload,
        apply_files=apply_files,
        run_command=run,
        remote_branch_exists=remote_branch_exists,
    )

    run_issue_flow(flow_config, flow_dependencies)

if __name__ == "__main__":
    main()
