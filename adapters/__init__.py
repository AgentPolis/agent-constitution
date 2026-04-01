from .base import LLMAdapter, LLMResponse
from .mock import MockAdapter

__all__ = [
    "LLMAdapter",
    "LLMResponse",
    "MockAdapter",
    "AnthropicAPIAdapter",
    "ClaudeCLIAdapter",
    "OllamaAdapter",
]


def __getattr__(name):
    if name == "AnthropicAPIAdapter":
        from .anthropic_api import AnthropicAPIAdapter
        return AnthropicAPIAdapter
    if name == "ClaudeCLIAdapter":
        from .claude_cli import ClaudeCLIAdapter
        return ClaudeCLIAdapter
    if name == "OllamaAdapter":
        from .ollama import OllamaAdapter
        return OllamaAdapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
