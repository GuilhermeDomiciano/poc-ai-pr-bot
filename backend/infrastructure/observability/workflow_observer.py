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


def observe_generated_change_set(change_set: ChangeSet) -> None:
    change_scope = classify_change_scope(change_set.files)
    log_event(
        logger,
        logging.INFO,
        "workflow.change_set.generated",
        change_scope=change_scope,
        files_count=len(change_set.files),
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
