from fastapi import HTTPException, status


INTERNAL_WORKFLOW_ERROR_MESSAGE = "Internal error while executing workflow"


class WorkflowExecutionError(RuntimeError):
    """Controlled exception for workflow execution failures in the HTTP adapter."""


def to_http_exception(error: Exception) -> HTTPException:
    if isinstance(error, WorkflowExecutionError):
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=INTERNAL_WORKFLOW_ERROR_MESSAGE,
        )

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=INTERNAL_WORKFLOW_ERROR_MESSAGE,
    )
