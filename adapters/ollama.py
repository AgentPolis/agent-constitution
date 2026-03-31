import time

import httpx

from .base import LLMAdapter, LLMResponse


class OllamaAdapter(LLMAdapter):
    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434/v1",
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def call(
        self,
        messages: list[dict],
        system_prompt: str = "",
        tools: list[dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        api_messages = []
        if system_prompt:
            api_messages.append({"role": "system", "content": system_prompt})
        api_messages.extend(messages)

        payload: dict = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        start = time.time()
        try:
            with httpx.Client(timeout=300) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ConnectionError(
                "Ollama is not running. Start it with: ollama serve"
            ) from exc

        duration_ms = int((time.time() - start) * 1000)
        data = response.json()

        # Extract text content
        choice = data["choices"][0]
        content = choice["message"].get("content") or ""

        # Extract tool calls
        tool_calls = []
        for tc in choice["message"].get("tool_calls") or []:
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": tc["function"]["name"],
                "input": tc["function"].get("arguments", {}),
            })

        # Token counts from usage (may be absent for some Ollama models)
        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=0.0,
            duration_ms=duration_ms,
            tool_calls=tool_calls,
        )
