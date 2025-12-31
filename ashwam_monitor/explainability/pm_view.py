from datetime import datetime
from typing import Optional

from ..models.outputs import InvariantReport, DriftReport, CanaryReport
from .templates import PM_TEMPLATE


def get_status_emoji(report: InvariantReport, drift: DriftReport = None, canary: CanaryReport = None) -> str:
    # determine overall status
    critical_count = sum(1 for a in report.alerts if "CRITICAL" in a)
    if critical_count > 0:
        return "🔴 CRITICAL"
    if canary and canary.action.value == "ROLLBACK":
        return "🔴 CRITICAL"
    elif report.hallucination_rate > 0.05:
        return "🟡 DEGRADED"
    return "🟢 HEALTHY"


def format_metric(name: str, value: float, threshold: float = None, is_rate: bool = True) -> dict:
    # format a single metric for display
    if is_rate:
        val_str = f"{value:.1%}"
    else:
        val_str = f"{value:.2f}"

    status = "✓"
    if threshold and is_rate:
        if name.startswith("hallucination") or name.startswith("contradiction"):
            if value > threshold:
                status = "⚠️"
        else:
            if value < threshold:
                status = "⚠️"

    return {"name": name, "value": val_str, "status": status}


def generate_pm_view(
    invariant: InvariantReport, 
    drift: Optional[DriftReport] = None,
    canary: Optional[CanaryReport] = None
) -> str:
    # generate pm focused dashboard with system health and risk signals
    status = get_status_emoji(invariant, drift, canary)

    metrics = [
        format_metric("hallucination_rate", invariant.hallucination_rate, 0.05),
        format_metric("contradiction_rate", invariant.contradiction_rate, 0.01),
        format_metric("evidence_validity", invariant.evidence_validity_rate, 0.90),
        format_metric("schema_validity", invariant.schema_validity_rate, 0.95),
    ]

    if drift:
        for m in drift.metrics:
            metrics.append({
                "name": m.name,
                "value": f"{m.current_value:.2f}",
                "status": "⚠️" if m.status.value != "STABLE" else "✓"
            })

    if canary:
        metrics.append({
            "name": "canary_f1",
            "value": f"{canary.f1:.1%}",
            "status": "⚠️" if canary.f1 < 0.5 else "✓"
        })

    # combine alerts
    alerts = invariant.alerts[:]
    if drift:
        alerts.extend(drift.alerts)

    # generate actions
    actions = []
    if invariant.hallucination_rate > 0.05:
        actions.append("review prompt for hallucination patterns")
    if invariant.contradiction_rate > 0.01:
        actions.append("investigate contradiction source")
    if drift and any(m.status.value == "BREAKAGE" for m in drift.metrics):
        actions.append("consider model rollback")
    if canary and canary.action.value == "HUMAN_REVIEW":
        actions.append("queue canary journals for clinical review")
    if canary and canary.action.value == "ROLLBACK":
        actions.append("immediate model rollback required")
    if not actions:
        actions.append("no immediate actions required")

    return PM_TEMPLATE.render(
        timestamp=invariant.timestamp.strftime("%Y-%m-%d %H:%M"),
        status=status,
        metrics=metrics,
        alerts=alerts,
        actions=actions
    )
