import os
from dataclasses import dataclass, field

from application.ports import AIProvider


_DEFAULT_MODEL = "claude-3-5-sonnet-latest"


@dataclass(frozen=True)
class AnthropicProvider(AIProvider):
    model: str
    api_key: str = field(repr=False)

    @classmethod
    def from_env(cls) -> "AnthropicProvider":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Missing required environment variable: ANTHROPIC_API_KEY")

        model = os.getenv("ANTHROPIC_MODEL", _DEFAULT_MODEL)
        return cls(model=model, api_key=api_key)

    def generate_changes(
        self,
        issue_title: str,
        issue_body: str,
        repo_tree: str,
    ) -> str:
        raise RuntimeError("Anthropic provider is configured but not implemented yet")
