import os
from pathlib import Path

from application.run_issue_flow import IssueFlowConfig
from infrastructure.http.schemas import RunWorkflowRequest


WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"


def build_issue_flow_config_from_request(
    payload: RunWorkflowRequest,
    *,
    repository_directory: Path = REPODIR,
) -> IssueFlowConfig:
    github_token = os.getenv("GITHUB_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if not github_token:
        raise RuntimeError("Missing required environment variable: GITHUB_TOKEN")
    if not openai_api_key:
        raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")

    return IssueFlowConfig(
        issue_number=payload.issue_number,
        repository_owner=payload.owner,
        repository_name=payload.repo,
        github_token=github_token,
        base_branch=payload.base_branch,
        repository_directory=repository_directory,
        dry_run=payload.dry_run,
    )
