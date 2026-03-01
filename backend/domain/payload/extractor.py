import json
from typing import Any


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
