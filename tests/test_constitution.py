"""
Tests for the Constitution class.
"""

import pytest

from constitution import Constitution


class TestConstitutionDefault:
    def test_default_returns_non_empty_text(self):
        c = Constitution.default()
        assert isinstance(c.text, str)
        assert len(c.text.strip()) > 0

    def test_default_contains_epistemic_honesty(self):
        c = Constitution.default()
        assert "EPISTEMIC HONESTY" in c.text

    def test_default_contains_confidence_calibration(self):
        c = Constitution.default()
        assert "CONFIDENCE CALIBRATION" in c.text

    def test_default_contains_bad_news_first(self):
        c = Constitution.default()
        assert "BAD NEWS FIRST" in c.text


class TestConstitutionAsPrompt:
    def test_as_prompt_wraps_with_start_marker(self):
        c = Constitution("some rules")
        prompt = c.as_prompt()
        assert "[CONSTITUTIONAL RULES]" in prompt

    def test_as_prompt_wraps_with_end_marker(self):
        c = Constitution("some rules")
        prompt = c.as_prompt()
        assert "[END CONSTITUTIONAL RULES]" in prompt

    def test_as_prompt_contains_text(self):
        c = Constitution("do not lie")
        prompt = c.as_prompt()
        assert "do not lie" in prompt

    def test_as_prompt_text_between_markers(self):
        c = Constitution("be honest")
        prompt = c.as_prompt()
        start_idx = prompt.index("[CONSTITUTIONAL RULES]")
        end_idx = prompt.index("[END CONSTITUTIONAL RULES]")
        assert start_idx < end_idx
        assert "be honest" in prompt[start_idx:end_idx]


class TestConstitutionMerge:
    def test_merge_combines_both_texts(self):
        c1 = Constitution("rule one")
        c2 = Constitution("rule two")
        merged = c1.merge(c2)
        assert "rule one" in merged.text
        assert "rule two" in merged.text

    def test_merge_returns_constitution_instance(self):
        c1 = Constitution("a")
        c2 = Constitution("b")
        merged = c1.merge(c2)
        assert isinstance(merged, Constitution)

    def test_merge_does_not_mutate_originals(self):
        c1 = Constitution("only this")
        c2 = Constitution("and that")
        c1.merge(c2)
        assert c1.text == "only this"
        assert c2.text == "and that"


class TestConstitutionFromFile:
    def test_from_file_loads_text(self, tmp_path):
        f = tmp_path / "const.md"
        f.write_text("## Rules\nBe honest.", encoding="utf-8")
        c = Constitution.from_file(f)
        assert "Be honest." in c.text

    def test_from_file_raises_value_error_for_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.md"
        with pytest.raises(ValueError, match="not found"):
            Constitution.from_file(missing)

    def test_from_file_accepts_string_path(self, tmp_path):
        f = tmp_path / "rules.txt"
        f.write_text("always calibrate", encoding="utf-8")
        c = Constitution.from_file(str(f))
        assert "always calibrate" in c.text


class TestConstitutionFromSoulMd:
    def test_from_soul_md_extracts_hard_constraints(self, tmp_path):
        soul = tmp_path / "SOUL.md"
        soul.write_text(
            "## Mission\nBe useful.\n\n## Hard Constraints\n- Never lie.\n- Never harm.\n\n## Tools\nSearch.",
            encoding="utf-8",
        )
        c = Constitution.from_soul_md(soul)
        assert "Never lie" in c.text
        assert "Never harm" in c.text
        # Should not include content from other sections
        assert "Be useful" not in c.text
        assert "Search" not in c.text

    def test_from_soul_md_falls_back_to_full_content_if_no_section(self, tmp_path):
        soul = tmp_path / "SOUL.md"
        content = "## Mission\nBe helpful.\n\n## Values\nHonesty."
        soul.write_text(content, encoding="utf-8")
        c = Constitution.from_soul_md(soul)
        # No Hard Constraints section -> returns full content
        assert "Be helpful" in c.text
        assert "Honesty" in c.text
