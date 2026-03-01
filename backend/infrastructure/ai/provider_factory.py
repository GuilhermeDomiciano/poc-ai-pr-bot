import os
from dataclasses import dataclass, field

from application.ports import AIProvider
from infrastructure.ai.anthropic import AnthropicProvider
from infrastructure.ai.openai import OpenAIProvider


_DEFAULT_AI_PROVIDER = "openai"
_PROVIDER_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


@dataclass(frozen=True)
class AIProviderRuntime:
    provider: str
    model: str
    api_key: str = field(repr=False)
    adapter: AIProvider = field(repr=False)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_ai_provider_name() -> str:
    provider = os.getenv("AI_PROVIDER", _DEFAULT_AI_PROVIDER).strip().lower()
    if provider not in _PROVIDER_API_KEY_ENV:
        supported = ", ".join(sorted(_PROVIDER_API_KEY_ENV.keys()))
        raise RuntimeError(f"Invalid AI_PROVIDER '{provider}'. Supported values: {supported}")
    return provider


def build_ai_provider_runtime_from_env() -> AIProviderRuntime:
    provider = resolve_ai_provider_name()
    api_key = _required_env(_PROVIDER_API_KEY_ENV[provider])

    if provider == "openai":
        adapter = OpenAIProvider.from_env()
        model = adapter.model
    else:
        adapter = AnthropicProvider.from_env()
        model = adapter.model

    return AIProviderRuntime(
        provider=provider,
        model=model,
        api_key=api_key,
        adapter=adapter,
    )
