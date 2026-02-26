import json
from pathlib import PurePosixPath
from typing import Any

from domain.models import ChangeSet


CONTRACT_ERROR_PREFIX = "Integration contract violation"
ALLOWED_FILE_ROOTS = {"backend", "frontend"}


def _contract_error(details: str) -> RuntimeError:
    return RuntimeError(f"{CONTRACT_ERROR_PREFIX}: {details}")


def extract_first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for character_index, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed_object, _ = decoder.raw_decode(text[character_index:])
            return parsed_object
        except json.JSONDecodeError:
            continue
    return None


def _validate_required_keys(payload_data: dict[str, Any]) -> None:
    required_keys = {"files", "branch", "commit", "pr_title", "pr_body"}
    missing_keys = required_keys - payload_data.keys()
    if missing_keys:
        raise _contract_error(
            f"missing required keys: {sorted(missing_keys)}; expected keys: files, branch, commit, pr_title, pr_body"
        )


def _validate_string_field(payload_data: dict[str, Any], field_name: str) -> str:
    value = payload_data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise _contract_error(f"field '{field_name}' must be a non-empty string")
    return value


def _validate_file_path(file_path: str) -> None:
    if not file_path.strip():
        raise _contract_error("file path must be a non-empty string")

    if "\\" in file_path:
        raise _contract_error(f"file path '{file_path}' must use '/' as separator")

    if file_path.startswith("~"):
        raise _contract_error(f"file path '{file_path}' must not start with '~'")

    normalized_path = PurePosixPath(file_path)
    if normalized_path.is_absolute():
        raise _contract_error(f"file path '{file_path}' must be repository-relative, not absolute")

    if any(part in {"", ".", ".."} for part in normalized_path.parts):
        raise _contract_error(f"file path '{file_path}' contains invalid path traversal segments")

    if len(normalized_path.parts) < 2:
        raise _contract_error(
            f"file path '{file_path}' must include a target file under backend/ or frontend/"
        )

    if normalized_path.parts[0] not in ALLOWED_FILE_ROOTS:
        raise _contract_error(
            f"file path '{file_path}' must start with 'backend/' or 'frontend/'"
        )


def _validate_files_map(files_value: Any) -> dict[str, str]:
    if not isinstance(files_value, dict):
        raise _contract_error("field 'files' must be an object map: {path: content}")

    if not files_value:
        raise _contract_error("field 'files' must contain at least one file change")

    validated_files: dict[str, str] = {}
    for raw_path, raw_content in files_value.items():
        if not isinstance(raw_path, str):
            raise _contract_error("all file paths in 'files' must be strings")

        _validate_file_path(raw_path)

        if not isinstance(raw_content, str):
            raise _contract_error(f"file content for '{raw_path}' must be a string")

        validated_files[raw_path] = raw_content

    return validated_files


def parse_payload(text: str) -> ChangeSet:
    payload_data = extract_first_json_object(text)
    if not isinstance(payload_data, dict):
        raise _contract_error("no valid JSON object found in crew output; return JSON only")

    _validate_required_keys(payload_data)

    files_map = _validate_files_map(payload_data["files"])
    branch = _validate_string_field(payload_data, "branch")
    commit = _validate_string_field(payload_data, "commit")
    pr_title = _validate_string_field(payload_data, "pr_title")
    pr_body = _validate_string_field(payload_data, "pr_body")

    return ChangeSet(
        files=files_map,
        branch=branch,
        commit=commit,
        pr_title=pr_title,
        pr_body=pr_body,
    )
