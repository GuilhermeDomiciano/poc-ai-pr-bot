import logging
import os
from functools import partial
from pathlib import Path

from application.issue_flow import IssueFlowConfig, IssueFlowDependencies
from domain.payload import parse_payload
from infrastructure.ai.provider_factory import build_ai_provider_runtime_from_env
from infrastructure.github.github_client import GitHubClient
from infrastructure.http.mappers import to_issue_flow_config
from infrastructure.http.schemas import RunWorkflowRequest
from infrastructure.observability.logging_utils import log_event, register_sensitive_values
from infrastructure.observability.workflow_observer import (
    observe_generated_change_set,
    observe_workflow_step,
)
from infrastructure.repo.file_writer import apply_files
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    publish_changes,
    remote_branch_exists,
    repo_tree_summary,
)


WORKDIR = Path("/work")
REPODIR = WORKDIR / "repo"
logger = logging.getLogger(__name__)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _build_github_client(payload: RunWorkflowRequest) -> GitHubClient:
    return GitHubClient(
        token=_required_env("GITHUB_TOKEN"),
        owner=payload.owner,
        repo=payload.repo,
    )


def build_issue_flow_config_from_request(
    payload: RunWorkflowRequest,
    *,
    repository_directory: Path = REPODIR,
) -> IssueFlowConfig:
    return to_issue_flow_config(payload, repository_directory=repository_directory)


def build_issue_flow_dependencies(payload: RunWorkflowRequest) -> IssueFlowDependencies:
    github_token = _required_env("GITHUB_TOKEN")
    ai_runtime = build_ai_provider_runtime_from_env()
    register_sensitive_values(github_token, ai_runtime.api_key)
    log_event(
        logger,
        logging.INFO,
        "workflow.ai.provider.selected",
        provider=ai_runtime.provider,
        model=ai_runtime.model,
    )

    git_author_name = os.getenv("GIT_AUTHOR_NAME", "AI Bot")
    git_author_email = os.getenv("GIT_AUTHOR_EMAIL", "ai-bot@example.com")
    github_client = _build_github_client(payload)
    return IssueFlowDependencies(
        get_issue=github_client.get_issue,
        create_pr=github_client.create_pr,
        clone_repo=partial(clone_repo, github_token=github_token),
        git_setup=partial(
            git_setup,
            git_author_name=git_author_name,
            git_author_email=git_author_email,
        ),
        repo_tree_summary=repo_tree_summary,
        ai_provider=ai_runtime.adapter,
        parse_payload=parse_payload,
        apply_files=apply_files,
        publish_changes=publish_changes,
        remote_branch_exists=remote_branch_exists,
        observe_change_set=observe_generated_change_set,
        observe_step=observe_workflow_step,
    )
