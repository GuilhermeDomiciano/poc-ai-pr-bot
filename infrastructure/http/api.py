import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from starlette.responses import Response

from application.run_issue_flow import IssueFlowDependencies, run_issue_flow
from domain.payload_parser import parse_payload
from infrastructure.ai.crew_runner import run_crew
from infrastructure.github.github_client import GitHubClient
from infrastructure.http.factories import build_issue_flow_config_from_request
from infrastructure.http.schemas import RunWorkflowRequest, RunWorkflowResponse
from infrastructure.observability.context import reset_request_id, set_request_id
from infrastructure.observability.logging_utils import configure_logging, safe_message
from infrastructure.repo.file_writer import apply_files
from infrastructure.repo.operations import (
    clone_repo,
    git_setup,
    remote_branch_exists,
    repo_tree_summary,
    run,
)


configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="POC AI PR Bot API")


@app.middleware("http")
async def request_observability_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)

    method = request.method
    path = request.url.path
    start_time = time.perf_counter()
    logger.info(safe_message(f"HTTP start method={method} path={path}"))

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            safe_message(
                f"HTTP end method={method} path={path} status={status_code} duration_ms={duration_ms:.2f}"
            )
        )
        reset_request_id(token)


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
        logger.error(safe_message("Workflow execution failed"))
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
