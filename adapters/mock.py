import json
import random
import time

from .base import LLMAdapter, LLMResponse

# ---------------------------------------------------------------------------
# Challenge templates -- each represents a distinct risk vector a challenger
# might raise during an adversarial review.
# ---------------------------------------------------------------------------
CHALLENGE_TEMPLATES = [
    {
        "category": "market_risk",
        "challenge_text": (
            "The target market shows signs of saturation — top-3 incumbents "
            "already capture 78% of spend.  What evidence exists that a new "
            "entrant can carve meaningful share?"
        ),
        "severity": "high",
    },
    {
        "category": "competitor_threat",
        "challenge_text": (
            "At least two well-funded competitors have announced identical "
            "features on their public roadmaps.  First-mover advantage may "
            "evaporate within 6–9 months."
        ),
        "severity": "high",
    },
    {
        "category": "technical_feasibility",
        "challenge_text": (
            "The proposed architecture relies on components that have not been "
            "proven at the required scale.  Latency targets of <200 ms may be "
            "unrealistic without a fundamental redesign."
        ),
        "severity": "high",
    },
    {
        "category": "regulatory_risk",
        "challenge_text": (
            "Pending legislation in at least three target jurisdictions could "
            "impose data-residency requirements that invalidate the current "
            "cloud deployment model."
        ),
        "severity": "medium",
    },
    {
        "category": "team_capacity",
        "challenge_text": (
            "The execution plan requires 4 senior engineers the team does not "
            "yet have.  Hiring timelines in this market average 3–5 months per "
            "senior hire."
        ),
        "severity": "medium",
    },
    {
        "category": "funding_runway",
        "challenge_text": (
            "At the projected burn rate, runway is 11 months.  If customer "
            "acquisition lags by even one quarter the company will need to "
            "raise an unplanned bridge round at dilutive terms."
        ),
        "severity": "high",
    },
    {
        "category": "market_timing",
        "challenge_text": (
            "Enterprise adoption cycles in this segment average 9–14 months.  "
            "The go-to-market plan assumes a 4-month sales cycle that only "
            "applies to SMB buyers."
        ),
        "severity": "medium",
    },
    {
        "category": "customer_acquisition_cost",
        "challenge_text": (
            "Blended CAC in comparable SaaS verticals runs $1,200–$1,800.  "
            "The model assumes $600 with no paid-acquisition channel proven at "
            "scale."
        ),
        "severity": "medium",
    },
    {
        "category": "scalability_concerns",
        "challenge_text": (
            "The data pipeline is single-tenant by design.  Migrating to "
            "multi-tenant would require re-architecting the storage layer — "
            "an estimated 3–4 month effort that is not on the roadmap."
        ),
        "severity": "high",
    },
    {
        "category": "dependency_risk",
        "challenge_text": (
            "Core functionality depends on a third-party API whose SLA "
            "guarantees only 99.5% uptime and whose pricing has increased "
            "40% year-over-year for the last two years."
        ),
        "severity": "medium",
    },
    {
        "category": "market_risk",
        "challenge_text": (
            "Customer interviews reveal willingness-to-pay 30–40% below the "
            "proposed price point.  Unit economics turn negative at those "
            "levels unless COGS drops substantially."
        ),
        "severity": "high",
    },
    {
        "category": "technical_feasibility",
        "challenge_text": (
            "The ML model accuracy claimed in the pitch deck was measured on "
            "a curated benchmark.  Real-world precision on noisy production "
            "data is likely 15–20 points lower."
        ),
        "severity": "medium",
    },
]

# ---------------------------------------------------------------------------
# Defense templates -- structured rebuttals keyed by challenge category.
# ---------------------------------------------------------------------------
DEFENSE_TEMPLATES = {
    "market_risk": [
        {
            "defense_text": (
                "Independent TAM analysis from two credible sources confirms "
                "the underserved mid-market segment alone represents $2.4B in "
                "annual spend — largely untouched by the top-3 incumbents."
            ),
            "evidence_type": "market_research",
        },
        {
            "defense_text": (
                "Early pricing experiments with 120 beta users show 68% "
                "conversion at the proposed price point, suggesting "
                "willingness-to-pay is within range for the target persona."
            ),
            "evidence_type": "customer_validation",
        },
    ],
    "competitor_threat": [
        {
            "defense_text": (
                "Our patent-pending approach to data enrichment gives us a "
                "12–18 month technical lead.  Competitors' announced features "
                "address a different workflow and do not overlap directly."
            ),
            "evidence_type": "competitive_analysis",
        },
    ],
    "technical_feasibility": [
        {
            "defense_text": (
                "Load testing on staging infrastructure demonstrates <150 ms "
                "p99 latency at 3x projected peak traffic.  Architecture "
                "review was signed off by two external advisors."
            ),
            "evidence_type": "technical_validation",
        },
        {
            "defense_text": (
                "Model accuracy on a held-out production sample is 82%, only "
                "4 points below the benchmark figure.  An active-learning "
                "pipeline is already improving precision week-over-week."
            ),
            "evidence_type": "technical_validation",
        },
    ],
    "regulatory_risk": [
        {
            "defense_text": (
                "Legal counsel has mapped all pending legislation and "
                "confirmed our multi-region deployment option satisfies "
                "data-residency requirements in all three jurisdictions."
            ),
            "evidence_type": "legal_review",
        },
    ],
    "team_capacity": [
        {
            "defense_text": (
                "Two of the four senior hires are already in final-round "
                "interviews.  Additionally, a staffing partnership can "
                "provide contract engineers within 3 weeks to bridge gaps."
            ),
            "evidence_type": "hiring_pipeline",
        },
    ],
    "funding_runway": [
        {
            "defense_text": (
                "The financial model includes a conservative contingency "
                "buffer.  Even under the downside scenario, runway extends "
                "to 14 months, and two investors have signaled follow-on "
                "interest at current valuation."
            ),
            "evidence_type": "financial_model",
        },
    ],
    "market_timing": [
        {
            "defense_text": (
                "Our product-led-growth motion bypasses traditional "
                "enterprise procurement.  Three design partners converted "
                "from trial to paid in under 6 weeks, suggesting the sales "
                "cycle assumption holds for our ICP."
            ),
            "evidence_type": "customer_validation",
        },
    ],
    "customer_acquisition_cost": [
        {
            "defense_text": (
                "Organic and community-driven acquisition currently accounts "
                "for 55% of pipeline at near-zero marginal cost.  Blended "
                "CAC including paid channels is $740, trending downward."
            ),
            "evidence_type": "growth_metrics",
        },
    ],
    "scalability_concerns": [
        {
            "defense_text": (
                "The storage layer already uses a partitioned schema that "
                "supports tenant isolation.  Migration to full multi-tenant "
                "is scoped at 5 weeks — not 3–4 months — per engineering's "
                "detailed breakdown."
            ),
            "evidence_type": "technical_validation",
        },
    ],
    "dependency_risk": [
        {
            "defense_text": (
                "A fallback provider has been integrated behind a feature "
                "flag and passes all integration tests.  Pricing risk is "
                "mitigated by a 2-year rate-lock negotiated last quarter."
            ),
            "evidence_type": "risk_mitigation",
        },
    ],
}

# ---------------------------------------------------------------------------
# Legacy default responses -- kept for backward compatibility.
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _estimate_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def _extract_message_text(messages: list[dict]) -> str:
    """Concatenate user/assistant message content into a single string."""
    parts = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Response generators — one per debate role.
# ---------------------------------------------------------------------------

def _generate_challenger_response() -> dict:
    """Select 3 diverse challenges and format as structured output."""
    # Prefer distinct categories when possible.
    by_category: dict[str, list[dict]] = {}
    for t in CHALLENGE_TEMPLATES:
        by_category.setdefault(t["category"], []).append(t)

    categories = list(by_category.keys())
    random.shuffle(categories)
    selected: list[dict] = []
    for cat in categories:
        if len(selected) >= 3:
            break
        selected.append(random.choice(by_category[cat]))

    # If we somehow have fewer than 3 categories, fill from remaining pool.
    if len(selected) < 3:
        remaining = [t for t in CHALLENGE_TEMPLATES if t not in selected]
        selected.extend(random.sample(remaining, 3 - len(selected)))

    challenges = [tpl["challenge_text"] for tpl in selected]

    return {
        "challenges": challenges,
        "severity": max(tpl["severity"] for tpl in selected),
        "confidence": round(random.uniform(0.72, 0.92), 2),
    }


def _generate_defender_response(messages: list[dict]) -> dict:
    """Parse prior messages for challenge categories and produce defenses."""
    prior_text = _extract_message_text(messages).lower()

    # Identify which categories were raised.
    matched_categories: list[str] = []
    for cat in DEFENSE_TEMPLATES:
        # Match on the category name (underscores replaced with spaces too).
        if cat in prior_text or cat.replace("_", " ") in prior_text:
            matched_categories.append(cat)

    # Fallback: if nothing matched, pick 3 random categories so we always
    # return something useful.
    if not matched_categories:
        matched_categories = random.sample(
            list(DEFENSE_TEMPLATES.keys()), min(3, len(DEFENSE_TEMPLATES))
        )

    defenses = []
    for cat in matched_categories:
        tpl = random.choice(DEFENSE_TEMPLATES[cat])
        defenses.append(tpl["defense_text"])

    return {
        "defenses": defenses,
        "confidence": round(random.uniform(0.68, 0.88), 2),
    }


def _generate_judge_response() -> dict:
    """Weighted random verdict with a score delta and reasoning."""
    verdict = random.choices(
        ["proceed", "proceed_with_caution", "reject"],
        weights=[30, 50, 20],
        k=1,
    )[0]

    score_delta = random.randint(-5, 3)

    reasoning_map = {
        "proceed": (
            "Challenges raised were substantive but the defense provided "
            "credible evidence on every point.  Risk profile is acceptable."
        ),
        "proceed_with_caution": (
            "Several challenges remain partially unresolved.  The team "
            "should address the highest-severity items before the next gate."
        ),
        "reject": (
            "Critical risks around feasibility and runway were not "
            "adequately mitigated.  Revisit after the identified gaps are "
            "closed."
        ),
    }

    return {
        "verdict": verdict,
        "score_delta": score_delta,
        "reasoning": reasoning_map[verdict],
        "confidence": round(random.uniform(0.60, 0.85), 2),
    }


# ---------------------------------------------------------------------------
# Validator — lightweight schema check on generated responses.
# ---------------------------------------------------------------------------

_EXPECTED_KEYS: dict[str, set[str]] = {
    "challenger": {"challenges", "severity", "confidence"},
    "defender": {"defenses", "confidence"},
    "judge": {"verdict", "score_delta", "reasoning", "confidence"},
}


def _validate_response(role: str, payload: dict) -> bool:
    """Return True if *payload* contains all keys expected for *role*."""
    expected = _EXPECTED_KEYS.get(role)
    if expected is None:
        # No schema defined for this role — accept anything.
        return True
    return expected.issubset(payload.keys())


# ---------------------------------------------------------------------------
# MockAdapter
# ---------------------------------------------------------------------------

class MockAdapter(LLMAdapter):
    def __init__(
        self,
        role_responses: dict = None,
        simulate_delay_ms: int = 50,
    ):
        self._custom_roles = set(role_responses.keys()) if role_responses else set()
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

    @staticmethod
    def _detect_debate_role(system_prompt: str, messages: list[dict]) -> str | None:
        """Return the debate-specific role only when the user message is a debate prompt."""
        user_text = " ".join(
            msg.get("content", "") for msg in messages if msg.get("role") == "user"
        ).lower()

        # Only enter debate mode when the user message contains debate-specific phrasing.
        # Check verdict FIRST — judge prompts contain "defenses" as context, so defense
        # check would false-positive if tested before verdict.
        if "verdict" in user_text and "evaluate" in user_text:
            return "judge"
        if "challenges" in user_text and "generate" in user_text:
            return "challenger"
        if "provide a defense" in user_text or "defend" in user_text:
            return "defender"
        return None

    def call(
        self,
        messages: list[dict],
        system_prompt: str = "",
        tools: list[dict] = None,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        start = time.time()
        if self.simulate_delay_ms > 0:
            time.sleep(self.simulate_delay_ms / 1000.0)
        duration_ms = int((time.time() - start) * 1000)

        # --- Check for explicit custom role_responses first (backward compat) ---
        role = self._detect_role(system_prompt)
        has_custom_override = role != "default" and role in (self._custom_roles or set())

        if has_custom_override:
            # User supplied an explicit override — honour it verbatim.
            content = self.role_responses[role]
        else:
            # --- Debate-aware generation path ---
            debate_role = self._detect_debate_role(system_prompt, messages)
            if debate_role is not None:
                content = self._generate_debate_response(debate_role, messages)
            else:
                # Fallback to legacy static responses.
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
            duration_ms=duration_ms,
            tool_calls=[],
        )

    # -----------------------------------------------------------------------
    # Generate → validate cycle for debate responses.
    # -----------------------------------------------------------------------

    @staticmethod
    def _generate_debate_response(
        debate_role: str,
        messages: list[dict],
        *,
        _max_attempts: int = 3,
    ) -> str:
        """Generate a role-appropriate response and validate its schema.

        If validation fails (should be rare with deterministic generators),
        retry up to *_max_attempts* times before falling back to a minimal
        valid payload.
        """
        generators = {
            "challenger": lambda: _generate_challenger_response(),
            "defender": lambda: _generate_defender_response(messages),
            "judge": lambda: _generate_judge_response(),
        }

        generate = generators[debate_role]

        for _ in range(_max_attempts):
            payload = generate()
            if _validate_response(debate_role, payload):
                return json.dumps(payload)

        # Final fallback — should never be reached in practice.
        fallback = {
            "challenger": {
                "challenges": [],
                "severity": "low",
                "confidence": 0.50,
            },
            "defender": {
                "defenses": [],
                "confidence": 0.50,
            },
            "judge": {
                "verdict": "proceed_with_caution",
                "score_delta": 0,
                "reasoning": "Insufficient data to render a confident verdict.",
                "confidence": 0.50,
            },
        }
        return json.dumps(fallback[debate_role])
