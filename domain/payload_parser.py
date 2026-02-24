import json
from typing import Any

from domain.models import ChangeSet


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


def parse_payload(text: str) -> ChangeSet:
    payload_data = extract_first_json_object(text)
    if not isinstance(payload_data, dict):
        raise RuntimeError(
            "No valid JSON object found in Crew output. "
            "Update prompts to return pure JSON."
        )

    required_keys = {"files", "branch", "commit", "pr_title", "pr_body"}
    missing_keys = required_keys - payload_data.keys()
    if missing_keys:
        raise RuntimeError(
            f"Crew JSON is missing required keys: {sorted(missing_keys)}. "
            "Expected keys: files, branch, commit, pr_title, pr_body."
        )

    if not isinstance(payload_data["files"], dict):
        raise RuntimeError("Crew JSON key 'files' must be an object map: {path: content}.")

    return ChangeSet(
        files=payload_data["files"],
        branch=payload_data["branch"],
        commit=payload_data["commit"],
        pr_title=payload_data["pr_title"],
        pr_body=payload_data["pr_body"],
    )
