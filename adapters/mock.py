import json
import hashlib
import random
import time

from .base import LLMAdapter, LLMResponse

SCENARIO_DEPLOY = "deploy"
SCENARIO_PRICING = "pricing"
SCENARIO_ORG = "org_design"
SCENARIO_GENERIC = "generic"

SCENARIO_CHALLENGES = {
    SCENARIO_DEPLOY: [
        "Rollback has not been rehearsed on a staging environment that mirrors production.",
        "Blast radius is still broad because billing-auth touches login, entitlements, and revenue events.",
        "Monitoring and abort thresholds are not yet explicit enough for an overnight production change.",
    ],
    SCENARIO_PRICING: [
        "This exception could become a precedent if sales teams cannot clearly explain why this account is special.",
        "Finance has not yet shown that the discounted terms still clear a sensible contribution margin.",
        "The commercial upside is plausible, but the evidence base is still thin for a one-off exception.",
    ],
    SCENARIO_ORG: [
        "A pod reorg this close to launch could interrupt execution ownership during the highest-risk window.",
        "The transition plan does not yet show who temporarily owns cross-functional dependencies.",
        "It is still unclear whether the new structure is reversible if launch execution degrades.",
    ],
    SCENARIO_GENERIC: [
        "The decision still depends on assumptions that have not been pressure-tested with evidence.",
        "The downside case is not yet specific enough to judge reversibility.",
        "Ownership for the next gate is still too vague to support a confident decision.",
    ],
}

SCENARIO_DEFENSES = {
    SCENARIO_DEPLOY: [
        "A rollback runbook exists and can be validated with a staging drill before the production window opens.",
        "The change can be shipped behind a canary release so customer impact stays bounded during the first hour.",
        "On-call ownership and dashboards can be pre-assigned so the team has a clear abort path if metrics move.",
    ],
    SCENARIO_PRICING: [
        "The exception can be time-boxed to one contract and tied to explicit approval rules to reduce precedent risk.",
        "Strategic fit is stronger than average because this account can unlock a visible enterprise reference.",
        "Commercial downside can be constrained if finance signs off on a floor and renewal guardrails before signature.",
    ],
    SCENARIO_ORG: [
        "The reorg can be staged after launch planning so changes to reporting lines do not break current delivery.",
        "Temporary ownership maps can be published before the shift so no cross-functional work drops on the floor.",
        "A trial window with explicit reversal criteria makes the change less permanent if execution gets worse.",
    ],
    SCENARIO_GENERIC: [
        "The team can reduce uncertainty by proving the highest-risk assumption before the final commitment.",
        "A narrower scope or pilot can preserve optionality while still generating useful evidence.",
        "Decision quality improves if ownership and review criteria are made explicit before action.",
    ],
}

SCENARIO_JUDGE_GUIDANCE = {
    SCENARIO_DEPLOY: {
        "missing_context": [
            "Deployment prep document or release checklist was not supplied.",
            "Delay cost is still unknown: what is the customer or revenue impact of waiting until tomorrow?",
            "Blast radius is not quantified: affected users, transactions, and revenue exposure are still missing.",
            "Comparable hotfix history is missing: there is no reference to prior success or failure rates for similar changes.",
        ],
        "reasoning": {
            "proceed": "The change is still high-stakes, but operational controls are specific enough to allow a bounded release.",
            "proceed_with_caution": "The change may be worth making, but release readiness still depends on proving rollback and guardrails.",
            "reject": "The current release plan leaves too much operational downside unresolved for a safe production push.",
        },
        "next_actions": {
            "proceed": [
                "Run one staging rollback drill before the production window.",
                "Ship behind a canary or staged rollout with explicit abort thresholds.",
                "Name the on-call owner and confirm monitoring dashboards before rollout.",
            ],
            "proceed_with_caution": [
                "Run one staging rollback drill before approving production rollout.",
                "Define explicit blast-radius limits and abort thresholds for the first release window.",
                "Confirm on-call ownership and monitoring before launch.",
            ],
            "reject": [
                "Pause rollout until rollback has been exercised successfully in staging.",
                "Shrink blast radius with a canary or staged rollout plan.",
                "Do not ship until monitoring, abort thresholds, and ownership are explicit.",
            ],
        },
        "upgrade_condition": {
            "proceed": "Rollback drill passes and staged rollout guardrails are confirmed.",
            "proceed_with_caution": "Rollback is proven in staging and release is constrained with explicit abort thresholds.",
            "reject": "A tested rollback path plus staged rollout guardrails are in place.",
        },
        "downgrade_condition": {
            "proceed": "If rollback requires manual repair or monitoring remains incomplete, downgrade immediately.",
            "proceed_with_caution": "If rollback is untested or blast radius remains broad, downgrade to reject.",
            "reject": "Any new sign that the change touches revenue flows without clear rollback keeps this at reject.",
        },
    },
    SCENARIO_PRICING: {
        "missing_context": [
            "Commercial context is incomplete: no finance memo or margin floor was supplied.",
            "Precedent review is missing: there is no written rule for why this account qualifies as an exception.",
            "Evidence quality is still thin: comparable deal history or renewal impact was not supplied.",
        ],
        "reasoning": {
            "proceed": "The upside is real and the exception can be bounded tightly enough to avoid creating an uncontrolled precedent.",
            "proceed_with_caution": "The account may justify an exception, but precedent and evidence risk still need tighter controls.",
            "reject": "The commercial case is still too weak relative to the precedent risk and unclear guardrails.",
        },
        "next_actions": {
            "proceed": [
                "Document why this account qualifies as an exception and who approved it.",
                "Time-box the exception to a single contract or renewal window.",
                "Set a minimum margin floor with finance before signature.",
            ],
            "proceed_with_caution": [
                "Require finance approval on a minimum acceptable margin before signing.",
                "Limit the exception to one contract term with explicit renewal rules.",
                "Write down why this account is strategically exceptional so sales can defend the precedent.",
            ],
            "reject": [
                "Do not approve until finance confirms the downside is acceptable.",
                "Narrow the exception scope so it cannot become a default discount path.",
                "Gather stronger evidence that the account has strategic value beyond short-term revenue.",
            ],
        },
        "upgrade_condition": {
            "proceed": "Finance signs off on the floor and the exception is clearly time-boxed.",
            "proceed_with_caution": "The deal has a signed-off margin floor and written precedent guardrails.",
            "reject": "The account shows strategic upside that materially exceeds precedent cost and has clear guardrails.",
        },
        "downgrade_condition": {
            "proceed": "If other accounts can demand the same terms without review, downgrade.",
            "proceed_with_caution": "If finance cannot support the margin floor or precedent guardrails are weak, downgrade to reject.",
            "reject": "Any new evidence of broader discount contagion keeps this at reject.",
        },
    },
    SCENARIO_ORG: {
        "missing_context": [
            "Launch timeline and dependency map were not supplied.",
            "Current and proposed ownership maps are missing.",
            "No reversible transition plan or prior reorg evidence was supplied.",
        ],
        "reasoning": {
            "proceed": "The structure change may help, but only if execution continuity is protected through launch-critical work.",
            "proceed_with_caution": "The case for better ownership is real, but launch timing and transition cost still make this fragile.",
            "reject": "The timing and disruption risks are too high relative to the still-unclear execution benefits.",
        },
        "next_actions": {
            "proceed": [
                "Publish a temporary ownership map before any reporting-line changes.",
                "Protect launch-critical work by delaying nonessential transitions until after the key milestone.",
                "Define reversal criteria in case execution quality drops.",
            ],
            "proceed_with_caution": [
                "Delay structural changes until launch-critical milestones are protected.",
                "Create a temporary ownership map for cross-functional work before reassigning teams.",
                "Define measurable reversal criteria before the change goes live.",
            ],
            "reject": [
                "Do not change the org before launch-critical work is stable.",
                "Clarify ownership gaps and transition steps before revisiting the reorg.",
                "Reassess after launch when timing pressure is lower.",
            ],
        },
        "upgrade_condition": {
            "proceed": "Ownership remains explicit and launch-critical work stays protected during the transition.",
            "proceed_with_caution": "A staged transition plan and reversible trial window are documented.",
            "reject": "The launch window passes and the team can show a reversible transition plan with clear ownership.",
        },
        "downgrade_condition": {
            "proceed": "If launch work loses clear ownership or timing slips, downgrade immediately.",
            "proceed_with_caution": "If the transition creates ownership ambiguity or launch risk increases, downgrade to reject.",
            "reject": "Any new sign of launch-critical disruption keeps this at reject.",
        },
    },
    SCENARIO_GENERIC: {
        "missing_context": [
            "Supporting background or decision packet was not supplied.",
            "Success and downside criteria are still implicit rather than documented.",
            "There is no prior evidence or precedent attached to the decision.",
        ],
        "reasoning": {
            "proceed": "The case is acceptable, but only because the remaining uncertainty appears bounded and reversible.",
            "proceed_with_caution": "The direction may still be right, but missing evidence prevents a stronger recommendation.",
            "reject": "The unresolved downside still outweighs the current evidence for action.",
        },
        "next_actions": {
            "proceed": [
                "Document the highest-risk assumption and who owns validating it.",
                "Keep the first step reversible so downside stays bounded.",
                "Review the decision again once the next evidence gate is complete.",
            ],
            "proceed_with_caution": [
                "Prove the highest-risk assumption before broad commitment.",
                "Limit the first step so the decision remains reversible.",
                "Set a clear next gate for revisiting the recommendation.",
            ],
            "reject": [
                "Pause action until the top uncertainty is resolved.",
                "Narrow scope to a reversible pilot if progress is still needed.",
                "Reassess once evidence quality materially improves.",
            ],
        },
        "upgrade_condition": {
            "proceed": "The next evidence gate confirms the main assumption without increasing downside.",
            "proceed_with_caution": "The highest-risk assumption is validated with concrete evidence.",
            "reject": "Evidence quality improves enough to bound downside and preserve reversibility.",
        },
        "downgrade_condition": {
            "proceed": "Any new evidence that makes the choice harder to reverse should lower the recommendation.",
            "proceed_with_caution": "If new downside appears or reversibility worsens, downgrade to reject.",
            "reject": "Any evidence that further weakens reversibility keeps this at reject.",
        },
    },
}

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
        '{"score": 78, "dimensions": {"market_size": 16, "timing": 15, "moat": 12, '
        '"execution": 17, "revenue": 18}, "summary": "Promising opportunity with strong upside, but still meaningful execution and market risk.", '
        '"confidence": 0.75, "speculation_tags": []}'
    ),
    "critic": (
        '{"challenges": ["Market is more competitive than assessed", '
        '"Revenue timeline is optimistic", "Technical complexity underestimated"], '
        '"severity": "medium", "confidence": 0.80}'
    ),
    "judge": (
        '{"verdict": "proceed_with_caution", "score_delta": -21, '
        '"reasoning": "The direction may still be worth pursuing, but several unresolved risks materially reduce readiness. '
        'Proceed only after the next gate addresses the highest-severity gaps.", '
        '"missing_context": ["Supporting background or decision packet was not supplied."], '
        '"next_actions": ["Resolve the top concern before acting."], '
        '"upgrade_condition": "The top concern is resolved with evidence.", '
        '"downgrade_condition": "New downside appears or reversibility worsens.", "confidence": 0.72}'
    ),
    "default": (
        '{"status": "ok", "response": "Task completed successfully.", "confidence": 0.70}'
    ),
}

SCENARIO_ANALYST_TEMPLATES = {
    SCENARIO_DEPLOY: {
        "dimensions": {
            "impact": 18,
            "readiness": 15,
            "rollback": 12,
            "blast_radius": 10,
            "evidence": 17,
        },
        "summary": (
            "Meaningful operational value is available, but deployment readiness "
            "and rollback confidence are not yet strong enough for an easy approval."
        ),
        "confidence": 0.77,
    },
    SCENARIO_PRICING: {
        "dimensions": {
            "upside": 17,
            "precedent_risk": 11,
            "reversibility": 13,
            "evidence": 12,
            "strategic_fit": 18,
        },
        "summary": (
            "The commercial upside is real, but precedent risk and limited evidence "
            "make this harder to approve cleanly without stronger guardrails."
        ),
        "confidence": 0.74,
    },
    SCENARIO_ORG: {
        "dimensions": {
            "clarity": 16,
            "disruption": 8,
            "timing": 9,
            "reversibility": 10,
            "execution_risk": 11,
        },
        "summary": (
            "The reorganization could improve ownership clarity, but the timing and "
            "disruption risk make it a harder call right before a major launch."
        ),
        "confidence": 0.72,
    },
    SCENARIO_GENERIC: {
        "dimensions": {
            "impact": 16,
            "readiness": 14,
            "risk": 13,
            "evidence": 13,
            "reversibility": 15,
        },
        "summary": (
            "There is a plausible case for action, but the evidence is still mixed "
            "enough that the decision benefits from deeper review."
        ),
        "confidence": 0.70,
    },
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


def _rng_for(messages: list[dict], role: str) -> random.Random:
    prompt_text = _extract_message_text(messages)
    seed_material = f"{role}::{prompt_text}".encode("utf-8")
    seed = int(hashlib.sha256(seed_material).hexdigest()[:16], 16)
    return random.Random(seed)


def _detect_scenario(text: str) -> str:
    lowered = text.lower()

    deploy_signals = (
        "deploy", "rollout", "production", "hotfix", "rollback",
        "migration", "release", "ship this change", "ship the"
    )
    pricing_signals = (
        "pricing", "price", "discount", "exception", "enterprise account",
        "contract", "deal desk", "quote", "commercial"
    )
    org_signals = (
        "reorganize", "reorg", "vertical pods", "product and engineering",
        "team structure", "organization design", "org design", "pods", "pod structure",
        "pod ", "q4 launch"
    )

    if any(signal in lowered for signal in deploy_signals):
        return SCENARIO_DEPLOY
    if any(signal in lowered for signal in pricing_signals):
        return SCENARIO_PRICING
    if any(signal in lowered for signal in org_signals):
        return SCENARIO_ORG
    return SCENARIO_GENERIC


def _filter_missing_context(scenario: str, prompt_text: str, missing_context: list[str]) -> list[str]:
    lowered = prompt_text.lower()
    if scenario == SCENARIO_DEPLOY:
        checks = [
            (
                "Deployment prep document or release checklist was not supplied.",
                any(token in lowered for token in ("release-checklist", "release checklist", "deployment prep", "deploy checklist")),
            ),
            (
                "Delay cost is still unknown: what is the customer or revenue impact of waiting until tomorrow?",
                any(token in lowered for token in ("delay cost", "per hour", "hourly", "waiting until tomorrow", "cost of waiting")),
            ),
            (
                "Blast radius is not quantified: affected users, transactions, and revenue exposure are still missing.",
                any(token in lowered for token in ("affected users", "transactions", "revenue exposure", "blast radius", "sessions affected")),
            ),
            (
                "Comparable hotfix history is missing: there is no reference to prior success or failure rates for similar changes.",
                any(token in lowered for token in ("previous hotfix", "hotfix history", "prior hotfix", "historical", "success rate", "rollback rate")),
            ),
            (
                "Rollback evidence is still incomplete: no successful staging rollback drill was supplied.",
                any(
                    token in lowered
                    for token in (
                        "last staging rollback drill completed successfully",
                        "staging rollback drill completed successfully",
                        "rollback drill completed successfully",
                    )
                ),
            ),
            (
                "Abort thresholds are still incomplete: the release packet does not define a concrete rollback trigger.",
                any(
                    token in lowered
                    for token in (
                        "abort threshold:",
                        "error rate above 2 percent for 5 minutes",
                        "error rate > 2%",
                        "rollback if error rate",
                    )
                ),
            ),
            (
                "Night operations evidence is incomplete: on-call ownership or monitoring dashboard readiness was not supplied.",
                any(token in lowered for token in ("reviewed by on-call owner", "on-call owner", "oncall owner", "primary on-call"))
                and any(token in lowered for token in ("monitoring dashboards pinned", "dashboards pinned", "dashboard")),
            ),
        ]
        return [item for item, present in checks if not present]

    if scenario == SCENARIO_PRICING:
        checks = [
            (
                "Commercial context is incomplete: no finance memo or margin floor was supplied.",
                any(token in lowered for token in ("finance memo", "margin floor", "finance approval")),
            ),
            (
                "Precedent review is missing: there is no written rule for why this account qualifies as an exception.",
                any(token in lowered for token in ("precedent", "exception policy", "written rule", "guardrail")),
            ),
            (
                "Evidence quality is still thin: comparable deal history or renewal impact was not supplied.",
                any(token in lowered for token in ("comparable deal", "renewal impact", "deal history")),
            ),
        ]
        return [item for item, present in checks if not present]

    if scenario == SCENARIO_ORG:
        checks = [
            (
                "Launch timeline and dependency map were not supplied.",
                any(token in lowered for token in ("launch timeline", "dependency map", "critical path")),
            ),
            (
                "Current and proposed ownership maps are missing.",
                any(token in lowered for token in ("ownership map", "org chart", "responsibility map")),
            ),
            (
                "No reversible transition plan or prior reorg evidence was supplied.",
                any(token in lowered for token in ("transition plan", "reversible", "prior reorg", "reorg evidence")),
            ),
        ]
        return [item for item, present in checks if not present]

    return missing_context


def _deploy_context_signals(prompt_text: str) -> dict[str, bool]:
    lowered = prompt_text.lower()
    return {
        "checklist_present": any(
            token in lowered
            for token in (
                "release checklist reviewed",
                "deployment prep completed",
                "deploy checklist",
                "release checklist",
            )
        ),
        "canary_enabled": any(
            token in lowered
            for token in (
                "canary rollout enabled",
                "canary release",
                "10 percent of traffic",
                "10% of traffic",
            )
        ),
        "rollback_runbook_present": any(
            token in lowered
            for token in (
                "rollback runbook exists",
                "rollback runbook",
            )
        ),
        "rollback_drill_completed": any(
            token in lowered
            for token in (
                "last staging rollback drill completed successfully",
                "staging rollback drill completed successfully",
                "rollback drill completed successfully",
            )
        ),
        "abort_threshold_defined": any(
            token in lowered
            for token in (
                "abort threshold:",
                "error rate above 2 percent for 5 minutes",
                "error rate > 2%",
                "rollback if error rate",
            )
        ),
        "oncall_confirmed": any(
            token in lowered
            for token in (
                "reviewed by on-call owner",
                "rollback owner:",
                "on-call owner",
                "oncall owner",
                "primary on-call",
            )
        ),
        "dashboards_pinned": any(
            token in lowered
            for token in (
                "monitoring dashboards pinned",
                "dashboards pinned",
                "dashboard",
            )
        ),
        "delay_cost_known": any(
            token in lowered
            for token in (
                "delay cost:",
                "per hour",
                "12000 usd",
                "$12,000",
                "waiting until tomorrow",
            )
        ),
        "blast_radius_quantified": any(
            token in lowered
            for token in (
                "affected users:",
                "transactions:",
                "revenue exposure:",
                "1800 sign-in attempts",
                "950 billing-related transactions",
                "42000 usd",
            )
        ),
        "hotfix_history_known": any(
            token in lowered
            for token in (
                "previous hotfix history:",
                "5 comparable auth hotfixes",
                "4 successful, 1 rollback",
                "success rate",
            )
        ),
    }


def _build_deploy_analyst_response(prompt_text: str) -> dict:
    signals = _deploy_context_signals(prompt_text)

    impact = 18 if signals["delay_cost_known"] else 15
    readiness = 10
    readiness += 2 if signals["checklist_present"] else 0
    readiness += 2 if signals["canary_enabled"] else 0
    readiness += 1 if signals["oncall_confirmed"] else 0
    rollback = 8
    rollback += 3 if signals["rollback_runbook_present"] else 0
    rollback += 3 if signals["rollback_drill_completed"] else 0
    rollback += 2 if signals["abort_threshold_defined"] else 0
    blast_radius = 8
    blast_radius += 2 if signals["blast_radius_quantified"] else 0
    blast_radius += 2 if signals["canary_enabled"] else 0
    evidence = 9
    evidence += 3 if signals["delay_cost_known"] else 0
    evidence += 3 if signals["blast_radius_quantified"] else 0
    evidence += 3 if signals["hotfix_history_known"] else 0

    dimensions = {
        "impact": min(20, impact),
        "readiness": min(20, readiness),
        "rollback": min(20, rollback),
        "blast_radius": min(20, blast_radius),
        "evidence": min(20, evidence),
    }
    score = sum(dimensions.values())

    if signals["rollback_drill_completed"] and signals["abort_threshold_defined"] and signals["oncall_confirmed"]:
        summary = (
            "The hotfix addresses a meaningful business problem and the operating plan is materially stronger with "
            "rollback, threshold, and on-call details attached, but billing-auth still carries a broad production blast radius."
        )
    elif signals["rollback_runbook_present"] or signals["checklist_present"]:
        summary = (
            "Meaningful operational value is available, and some release controls exist, but deployment readiness "
            "still depends on proving rollback, guardrails, and first-hour operational discipline."
        )
    else:
        summary = (
            "Meaningful operational value is available, but deployment readiness and rollback confidence are not yet "
            "strong enough for an easy approval."
        )

    confidence = 0.74
    confidence += 0.02 if signals["blast_radius_quantified"] else 0.0
    confidence += 0.02 if signals["hotfix_history_known"] else 0.0
    confidence += 0.02 if signals["rollback_drill_completed"] else 0.0

    return {
        "score": score,
        "dimensions": dimensions,
        "summary": summary,
        "confidence": min(0.84, round(confidence, 2)),
        "scenario": SCENARIO_DEPLOY,
        "speculation_tags": [],
    }


def _build_deploy_challenges(prompt_text: str) -> list[str]:
    signals = _deploy_context_signals(prompt_text)
    challenges: list[str] = []

    if not signals["rollback_drill_completed"]:
        challenges.append(
            "Rollback has not been rehearsed on a staging environment that mirrors production."
        )
    else:
        challenges.append(
            "A successful staging rollback drill helps, but it still does not prove production parity for a billing-auth change."
        )

    if not signals["blast_radius_quantified"]:
        challenges.append(
            "Blast radius is still broad because billing-auth touches login, entitlements, and revenue events."
        )
    else:
        challenges.append(
            "Even with quantified exposure, billing-auth still affects a wide and economically sensitive production surface."
        )

    if not (signals["abort_threshold_defined"] and signals["oncall_confirmed"] and signals["dashboards_pinned"]):
        challenges.append(
            "Monitoring, ownership, and abort thresholds are not yet explicit enough for an overnight production change."
        )
    else:
        challenges.append(
            "Night deployment still depends on fast human execution, so monitoring and abort discipline must hold under real production pressure."
        )

    return challenges


def _build_deploy_defenses(prompt_text: str) -> list[str]:
    signals = _deploy_context_signals(prompt_text)
    defenses: list[str] = []

    if signals["rollback_drill_completed"]:
        defenses.append(
            "The rollback path has already been exercised successfully in staging, which materially reduces uncertainty around recovery."
        )
    elif signals["rollback_runbook_present"]:
        defenses.append(
            "A rollback runbook exists and can be validated with a staging drill before the production window opens."
        )
    else:
        defenses.append(
            "The team can still reduce release risk by writing a rollback path before the production window opens."
        )

    if signals["canary_enabled"] and signals["blast_radius_quantified"]:
        defenses.append(
            "The release can start with a canary and the quantified exposure makes it easier to judge whether the first-hour risk is acceptable."
        )
    elif signals["canary_enabled"]:
        defenses.append(
            "The change can be shipped behind a canary release so customer impact stays bounded during the first hour."
        )
    else:
        defenses.append(
            "A staged or canary rollout would reduce first-hour exposure for this production change."
        )

    if signals["abort_threshold_defined"] and signals["oncall_confirmed"] and signals["dashboards_pinned"]:
        defenses.append(
            "Abort thresholds, dashboard visibility, and on-call ownership are already documented, so the team has a concrete stop path if metrics move."
        )
    else:
        defenses.append(
            "On-call ownership and dashboards can be pre-assigned so the team has a clear abort path if metrics move."
        )

    return defenses


def _build_deploy_judge_response(prompt_text: str) -> dict:
    signals = _deploy_context_signals(prompt_text)

    readiness_complete = (
        signals["rollback_drill_completed"]
        and signals["abort_threshold_defined"]
        and signals["oncall_confirmed"]
        and signals["dashboards_pinned"]
    )
    evidence_strong = (
        signals["delay_cost_known"]
        and signals["blast_radius_quantified"]
        and signals["hotfix_history_known"]
    )

    if readiness_complete and evidence_strong:
        verdict = "proceed"
        score_delta = 8
    elif signals["rollback_runbook_present"] or signals["checklist_present"]:
        verdict = "proceed_with_caution"
        score_delta = -13
    else:
        verdict = "reject"
        score_delta = -34

    missing_context = _filter_missing_context(
        SCENARIO_DEPLOY,
        prompt_text,
        list(SCENARIO_JUDGE_GUIDANCE[SCENARIO_DEPLOY]["missing_context"]),
    )

    if verdict == "proceed":
        reasoning = (
            "The release still carries real production downside, but the attached materials show a tested rollback path, "
            "explicit abort thresholds, quantified exposure, and prior comparable history. That is enough to support a bounded rollout."
        )
        next_actions = [
            "Keep the canary rollout and first-hour monitoring in place during deployment.",
            "Confirm the on-call owner stays active through the initial release window.",
            "Document the post-release outcome so this hotfix becomes part of the comparable history set.",
        ]
        upgrade_condition = "A fresh production-readiness confirmation is recorded immediately before rollout."
        downgrade_condition = "If any readiness control is found stale or no longer applicable to tonight's build, downgrade immediately."
    elif verdict == "proceed_with_caution":
        reasoning = (
            "The change may still be worth making, but release readiness depends on closing the remaining operational gaps before rollout."
        )
        next_actions = [
            "Run one staging rollback drill before approving production rollout.",
            "Define explicit blast-radius limits and abort thresholds for the first release window.",
            "Confirm on-call ownership and monitoring before launch.",
        ]
        upgrade_condition = "Rollback is proven in staging and release is constrained with explicit abort thresholds."
        downgrade_condition = "If rollback is untested or blast radius remains broad, downgrade to reject."
    else:
        reasoning = (
            "The current release plan leaves too much operational downside unresolved for a safe production push."
        )
        next_actions = [
            "Pause rollout until rollback has been exercised successfully in staging.",
            "Shrink blast radius with a canary or staged rollout plan.",
            "Do not ship until monitoring, abort thresholds, and ownership are explicit.",
        ]
        upgrade_condition = "A tested rollback path plus staged rollout guardrails are in place."
        downgrade_condition = "Any new sign that the change touches revenue flows without clear rollback keeps this at reject."

    return {
        "verdict": verdict,
        "score_delta": score_delta,
        "reasoning": reasoning,
        "missing_context": missing_context,
        "next_actions": next_actions,
        "upgrade_condition": upgrade_condition,
        "downgrade_condition": downgrade_condition,
        "confidence": 0.82 if verdict == "proceed" else 0.76 if verdict == "proceed_with_caution" else 0.74,
    }


def _generate_analyst_response(messages: list[dict]) -> dict:
    prompt_text = _extract_message_text(messages)
    scenario = _detect_scenario(prompt_text)
    if scenario == SCENARIO_DEPLOY:
        return _build_deploy_analyst_response(prompt_text)
    template = SCENARIO_ANALYST_TEMPLATES[scenario]
    dimensions = template["dimensions"]
    score = sum(dimensions.values())

    payload = {
        "score": score,
        "dimensions": dimensions,
        "summary": template["summary"],
        "confidence": template["confidence"],
        "scenario": scenario,
        "speculation_tags": [],
    }
    return payload


# ---------------------------------------------------------------------------
# Response generators — one per debate role.
# ---------------------------------------------------------------------------

def _generate_challenger_response(messages: list[dict]) -> dict:
    """Return scenario-aware challenges when possible, else fallback to legacy pool."""
    prompt_text = _extract_message_text(messages)
    scenario = _detect_scenario(prompt_text)
    rng = _rng_for(messages, "challenger")
    if scenario == SCENARIO_DEPLOY:
        return {
            "challenges": _build_deploy_challenges(prompt_text),
            "severity": "high",
            "confidence": round(rng.uniform(0.74, 0.9), 2),
        }
    if scenario in SCENARIO_CHALLENGES:
        return {
            "challenges": list(SCENARIO_CHALLENGES[scenario]),
            "severity": "high" if scenario in {SCENARIO_DEPLOY, SCENARIO_PRICING} else "medium",
            "confidence": round(rng.uniform(0.74, 0.9), 2),
        }

    by_category: dict[str, list[dict]] = {}
    for t in CHALLENGE_TEMPLATES:
        by_category.setdefault(t["category"], []).append(t)

    categories = list(by_category.keys())
    rng.shuffle(categories)
    selected: list[dict] = []
    for cat in categories:
        if len(selected) >= 3:
            break
        selected.append(rng.choice(by_category[cat]))

    if len(selected) < 3:
        remaining = [t for t in CHALLENGE_TEMPLATES if t not in selected]
        selected.extend(rng.sample(remaining, 3 - len(selected)))

    return {
        "challenges": [tpl["challenge_text"] for tpl in selected],
        "severity": max(tpl["severity"] for tpl in selected),
        "confidence": round(rng.uniform(0.72, 0.92), 2),
    }


def _generate_defender_response(messages: list[dict]) -> dict:
    """Parse prior messages for challenge categories and produce defenses."""
    prior_text = _extract_message_text(messages).lower()
    scenario = _detect_scenario(prior_text)
    rng = _rng_for(messages, "defender")
    if scenario == SCENARIO_DEPLOY:
        return {
            "defenses": _build_deploy_defenses(prior_text),
            "confidence": round(rng.uniform(0.68, 0.86), 2),
        }
    if scenario in SCENARIO_DEFENSES:
        return {
            "defenses": list(SCENARIO_DEFENSES[scenario]),
            "confidence": round(rng.uniform(0.68, 0.86), 2),
        }

    # Identify which categories were raised.
    matched_categories: list[str] = []
    for cat in DEFENSE_TEMPLATES:
        # Match on the category name (underscores replaced with spaces too).
        if cat in prior_text or cat.replace("_", " ") in prior_text:
            matched_categories.append(cat)

    # Fallback: if nothing matched, pick 3 random categories so we always
    # return something useful.
    if not matched_categories:
        matched_categories = rng.sample(
            list(DEFENSE_TEMPLATES.keys()), min(3, len(DEFENSE_TEMPLATES))
        )

    defenses = []
    for cat in matched_categories:
        tpl = rng.choice(DEFENSE_TEMPLATES[cat])
        defenses.append(tpl["defense_text"])

    return {
        "defenses": defenses,
        "confidence": round(rng.uniform(0.68, 0.88), 2),
    }


def _generate_judge_response(messages: list[dict]) -> dict:
    """Weighted random verdict with scenario-aware follow-up guidance."""
    prompt_text = _extract_message_text(messages)
    scenario = _detect_scenario(prompt_text)
    if scenario == SCENARIO_DEPLOY:
        return _build_deploy_judge_response(prompt_text)
    rng = _rng_for(messages, "judge")
    verdict = rng.choices(
        ["proceed", "proceed_with_caution", "reject"],
        weights=[30, 50, 20],
        k=1,
    )[0]

    delta_options = {
        "proceed": [0, 8],
        "proceed_with_caution": [-13, -21],
        "reject": [-34, -21],
    }
    score_delta = rng.choice(delta_options[verdict])

    guidance = SCENARIO_JUDGE_GUIDANCE[scenario]
    missing_context = _filter_missing_context(
        scenario,
        prompt_text,
        list(guidance["missing_context"]),
    )

    return {
        "verdict": verdict,
        "score_delta": score_delta,
        "reasoning": guidance["reasoning"][verdict],
        "missing_context": missing_context,
        "next_actions": guidance["next_actions"][verdict],
        "upgrade_condition": guidance["upgrade_condition"][verdict],
        "downgrade_condition": guidance["downgrade_condition"][verdict],
        "confidence": round(rng.uniform(0.60, 0.85), 2),
    }


# ---------------------------------------------------------------------------
# Validator — lightweight schema check on generated responses.
# ---------------------------------------------------------------------------

_EXPECTED_KEYS: dict[str, set[str]] = {
    "challenger": {"challenges", "severity", "confidence"},
    "defender": {"defenses", "confidence"},
    "judge": {
        "verdict",
        "score_delta",
        "reasoning",
        "missing_context",
        "next_actions",
        "upgrade_condition",
        "downgrade_condition",
        "confidence",
    },
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

        # Use strict markers from the debate engine prompts to avoid false positives
        # when supporting documents mention words like "verdict" or "defense".
        if "evaluate the debate and return verdict" in user_text and "initial score:" in user_text:
            return "judge"
        if "generate exactly 3 specific challenges" in user_text:
            return "challenger"
        if "provide a defense for each challenge" in user_text:
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
            elif role == "analyst":
                content = json.dumps(_generate_analyst_response(messages))
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
            "analyst": lambda: _generate_analyst_response(messages),
            "challenger": lambda: _generate_challenger_response(messages),
            "defender": lambda: _generate_defender_response(messages),
            "judge": lambda: _generate_judge_response(messages),
        }

        generate = generators[debate_role]

        for _ in range(_max_attempts):
            payload = generate()
            if _validate_response(debate_role, payload):
                return json.dumps(payload)

        # Final fallback — should never be reached in practice.
        fallback = {
            "challenger": {
                "challenges": [
                    "Insufficient data to validate core assumptions.",
                    "Risk factors have not been adequately addressed.",
                    "Market conditions may not support the proposed approach.",
                ],
                "severity": "medium",
                "confidence": 0.30,
            },
            "defender": {
                "defenses": [
                    "The core approach is grounded in established patterns.",
                    "Risk mitigation strategies are in place.",
                    "Market analysis supports the general direction.",
                ],
                "confidence": 0.30,
            },
            "judge": {
                "verdict": "proceed_with_caution",
                "score_delta": 0,
                "reasoning": "Insufficient data to render a confident verdict.",
                "missing_context": ["Supporting background or decision packet was not supplied."],
                "next_actions": ["Gather clearer evidence before acting."],
                "upgrade_condition": "The top concern is resolved with concrete evidence.",
                "downgrade_condition": "New downside appears or reversibility worsens.",
                "confidence": 0.50,
            },
        }
        return json.dumps(fallback[debate_role])
