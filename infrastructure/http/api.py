from fastapi import FastAPI, HTTPException, status

from application.run_issue_flow import IssueFlowDependencies, run_issue_flow
from domain.payload_parser import parse_payload
from infrastructure.ai.crew_runner import run_crew
from infrastructure.github.github_client import GitHubClient
from infrastructure.http.factories import build_issue_flow_config_from_request
from infrastructure.http.schemas import RunWorkflowRequest, RunWorkflowResponse
from infrastructure.repo.file_writer import apply_files
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    remote_branch_exists,
    repo_tree_summary,
    run,
)


app = FastAPI(title="POC AI PR Bot API")


def _build_dependencies() -> IssueFlowDependencies:
    github_client = GitHubClient()
    return IssueFlowDependencies(
        get_issue=github_client.get_issue,
        create_pr=github_client.create_pr,
        clone_repo=clone_repo,
        git_setup=git_setup,
        repo_tree_summary=repo_tree_summary,
        run_crew=run_crew,
        parse_payload=parse_payload,
        apply_files=apply_files,
        run_command=run,
        remote_branch_exists=remote_branch_exists,
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/workflow/run", response_model=RunWorkflowResponse, status_code=status.HTTP_200_OK)
def run_workflow(payload: RunWorkflowRequest) -> RunWorkflowResponse:
    try:
        flow_config = build_issue_flow_config_from_request(payload)
        flow_dependencies = _build_dependencies()
        result = run_issue_flow(
            flow_config,
            flow_dependencies,
            raise_on_error=False,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while executing workflow",
        )

    if result.status == "error":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while executing workflow",
        )

    return RunWorkflowResponse.from_issue_flow_result(result)
