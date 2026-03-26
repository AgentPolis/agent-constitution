import time

from .base import LLMAdapter, LLMResponse

DEFAULT_RESPONSES = {
    "analyst": (
        '{"score": 35, "dimensions": {"market_size": 8, "timing": 7, "moat": 6, '
        '"execution": 7, "revenue": 7}, "summary": "Strong opportunity with good market fundamentals.", '
        '"confidence": 0.75, "speculation_tags": []}'
    ),
    "critic": (
        '{"challenges": ["Market is more competitive than assessed", '
        '"Revenue timeline is optimistic", "Technical complexity underestimated"], '
        '"severity": "medium", "confidence": 0.80}'
    ),
    "judge": (
        '{"verdict": "proceed_with_caution", "score_delta": -3, '
        '"reasoning": "Challenges are valid but defender provided reasonable rebuttals. '
        'Proceed with reduced confidence.", "confidence": 0.72}'
    ),
    "default": (
        '{"status": "ok", "response": "Task completed successfully.", "confidence": 0.70}'
    ),
}


def _estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


class MockAdapter(LLMAdapter):
    def __init__(
        self,
        role_responses: dict = None,
        simulate_delay_ms: int = 50,
    ):
        self.role_responses = {**DEFAULT_RESPONSES, **(role_responses or {})}
        self.simulate_delay_ms = simulate_delay_ms

    def _detect_role(self, system_prompt: str) -> str:
        lowered = system_prompt.lower()
        # Check all known roles (built-in + custom), excluding "default"
        for role in self.role_responses:
            if role == "default":
                continue
            if role in lowered:
                return role
        return "default"

    def call(
        self,
        messages: list[dict],
        system_prompt: str = "",
        tools: list[dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        if self.simulate_delay_ms > 0:
            time.sleep(self.simulate_delay_ms / 1000.0)

        role = self._detect_role(system_prompt)
        content = self.role_responses.get(role, self.role_responses["default"])

        # Estimate token counts from prompt + response
        prompt_text = system_prompt + " ".join(
            msg.get("content", "") if isinstance(msg.get("content"), str) else ""
            for msg in messages
        )
        input_tokens = _estimate_tokens(prompt_text)
        output_tokens = _estimate_tokens(content)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
            duration_ms=self.simulate_delay_ms,
            tool_calls=[],
        )
