from __future__ import annotations

from dataclasses import dataclass


SCENARIO_DEPLOY = "deploy"
SCENARIO_PRICING = "pricing"
SCENARIO_ORG = "org_design"
SCENARIO_GENERIC = "generic"


@dataclass(frozen=True)
class ScenarioRubric:
    key: str
    dimensions: tuple[str, str, str, str, str]
    description: str


RUBRICS: dict[str, ScenarioRubric] = {
    SCENARIO_DEPLOY: ScenarioRubric(
        key=SCENARIO_DEPLOY,
        dimensions=("impact", "readiness", "rollback", "blast_radius", "evidence"),
        description="deployment and production-change decisions",
    ),
    SCENARIO_PRICING: ScenarioRubric(
        key=SCENARIO_PRICING,
        dimensions=("upside", "precedent_risk", "reversibility", "evidence", "strategic_fit"),
        description="pricing, discount, and commercial exception decisions",
    ),
    SCENARIO_ORG: ScenarioRubric(
        key=SCENARIO_ORG,
        dimensions=("clarity", "disruption", "timing", "reversibility", "execution_risk"),
        description="reorg, pod, and organization-design decisions",
    ),
    SCENARIO_GENERIC: ScenarioRubric(
        key=SCENARIO_GENERIC,
        dimensions=("impact", "readiness", "risk", "evidence", "reversibility"),
        description="general high-stakes decisions",
    ),
}


def detect_scenario(topic: str) -> str:
    lowered = topic.lower()

    if any(token in lowered for token in (
        "deploy", "rollout", "production", "hotfix", "rollback", "migration", "release"
    )):
        return SCENARIO_DEPLOY

    if any(token in lowered for token in (
        "pricing", "price", "discount", "exception", "enterprise account", "contract", "commercial"
    )):
        return SCENARIO_PRICING

    if any(token in lowered for token in (
        "reorganize", "reorg", "vertical pods", "pod structure", "team structure",
        "organization design", "org design", "pods", "pod "
    )):
        return SCENARIO_ORG

    return SCENARIO_GENERIC


def rubric_for_topic(topic: str) -> ScenarioRubric:
    return RUBRICS[detect_scenario(topic)]


def build_analyst_prompt(topic: str) -> str:
    rubric = rubric_for_topic(topic)
    dims = ", ".join(rubric.dimensions)
    return (
        f"Evaluate this decision for {rubric.description}. "
        f"Use a 0-100 score across exactly 5 dimensions: {dims}. "
        f"Score each dimension from 0-20 and return JSON with: "
        f"score, dimensions dict, summary, confidence (0-1), and scenario. "
        f"If supporting context is thin, reflect that in the score and summary rather than assuming missing facts. "
        f"Decision: {topic}"
    )
