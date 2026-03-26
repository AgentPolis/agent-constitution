"""
Tests for the LLM adapter abstraction layer.
All execution tests use MockAdapter only (no API key required).
"""

import pytest

from adapters import LLMAdapter, LLMResponse, ClaudeCLIAdapter, AnthropicAPIAdapter, MockAdapter


# ---------------------------------------------------------------------------
# LLMResponse field types
# ---------------------------------------------------------------------------

class TestLLMResponseFields:
    def test_required_fields_present(self):
        resp = LLMResponse(
            content="hello",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            duration_ms=123,
        )
        assert hasattr(resp, "content")
        assert hasattr(resp, "input_tokens")
        assert hasattr(resp, "output_tokens")
        assert hasattr(resp, "cost_usd")
        assert hasattr(resp, "duration_ms")
        assert hasattr(resp, "tool_calls")

    def test_field_types(self):
        resp = LLMResponse(
            content="hello",
            input_tokens=10,
            output_tokens=5,
            cost_usd=0.001,
            duration_ms=123,
        )
        assert isinstance(resp.content, str)
        assert isinstance(resp.input_tokens, int)
        assert isinstance(resp.output_tokens, int)
        assert isinstance(resp.cost_usd, float)
        assert isinstance(resp.duration_ms, int)
        assert isinstance(resp.tool_calls, list)

    def test_tool_calls_default_is_empty_list(self):
        resp = LLMResponse(
            content="x",
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.0,
            duration_ms=0,
        )
        assert resp.tool_calls == []

    def test_tool_calls_explicit(self):
        calls = [{"id": "123", "name": "search", "input": {"q": "test"}}]
        resp = LLMResponse(
            content="x",
            input_tokens=1,
            output_tokens=1,
            cost_usd=0.0,
            duration_ms=0,
            tool_calls=calls,
        )
        assert resp.tool_calls == calls


# ---------------------------------------------------------------------------
# Interface checks (isinstance / ABC)
# ---------------------------------------------------------------------------

class TestAdapterInterfaces:
    def test_mock_adapter_is_llm_adapter(self):
        adapter = MockAdapter()
        assert isinstance(adapter, LLMAdapter)

    def test_claude_cli_adapter_is_llm_adapter(self):
        adapter = ClaudeCLIAdapter()
        assert isinstance(adapter, LLMAdapter)

    def test_anthropic_api_adapter_is_llm_adapter(self):
        adapter = AnthropicAPIAdapter()
        assert isinstance(adapter, LLMAdapter)

    def test_all_adapters_have_call_method(self):
        for AdapterClass in (MockAdapter, ClaudeCLIAdapter, AnthropicAPIAdapter):
            adapter = AdapterClass()
            assert callable(getattr(adapter, "call", None))


# ---------------------------------------------------------------------------
# MockAdapter behaviour
# ---------------------------------------------------------------------------

class TestMockAdapter:
    def _make_messages(self, text: str) -> list[dict]:
        return [{"role": "user", "content": text}]

    def test_returns_llm_response(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(self._make_messages("hello"))
        assert isinstance(resp, LLMResponse)

    def test_all_fields_populated(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(self._make_messages("hello"))
        assert isinstance(resp.content, str) and len(resp.content) > 0
        assert isinstance(resp.input_tokens, int) and resp.input_tokens >= 0
        assert isinstance(resp.output_tokens, int) and resp.output_tokens >= 0
        assert isinstance(resp.cost_usd, float)
        assert isinstance(resp.duration_ms, int)
        assert isinstance(resp.tool_calls, list)

    def test_detects_analyst_role(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(
            self._make_messages("analyse this"),
            system_prompt="You are an analyst agent.",
        )
        assert "score" in resp.content

    def test_detects_critic_role(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(
            self._make_messages("critique this"),
            system_prompt="You are a critic who challenges claims.",
        )
        assert "challenges" in resp.content

    def test_detects_judge_role(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(
            self._make_messages("judge the debate"),
            system_prompt="Act as judge and deliver a verdict.",
        )
        assert "verdict" in resp.content

    def test_unknown_role_returns_default(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(
            self._make_messages("do something"),
            system_prompt="You are a generic assistant.",
        )
        assert "status" in resp.content

    def test_empty_system_prompt_returns_default(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(self._make_messages("do something"))
        assert "status" in resp.content

    def test_custom_role_response(self):
        custom = {"planner": '{"plan": "step 1, step 2"}'}
        adapter = MockAdapter(role_responses=custom, simulate_delay_ms=0)
        resp = adapter.call(
            self._make_messages("plan this"),
            system_prompt="You are a planner.",
        )
        assert "plan" in resp.content

    def test_simulate_delay(self):
        import time
        adapter = MockAdapter(simulate_delay_ms=20)
        start = time.time()
        adapter.call(self._make_messages("hi"))
        elapsed_ms = (time.time() - start) * 1000
        assert elapsed_ms >= 15  # allow small timing jitter

    def test_tool_calls_empty_by_default(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(self._make_messages("hi"))
        assert resp.tool_calls == []

    def test_cost_is_zero(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp = adapter.call(self._make_messages("hi"))
        assert resp.cost_usd == 0.0

    def test_multiple_calls_independent(self):
        adapter = MockAdapter(simulate_delay_ms=0)
        resp1 = adapter.call(self._make_messages("a"), system_prompt="You are an analyst.")
        resp2 = adapter.call(self._make_messages("b"), system_prompt="You are a critic.")
        assert "score" in resp1.content
        assert "challenges" in resp2.content
