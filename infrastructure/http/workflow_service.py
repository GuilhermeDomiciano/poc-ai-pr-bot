import logging

from application.run_issue_flow import run_issue_flow
from infrastructure.http.errors import WorkflowExecutionError
from infrastructure.http.workflow_factory import (
    build_issue_flow_config_from_request,
    build_issue_flow_dependencies,
)
from infrastructure.http.mappers import to_run_workflow_response
from infrastructure.http.schemas import RunWorkflowRequest, RunWorkflowResponse
from infrastructure.observability.logging_utils import log_event


logger = logging.getLogger(__name__)


def execute_workflow(payload: RunWorkflowRequest) -> RunWorkflowResponse:
    try:
        flow_config = build_issue_flow_config_from_request(payload)
        flow_dependencies = build_issue_flow_dependencies(payload)
        result = run_issue_flow(
            flow_config,
            flow_dependencies,
            raise_on_error=False,
        )
    except Exception as error:
        log_event(logger, logging.ERROR, "http.workflow.execution_failed", error=str(error))
        raise WorkflowExecutionError("workflow execution failed") from error

    if result.status == "error":
        raise WorkflowExecutionError(result.error or "workflow execution failed")

    return to_run_workflow_response(result)
