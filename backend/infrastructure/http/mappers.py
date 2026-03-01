from pathlib import Path

from application.issue_flow import IssueFlowConfig, IssueFlowResult
from infrastructure.http.schemas import RunWorkflowRequest, RunWorkflowResponse


def to_issue_flow_config(
    payload: RunWorkflowRequest,
    *,
    repository_directory: Path,
) -> IssueFlowConfig:
    return IssueFlowConfig(
        issue_number=payload.issue_number,
        repository_owner=payload.owner,
        repository_name=payload.repo,
        base_branch=payload.base_branch,
        repository_directory=repository_directory,
        dry_run=payload.dry_run,
    )


def to_run_workflow_response(result: IssueFlowResult) -> RunWorkflowResponse:
    return RunWorkflowResponse(
        status=result.status,
        message=result.message,
        branch=result.branch,
        commit=result.commit,
        pr_title=result.pr_title,
        pr_url=result.pr_url,
    )
