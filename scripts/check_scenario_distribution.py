#!/usr/bin/env python3
"""Check that scenario-aware scoring separates deploy, pricing, and org/design prompts."""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from adapters import MockAdapter
from constitution import BaseAgent, Constitution
from constitution.debate import score_band
from constitution.scenarios import rubric_for_topic


PROMPTS = {
    "deploy": [
        "Should we deploy the billing-auth hotfix to production tonight?",
        "Should we roll out the payments migration to production this evening?",
        "Should we release the auth-service hotfix before the weekend support window?",
    ],
    "pricing": [
        "Should we approve this pricing exception for a strategic enterprise account?",
        "Should we offer this custom discount to close the enterprise renewal?",
        "Should we approve a one-time commercial exception for this lighthouse customer?",
    ],
    "org_design": [
        "Should we reorganize product and engineering into vertical pods before the Q4 launch?",
        "Should we move into a pod structure before the platform launch milestone?",
        "Should we change team structure ahead of the launch and reorganize into pods?",
    ],
}


def main() -> None:
    rules = Constitution.default()
    analyst = BaseAgent(
        role="analyst",
        goal="Evaluate decisions with honest, calibrated, scenario-aware assessments.",
        adapter=MockAdapter(simulate_delay_ms=0),
        constitution=rules,
    )

    by_scenario: dict[str, list[int]] = {}

    print("Scenario-aware distribution check\n")
    for scenario, prompts in PROMPTS.items():
        scores: list[int] = []
        print(f"[{scenario}]")
        for prompt in prompts:
            rubric = rubric_for_topic(prompt)
            response = analyst.run(
                f"Evaluate this decision for {rubric.description}. "
                f"Use a 0-100 score across exactly 5 dimensions: {', '.join(rubric.dimensions)}. "
                f"Score each dimension from 0-20 and return JSON with: "
                f"score, dimensions dict, summary, confidence (0-1), and scenario. "
                f"Decision: {prompt}"
            )
            data = json.loads(response)
            score = int(data["score"])
            scores.append(score)
            dims = ", ".join(data["dimensions"].keys())
            print(f"- {score:>3} | {score_band(score):<10} | {data['scenario']:<10} | {dims}")
        by_scenario[scenario] = scores
        print(
            f"  avg={statistics.mean(scores):.1f} min={min(scores)} max={max(scores)} "
            f"bands={', '.join(score_band(score) for score in scores)}"
        )
        print()

    deploy_max = max(by_scenario["deploy"])
    pricing_max = max(by_scenario["pricing"])
    org_min = min(by_scenario["org_design"])
    org_max = max(by_scenario["org_design"])

    print("Separation summary")
    print(f"- deploy range:   {min(by_scenario['deploy'])}-{deploy_max}")
    print(f"- pricing range:  {min(by_scenario['pricing'])}-{pricing_max}")
    print(f"- org range:      {org_min}-{org_max}")
    print(
        f"- deploy/pricing above threshold: "
        f"{all(score >= 70 for score in by_scenario['deploy'] + by_scenario['pricing'])}"
    )
    print(f"- org below threshold: {all(score < 70 for score in by_scenario['org_design'])}")


if __name__ == "__main__":
    main()
