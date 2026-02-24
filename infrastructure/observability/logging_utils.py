import logging
import os
import re
from typing import Iterable

from infrastructure.observability.context import get_request_id


_SENSITIVE_ENV_KEYS = (
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
)
_TOKEN_PATTERNS = (
    re.compile(r"(x-access-token:)[^@\s]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-.]+", re.IGNORECASE),
)


def _sensitive_values() -> Iterable[str]:
    for key in _SENSITIVE_ENV_KEYS:
        value = os.getenv(key)
        if value:
            yield value


def redact_secrets(text: str) -> str:
    redacted = text
    for value in _sensitive_values():
        redacted = redacted.replace(value, "[REDACTED]")
    for pattern in _TOKEN_PATTERNS:
        redacted = pattern.sub(r"\1[REDACTED]", redacted)
    return redacted


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def configure_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [request_id=%(request_id)s] %(name)s - %(message)s",
        )

    current_factory = logging.getLogRecordFactory()
    if not getattr(current_factory, "_request_id_factory", False):
        def record_factory(*args, **kwargs):
            record = current_factory(*args, **kwargs)
            record.request_id = get_request_id()
            return record

        setattr(record_factory, "_request_id_factory", True)
        logging.setLogRecordFactory(record_factory)

    for handler in logging.getLogger().handlers:
        has_request_id_filter = any(isinstance(f, RequestIdFilter) for f in handler.filters)
        if not has_request_id_filter:
            handler.addFilter(RequestIdFilter())


def safe_message(message: str) -> str:
    return redact_secrets(message)
