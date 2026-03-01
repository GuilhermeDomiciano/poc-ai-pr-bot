"""Backward-compatible imports for payload parsing.

Prefer importing from `domain.payload` in new code.
"""

from domain.payload import (
    CONTRACT_ERROR_PREFIX,
    ContractViolationError,
    extract_first_json_object,
    parse_payload,
)

__all__ = [
    "CONTRACT_ERROR_PREFIX",
    "ContractViolationError",
    "extract_first_json_object",
    "parse_payload",
]
