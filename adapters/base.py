from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    content: str           # Text content of the response
    input_tokens: int
    output_tokens: int
    cost_usd: float
    duration_ms: int
    tool_calls: list[dict] = field(default_factory=list)  # For tool_use responses


class LLMAdapter(ABC):
    @abstractmethod
    def call(
        self,
        messages: list[dict],
        system_prompt: str = "",
        tools: list[dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...
