import logging
import os
from functools import partial
from pathlib import Path
from dotenv import load_dotenv
from application.issue_flow import (
    IssueFlowConfig,
    IssueFlowDependencies,
    run_issue_flow,
)
from infrastructure.github.github_client import GitHubClient
from infrastructure.ai.crew_runner import run_crew
from domain.payload import parse_payload
from infrastructure.repo.file_writer import apply_files
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    publish_changes,
    remote_branch_exists,
    repo_tree_summary,
)
from infrastructure.observability.logging_utils import (
    configure_logging,
    log_event,
    register_sensitive_values,
)
from infrastructure.observability.workflow_observer import (
    is_contract_violation_error,
    log_contract_violation,
    observe_generated_change_set,
    observe_workflow_step,
)


load_dotenv()
configure_logging()
logger = logging.getLogger(__name__)

WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    log_event(logger, logging.INFO, "cli.workflow.start")
    github_token = required_env("GITHUB_TOKEN")
    openai_api_key = required_env("OPENAI_API_KEY")
    owner = required_env("GH_OWNER")
    repo = required_env("GH_REPO")
    issue_number = int(required_env("ISSUE_NUMBER"))
    git_author_name = os.getenv("GIT_AUTHOR_NAME", "AI Bot")
    git_author_email = os.getenv("GIT_AUTHOR_EMAIL", "ai-bot@example.com")
    register_sensitive_values(github_token, openai_api_key)

    github_client = GitHubClient(token=github_token, owner=owner, repo=repo)
    flow_config = IssueFlowConfig(
        issue_number=issue_number,
        repository_owner=owner,
        repository_name=repo,
        base_branch=os.getenv("GH_BASE_BRANCH", "main"),
        repository_directory=REPODIR,
        dry_run=False,
    )

    flow_dependencies = IssueFlowDependencies(
        get_issue=github_client.get_issue,
        create_pr=github_client.create_pr,
        clone_repo=partial(clone_repo, github_token=github_token),
        git_setup=partial(
            git_setup,
            git_author_name=git_author_name,
            git_author_email=git_author_email,
        ),
        repo_tree_summary=repo_tree_summary,
        run_crew=run_crew,
        parse_payload=parse_payload,
        apply_files=apply_files,
        publish_changes=publish_changes,
        remote_branch_exists=remote_branch_exists,
        observe_change_set=observe_generated_change_set,
        observe_step=observe_workflow_step,
    )
    try:
        result = run_issue_flow(flow_config, flow_dependencies)
    except Exception as error:
        error_message = str(error)
        if is_contract_violation_error(error_message):
            log_contract_violation(error_message)
        log_event(logger, logging.ERROR, "cli.workflow.failed", error=error_message)
        raise

    log_event(logger, logging.INFO, "cli.workflow.end", status=result.status, message=result.message)

if __name__ == "__main__":
    main()
