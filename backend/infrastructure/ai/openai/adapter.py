import json
import os
import time
from dataclasses import dataclass
from typing import Any

from jsonschema import ValidationError, validate
from openai import APIConnectionError, APITimeoutError, BadRequestError, OpenAI, RateLimitError

from application.ports import AIProvider


_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TIMEOUT_SECONDS = 120.0
_DEFAULT_MAX_RETRIES = 2
_DEFAULT_RETRY_BACKOFF_SECONDS = 1.0

_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["files", "branch", "commit", "pr_title", "pr_body"],
    "properties": {
        "files": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": {"type": "string"},
        },
        "branch": {"type": "string", "minLength": 1},
        "commit": {"type": "string", "minLength": 1},
        "pr_title": {"type": "string", "minLength": 1},
        "pr_body": {"type": "string", "minLength": 1},
    },
}

_SYSTEM_PROMPT = """
You are an implementation agent for a monorepo with `backend/` and `frontend/`.
Return exactly one JSON object compatible with the contract below.

Rules:
- Output JSON only (no markdown, no comments, no explanation).
- Include full file contents for every changed file.
- All keys inside `files` must be repository-relative paths under `backend/` or `frontend/`.
- Keep the solution coherent across backend/frontend contracts.
""".strip()

_USER_PROMPT_TEMPLATE = """
Issue:
- Title: {issue_title}
- Body: {issue_body}

Repository tree summary:
{repo_tree}

Output contract (required keys):
- files: object map {{ "path/to/file": "FULL_FILE_CONTENT" }}
- branch: string
- commit: string
- pr_title: string
- pr_body: string

Quality constraints:
- Keep edits minimal and safe.
- Preserve existing architecture and API contracts when possible.
- If backend/frontend integration changes are needed, keep request/response names consistent.
""".strip()


@dataclass(frozen=True)
class OpenAIProvider(AIProvider):
    client: OpenAI
    model: str
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS
    max_retries: int = _DEFAULT_MAX_RETRIES
    retry_backoff_seconds: float = _DEFAULT_RETRY_BACKOFF_SECONDS

    @classmethod
    def from_env(cls) -> "OpenAIProvider":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")

        model = os.getenv("OPENAI_MODEL", _DEFAULT_MODEL)
        timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", str(_DEFAULT_TIMEOUT_SECONDS)))
        max_retries = int(os.getenv("OPENAI_MAX_RETRIES", str(_DEFAULT_MAX_RETRIES)))
        retry_backoff_seconds = float(
            os.getenv("OPENAI_RETRY_BACKOFF_SECONDS", str(_DEFAULT_RETRY_BACKOFF_SECONDS))
        )

        # Disable SDK automatic retry to keep retry policy explicit and observable in this layer.
        client = OpenAI(api_key=api_key, timeout=timeout_seconds, max_retries=0)
        return cls(
            client=client,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

    def generate_changes(
        self,
        issue_title: str,
        issue_body: str,
        repo_tree: str,
    ) -> str:
        user_prompt = _USER_PROMPT_TEMPLATE.format(
            issue_title=issue_title.strip(),
            issue_body=issue_body.strip() or "(empty)",
            repo_tree=repo_tree.strip(),
        )
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        attempts = self.max_retries + 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._request_with_schema(messages)
            except BadRequestError:
                # Some models/accounts may not support json_schema in Chat Completions.
                try:
                    return self._request_with_json_object(messages)
                except Exception as fallback_error:  # noqa: BLE001
                    last_error = fallback_error
            except (APITimeoutError, APIConnectionError, RateLimitError) as error:
                last_error = error
            except (ValidationError, ValueError) as error:
                # Retry when model returns malformed/incomplete JSON despite format constraints.
                last_error = error

            if attempt < attempts:
                time.sleep(self.retry_backoff_seconds * attempt)

        error_message = str(last_error) if last_error else "unknown OpenAI provider error"
        raise RuntimeError(f"OpenAI generation failed after {attempts} attempts: {error_message}")

    def _request_with_schema(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            timeout=self.timeout_seconds,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "workflow_changes",
                    "strict": True,
                    "schema": _PAYLOAD_SCHEMA,
                },
            },
        )
        return self._extract_and_validate_content(response)

    def _request_with_json_object(self, messages: list[dict[str, str]]) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            timeout=self.timeout_seconds,
            messages=messages,
            response_format={"type": "json_object"},
        )
        return self._extract_and_validate_content(response)

    def _extract_and_validate_content(self, response: Any) -> str:
        if not response.choices:
            raise ValueError("OpenAI response did not contain choices")

        message = response.choices[0].message
        content = message.content if message else None
        if not isinstance(content, str) or not content.strip():
            raise ValueError("OpenAI response did not contain message content")

        payload = json.loads(content)
        validate(instance=payload, schema=_PAYLOAD_SCHEMA)
        return json.dumps(payload)
