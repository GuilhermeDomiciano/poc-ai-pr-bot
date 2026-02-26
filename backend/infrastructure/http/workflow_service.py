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
from infrastructure.observability.workflow_observer import (
    is_contract_violation_error,
    log_contract_violation,
)


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
        error_message = str(error)
        if is_contract_violation_error(error_message):
            log_contract_violation(error_message)
        log_event(logger, logging.ERROR, "http.workflow.execution_failed", error=error_message)
        raise WorkflowExecutionError("workflow execution failed") from error

    if result.status == "error":
        error_message = result.error or "workflow execution failed"
        if is_contract_violation_error(error_message):
            log_contract_violation(error_message)
        raise WorkflowExecutionError(error_message)

    return to_run_workflow_response(result)
