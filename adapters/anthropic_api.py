import os
import time

from .base import LLMAdapter, LLMResponse

# Cost per million tokens (USD)
COST_TABLE = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-5": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-opus-4": {"input": 15.00, "output": 75.00},
}

DEFAULT_COST = {"input": 3.00, "output": 15.00}


class AnthropicAPIAdapter(LLMAdapter):
    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str = None,
        max_tokens: int = 4096,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.default_max_tokens = max_tokens

    def _get_client(self):
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("anthropic package is required: pip install anthropic") from exc
        return anthropic.Anthropic(api_key=self.api_key)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Try exact match, then prefix match
        pricing = COST_TABLE.get(model)
        if pricing is None:
            for key in COST_TABLE:
                if model.startswith(key) or key.startswith(model):
                    pricing = COST_TABLE[key]
                    break
        if pricing is None:
            pricing = DEFAULT_COST
        cost = (input_tokens / 1_000_000) * pricing["input"]
        cost += (output_tokens / 1_000_000) * pricing["output"]
        return cost

    def call(
        self,
        messages: list[dict],
        system_prompt: str = "",
        tools: list[dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens or self.default_max_tokens,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = tools

        start = time.time()
        response = client.messages.create(**kwargs)
        duration_ms = int((time.time() - start) * 1000)

        # Extract text content and tool_use blocks
        content_text_parts = []
        tool_calls = []
        for block in response.content:
            if hasattr(block, "type"):
                if block.type == "text":
                    content_text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

        content = "\n".join(content_text_parts)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost_usd = self._calculate_cost(self.model, input_tokens, output_tokens)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            tool_calls=tool_calls,
        )
