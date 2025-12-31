from dataclasses import dataclass
from typing import Callable, List, Any


@dataclass
class InvariantDefinition:
    # metadata for each invariant check
    name: str
    description: str
    why_exists: str
    risk_mitigated: str
    failure_action: str
    threshold: float


# all the invariant definitions in one place

SCHEMA_VALIDITY = InvariantDefinition(
    name="schema_validity",
    description="percentage of items with valid schema",
    why_exists="parser outputs power downstream features and if schema is bad everything breaks",
    risk_mitigated="app crashes corrupted health records broken integrations",
    failure_action="rate below 95% block batch and alert engineering - below 80% trigger incident",
    threshold=0.95
)

EVIDENCE_VALIDITY = InvariantDefinition(
    name="evidence_validity",
    description="percentage of items whose evidence span exists in source journal",
    why_exists="extractions must be grounded in actual user words - fabricated evidence in health app is dangerous",
    risk_mitigated="health anxiety from false positives incorrect self care erosion of trust",
    failure_action="rate below 90% queue for clinician review - below 80% block batch investigate model",
    threshold=0.90
)

HALLUCINATION_RATE = InvariantDefinition(
    name="hallucination_rate",
    description="percentage of items with evidence span NOT found in source",
    why_exists="direct measure of fabricated content - hallucinated symptoms could cause unnecessary alarm",
    risk_mitigated="false health signals anxiety incorrect tracking potential clinical harm",
    failure_action="rate above 5% escalate to clinical review - above 10% block batch trigger incident",
    threshold=0.05
)

CONTRADICTION_RATE = InvariantDefinition(
    name="contradiction_rate",
    description="rate of same evidence span with conflicting polarity",
    why_exists="contradictions are especially harmful - telling user cramps present AND absent destroys trust",
    risk_mitigated="user confusion incorrect health decisions clinical harm liability",
    failure_action="any contradiction flag both items for human review - rate above 1% alert engineering",
    threshold=0.01
)


ALL_INVARIANTS = [
    SCHEMA_VALIDITY,
    EVIDENCE_VALIDITY,
    HALLUCINATION_RATE,
    CONTRADICTION_RATE
]
