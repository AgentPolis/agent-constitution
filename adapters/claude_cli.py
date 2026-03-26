import json
import subprocess
import time

from .base import LLMAdapter, LLMResponse

MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
}

# Cost per million tokens (USD)
COST_TABLE = {
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}

# Default costs for unknown models (sonnet-level)
DEFAULT_COST = {"input": 3.00, "output": 15.00}


class ClaudeCLIAdapter(LLMAdapter):
    def __init__(self, model: str = "claude-haiku-4-5-20251001", allowed_tools: list[str] = None):
        self.model = MODEL_ALIASES.get(model, model)
        self.allowed_tools = allowed_tools  # instance-level tool allowlist

    def _messages_to_prompt(self, messages: list[dict], system_prompt: str = "") -> str:
        parts = []
        if system_prompt:
            parts.append(f"System: {system_prompt}")
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            if isinstance(content, list):
                # Handle content blocks
                text_parts = [
                    block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"
                ]
                content = " ".join(text_parts)
            parts.append(f"{role}: {content}")
        return "\n\n".join(parts)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = COST_TABLE.get(model, DEFAULT_COST)
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
        prompt = self._messages_to_prompt(messages, system_prompt)

        cmd = [
            "claude",
            "-p", prompt,
            "--model", self.model,
            "--output-format", "json",
            "--no-session-persistence",
            "--max-tokens", str(max_tokens),
        ]

        # Determine effective tools list
        effective_tools = tools or self.allowed_tools
        if effective_tools:
            tool_names = []
            for t in effective_tools:
                if isinstance(t, dict):
                    tool_names.append(t.get("name", str(t)))
                else:
                    tool_names.append(str(t))
            cmd += ["--allowedTools", ",".join(tool_names)]
        else:
            # Pure thinker — no tools
            cmd += ["--tools", ""]

        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        duration_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI returned non-zero exit code {result.returncode}: {result.stderr}"
            )

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse claude CLI JSON output: {exc}\nOutput: {result.stdout}") from exc

        content = data.get("result", data.get("content", ""))
        if isinstance(content, list):
            text_parts = [
                block.get("text", "") for block in content if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = "\n".join(text_parts)

        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        cost_usd = self._calculate_cost(self.model, input_tokens, output_tokens)

        # Extract tool calls if present
        tool_calls = []
        raw_content = data.get("content", [])
        if isinstance(raw_content, list):
            for block in raw_content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_calls.append({
                        "id": block.get("id"),
                        "name": block.get("name"),
                        "input": block.get("input", {}),
                    })

        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            tool_calls=tool_calls,
        )
