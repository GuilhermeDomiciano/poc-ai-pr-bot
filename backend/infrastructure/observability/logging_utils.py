import logging
import re
from datetime import datetime, timezone
from typing import Any, Iterable

from infrastructure.observability.context import get_request_id
from infrastructure.observability.event_stream import publish_runtime_event


_TOKEN_PATTERNS = (
    re.compile(r"(x-access-token:)[^@\s]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9_\-.]+", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]+\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]+\b"),
)
_REGISTERED_SENSITIVE_VALUES: set[str] = set()


def register_sensitive_values(*values: str) -> None:
    for value in values:
        if value:
            _REGISTERED_SENSITIVE_VALUES.add(value)


def _sensitive_values() -> Iterable[str]:
    return _REGISTERED_SENSITIVE_VALUES


def redact_secrets(text: str) -> str:
    redacted = text
    for value in _sensitive_values():
        redacted = redacted.replace(value, "[REDACTED]")
    for pattern in _TOKEN_PATTERNS:
        if pattern.groups > 0:
            redacted = pattern.sub(r"\1[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
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
        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
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


def _format_field_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return safe_message(value)
    return safe_message(repr(value))


def structured_message(event: str, **fields: Any) -> str:
    parts = [f"event={safe_message(event)}"]
    for key, value in fields.items():
        if value is None:
            continue
        formatted_value = _format_field_value(value).replace('"', '\\"')
        parts.append(f'{key}="{formatted_value}"')
    return " ".join(parts)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    request_id = get_request_id()
    normalized_fields = {
        key: _format_field_value(value)
        for key, value in fields.items()
        if value is not None
    }
    message = structured_message(event, **fields)

    logger.log(level, message)
    publish_runtime_event(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": logging.getLevelName(level).lower(),
            "event": event,
            "request_id": request_id,
            "fields": normalized_fields,
            "message": message,
        }
    )
