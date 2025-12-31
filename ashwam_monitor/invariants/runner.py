from typing import List, Dict
from datetime import datetime
import uuid

from ..models.inputs import ParserOutput
from ..models.outputs import InvariantReport, InvariantViolation, InvariantDefinition as OutputDef
from ..models.enums import AlertLevel
from ..config import config

from .schema_checker import compute_schema_validity
from .evidence_checker import find_hallucinations, compute_evidence_validity
from .contradiction_checker import find_contradictions
from .definitions import ALL_INVARIANTS


def run_invariant_checks(
    outputs: List[ParserOutput],
    journals: Dict[str, str]
) -> InvariantReport:
    # run all invariant checks and build a report
    run_id = f"inv-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    total_items = sum(len(o.items) for o in outputs)
    total_journals = len(outputs)

    schema_rate, schema_violations = compute_schema_validity(outputs)
    evidence_rate, evidence_violations = compute_evidence_validity(outputs, journals)
    hall_rate, hallucinations, hall_clusters = find_hallucinations(outputs, journals)
    contra_rate, contradictions = find_contradictions(outputs)

    violations = []

    for v in schema_violations:
        violations.append(InvariantViolation(
            journal_id=v["journal_id"],
            item_index=v["item_index"],
            invariant_name="schema_validity",
            violation_type="schema_error",
            details="; ".join(v["errors"]),
            severity=AlertLevel.WARNING
        ))

    for h in hallucinations:
        violations.append(InvariantViolation(
            journal_id=h["journal_id"],
            item_index=h["item_index"],
            invariant_name="hallucination",
            violation_type="evidence_not_found",
            details=f"span '{h['evidence_span']}' not in source",
            severity=AlertLevel.CRITICAL
        ))

    for c in contradictions:
        for item in c["conflicting_items"]:
            violations.append(InvariantViolation(
                journal_id=c["journal_id"],
                item_index=item["index"],
                invariant_name="contradiction",
                violation_type="polarity_conflict",
                details=f"span '{c['evidence_span']}' has conflicting polarity",
                severity=AlertLevel.CRITICAL
            ))

    alerts = []
    thresholds = config.invariants

    if schema_rate < thresholds.min_schema_validity:
        alerts.append(f"CRITICAL: schema validity {schema_rate:.1%} below threshold {thresholds.min_schema_validity:.0%}")

    if hall_rate > thresholds.max_hallucination_rate:
        alerts.append(f"CRITICAL: hallucination rate {hall_rate:.1%} exceeds threshold {thresholds.max_hallucination_rate:.0%}")

    if contra_rate > thresholds.max_contradiction_rate:
        alerts.append(f"CRITICAL: contradiction rate {contra_rate:.1%} exceeds threshold {thresholds.max_contradiction_rate:.0%}")

    for span, count in hall_clusters.items():
        if count > 1:
            alerts.append(f"WARNING: systematic hallucination '{span}' appears {count} times")

    # convert definitions to output format
    defs = [
        OutputDef(
            name=d.name,
            description=d.description,
            why_exists=d.why_exists,
            risk_mitigated=d.risk_mitigated,
            failure_action=d.failure_action,
            threshold=d.threshold
        )
        for d in ALL_INVARIANTS
    ]

    return InvariantReport(
        timestamp=datetime.now(),
        run_id=run_id,
        total_items=total_items,
        total_journals=total_journals,
        schema_validity_rate=schema_rate,
        evidence_validity_rate=evidence_rate,
        hallucination_rate=hall_rate,
        contradiction_rate=contra_rate,
        violations=violations,
        alerts=alerts,
        thresholds_used={
            "min_schema_validity": thresholds.min_schema_validity,
            "min_evidence_validity": thresholds.min_evidence_validity,
            "max_hallucination_rate": thresholds.max_hallucination_rate,
            "max_contradiction_rate": thresholds.max_contradiction_rate
        },
        definitions=defs
    )
