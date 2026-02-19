import json

from domain.models import ChangeSet


def extract_first_json_object(text: str):
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[idx:])
            return obj
        except json.JSONDecodeError:
            continue
    return None


def parse_payload(text: str) -> ChangeSet:
    payload = extract_first_json_object(text)
    if not isinstance(payload, dict):
        raise RuntimeError(
            "No valid JSON object found in Crew output. "
            "Update prompts to return pure JSON."
        )

    required_keys = {"files", "branch", "commit", "pr_title", "pr_body"}
    missing = required_keys - payload.keys()
    if missing:
        raise RuntimeError(
            f"Crew JSON is missing required keys: {sorted(missing)}. "
            "Expected keys: files, branch, commit, pr_title, pr_body."
        )

    if not isinstance(payload["files"], dict):
        raise RuntimeError("Crew JSON key 'files' must be an object map: {path: content}.")

    return ChangeSet(
        files=payload["files"],
        branch=payload["branch"],
        commit=payload["commit"],
        pr_title=payload["pr_title"],
        pr_body=payload["pr_body"],
    )
