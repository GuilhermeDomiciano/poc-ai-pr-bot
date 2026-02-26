import logging

from domain.models import ChangeSet
from domain.payload_parser import CONTRACT_ERROR_PREFIX
from infrastructure.observability.logging_utils import log_event


logger = logging.getLogger(__name__)


def classify_change_scope(files_map: dict[str, str]) -> str:
    has_backend = any(path.startswith("backend/") for path in files_map)
    has_frontend = any(path.startswith("frontend/") for path in files_map)

    if has_backend and has_frontend:
        return "fullstack"
    if has_backend:
        return "backend_only"
    if has_frontend:
        return "frontend_only"
    return "unknown"


def _count_files_by_scope(files_map: dict[str, str]) -> tuple[int, int]:
    backend_files_count = sum(1 for path in files_map if path.startswith("backend/"))
    frontend_files_count = sum(1 for path in files_map if path.startswith("frontend/"))
    return backend_files_count, frontend_files_count


def observe_generated_change_set(change_set: ChangeSet) -> None:
    change_scope = classify_change_scope(change_set.files)
    backend_files_count, frontend_files_count = _count_files_by_scope(change_set.files)
    log_event(
        logger,
        logging.INFO,
        "workflow.change_set.generated",
        change_scope=change_scope,
        files_count=len(change_set.files),
        backend_files_count=backend_files_count,
        frontend_files_count=frontend_files_count,
    )


def is_contract_violation_error(error_message: str) -> bool:
    return error_message.startswith(CONTRACT_ERROR_PREFIX)


def log_contract_violation(error_message: str) -> None:
    log_event(
        logger,
        logging.ERROR,
        "workflow.integration_contract.failed",
        error=error_message,
    )


def observe_workflow_step(step: str, status: str, detail: str | None = None) -> None:
    level = logging.ERROR if status == "error" else logging.INFO
    log_event(
        logger,
        level,
        "workflow.step",
        step=step,
        status=status,
        detail=detail,
    )
