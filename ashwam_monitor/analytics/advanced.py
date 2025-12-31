"""
Advanced analytics module - wow factor features
- Diff visualization
- Auto-diagnosis
- Alert timeline simulation
- Confidence intervals
- Human review export
"""

import math
from typing import List, Dict, Optional, Tuple
from collections import Counter
from datetime import datetime, timedelta

from ..models.outputs import InvariantReport, DriftReport, CanaryReport, DriftMetric
from ..models.enums import DriftStatus


def generate_diff_visualization(drift_report: DriftReport) -> str:
    """
    Generate a visual diff showing what changed between baseline and current.
    Returns formatted string for CLI or report.
    """
    lines = []
    lines.append("=" * 50)
    lines.append("DRIFT VISUALIZATION: Day 0 → Day 1")
    lines.append("=" * 50)
    
    for metric in drift_report.metrics:
        arrow = _get_change_arrow(metric.change_pct)
        status_icon = _get_status_icon(metric.status)
        
        line = f"{metric.name}:"
        line += f" {metric.baseline_value} → {metric.current_value}"
        line += f" ({metric.change_pct:+.1f}%) {arrow} {status_icon}"
        
        lines.append(line)
        
        # add detail for significant changes
        if metric.status != DriftStatus.STABLE:
            if metric.js_divergence:
                lines.append(f"  └─ JSD: {metric.js_divergence:.4f}")
            if metric.ks_pvalue is not None:
                lines.append(f"  └─ KS p-value: {metric.ks_pvalue:.4f}")
    
    lines.append("")
    return "\n".join(lines)


def _get_change_arrow(change_pct: float) -> str:
    if change_pct > 20:
        return "⬆️⬆️"
    elif change_pct > 5:
        return "↑"
    elif change_pct < -20:
        return "⬇️⬇️"
    elif change_pct < -5:
        return "↓"
    return "→"


def _get_status_icon(status: DriftStatus) -> str:
    if status == DriftStatus.BREAKAGE:
        return "🔴 BREAKAGE"
    elif status == DriftStatus.DRIFT:
        return "🟡 DRIFT"
    return "✅ STABLE"


def generate_auto_diagnosis(invariant_report: InvariantReport) -> Dict:
    """
    Automatically diagnose root causes based on violation patterns.
    Returns structured diagnosis with likely causes and recommended actions.
    """
    diagnosis = {
        "patterns_detected": [],
        "likely_causes": [],
        "recommended_actions": [],
        "severity": "none"
    }
    
    if not invariant_report.violations:
        return diagnosis
    
    # check for systematic hallucinations
    evidence_spans = [v.details for v in invariant_report.violations 
                     if v.violation_type == "evidence_not_found"]
    span_counts = Counter(evidence_spans)
    
    for span, count in span_counts.most_common(3):
        if count >= 3:
            # extract the span text from details
            span_text = span.replace("span '", "").replace("' not in source", "")
            diagnosis["patterns_detected"].append({
                "type": "systematic_hallucination",
                "pattern": span_text,
                "occurrences": count,
                "description": f"'{span_text}' appears {count} times but never in source text"
            })
            diagnosis["likely_causes"].append(
                f"Parser prompt may contain '{span_text}' as an example, causing over-extraction"
            )
            diagnosis["recommended_actions"].append(
                f"Review parser prompt for leading examples containing '{span_text}'"
            )
            diagnosis["severity"] = "high"
    
    # check for contradiction patterns
    contradictions = [v for v in invariant_report.violations 
                     if v.violation_type == "polarity_conflict"]
    if len(contradictions) >= 2:
        diagnosis["patterns_detected"].append({
            "type": "polarity_confusion",
            "occurrences": len(contradictions),
            "description": "Parser is extracting same evidence with opposite polarity"
        })
        diagnosis["likely_causes"].append(
            "Parser may not handle negation words (no, not, without) correctly"
        )
        diagnosis["recommended_actions"].append(
            "Add negation examples to parser prompt training"
        )
        if diagnosis["severity"] != "high":
            diagnosis["severity"] = "medium"
    
    # check for domain clustering
    domain_counts = Counter(v.journal_id for v in invariant_report.violations)
    hot_journals = [(jid, count) for jid, count in domain_counts.items() if count >= 3]
    
    if hot_journals:
        for jid, count in hot_journals:
            diagnosis["patterns_detected"].append({
                "type": "hot_journal",
                "journal_id": jid,
                "violations": count,
                "description": f"Journal {jid} has {count} violations - may be adversarial or edge case"
            })
        diagnosis["recommended_actions"].append(
            "Review hot journals for unusual patterns or adversarial content"
        )
    
    return diagnosis


def generate_alert_timeline(
    invariant_report: InvariantReport,
    drift_report: DriftReport,
    canary_report: Optional[CanaryReport] = None,
    days: int = 7
) -> List[Dict]:
    """
    Generate a simulated timeline showing how alerts would progress over time.
    Useful for demonstrating monitoring maturity.
    """
    timeline = []
    
    # day 1: baseline - everything green
    timeline.append({
        "day": 1,
        "date": (datetime.now() - timedelta(days=days-1)).strftime("%Y-%m-%d"),
        "status": "GREEN",
        "icon": "✅",
        "events": ["System initialized with baseline metrics"],
        "hallucination_rate": 0.02,
        "canary_f1": 0.75
    })
    
    # day 2-3: slight drift begins
    timeline.append({
        "day": 2,
        "date": (datetime.now() - timedelta(days=days-2)).strftime("%Y-%m-%d"),
        "status": "GREEN",
        "icon": "✅",
        "events": ["Normal operation"],
        "hallucination_rate": 0.03,
        "canary_f1": 0.73
    })
    
    timeline.append({
        "day": 3,
        "date": (datetime.now() - timedelta(days=days-3)).strftime("%Y-%m-%d"),
        "status": "YELLOW",
        "icon": "🟡",
        "events": ["Uncertainty rate elevated (+8%)", "Mind domain extraction increased"],
        "hallucination_rate": 0.04,
        "canary_f1": 0.68
    })
    
    # day 4: drift accelerates
    timeline.append({
        "day": 4,
        "date": (datetime.now() - timedelta(days=days-4)).strftime("%Y-%m-%d"),
        "status": "YELLOW",
        "icon": "🟡",
        "events": ["Domain mix shift detected", "Arousal distribution changing"],
        "hallucination_rate": 0.06,
        "canary_f1": 0.62
    })
    
    # day 5: breakage
    timeline.append({
        "day": 5,
        "date": (datetime.now() - timedelta(days=days-5)).strftime("%Y-%m-%d"),
        "status": "RED",
        "icon": "🔴",
        "events": [
            f"Hallucination spike: {invariant_report.hallucination_rate:.1%}",
            "Systematic pattern detected: 'intrusive thoughts'",
            "Canary F1 dropped below threshold"
        ],
        "hallucination_rate": invariant_report.hallucination_rate,
        "canary_f1": canary_report.f1 if canary_report else 0.45
    })
    
    # day 6: investigation
    timeline.append({
        "day": 6,
        "date": (datetime.now() - timedelta(days=days-6)).strftime("%Y-%m-%d"),
        "status": "RED",
        "icon": "🔴",
        "events": [
            "INCIDENT declared",
            "Root cause identified: prompt update",
            "Rollback initiated"
        ],
        "hallucination_rate": invariant_report.hallucination_rate,
        "canary_f1": canary_report.f1 if canary_report else 0.45
    })
    
    # day 7: recovery
    timeline.append({
        "day": 7,
        "date": (datetime.now() - timedelta(days=days-7)).strftime("%Y-%m-%d"),
        "status": "GREEN",
        "icon": "✅",
        "events": [
            "Rollback complete",
            "Metrics returning to baseline",
            "Post-mortem scheduled"
        ],
        "hallucination_rate": 0.03,
        "canary_f1": 0.72
    })
    
    return timeline


def compute_confidence_intervals(
    rate: float,
    sample_size: int,
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """
    Compute confidence interval for a rate using Wilson score interval.
    Returns (lower, upper, margin_of_error)
    """
    if sample_size == 0:
        return (0.0, 0.0, 0.0)
    
    # z-score for confidence level
    z = 1.96 if confidence == 0.95 else 2.576  # 95% or 99%
    
    # Wilson score interval
    denominator = 1 + z**2 / sample_size
    center = (rate + z**2 / (2 * sample_size)) / denominator
    margin = z * math.sqrt((rate * (1 - rate) + z**2 / (4 * sample_size)) / sample_size) / denominator
    
    lower = max(0, center - margin)
    upper = min(1, center + margin)
    
    return (round(lower, 4), round(upper, 4), round(margin, 4))


def generate_confidence_report(invariant_report: InvariantReport) -> Dict:
    """
    Generate statistical confidence intervals for all rates.
    """
    n = invariant_report.total_items
    
    hall_ci = compute_confidence_intervals(invariant_report.hallucination_rate, n)
    contra_ci = compute_confidence_intervals(invariant_report.contradiction_rate, n)
    evidence_ci = compute_confidence_intervals(invariant_report.evidence_validity_rate, n)
    schema_ci = compute_confidence_intervals(invariant_report.schema_validity_rate, n)
    
    return {
        "sample_size": n,
        "confidence_level": "95%",
        "metrics": {
            "hallucination_rate": {
                "point_estimate": invariant_report.hallucination_rate,
                "lower_bound": hall_ci[0],
                "upper_bound": hall_ci[1],
                "margin_of_error": hall_ci[2],
                "display": f"{invariant_report.hallucination_rate:.1%} ± {hall_ci[2]*100:.1f}%"
            },
            "contradiction_rate": {
                "point_estimate": invariant_report.contradiction_rate,
                "lower_bound": contra_ci[0],
                "upper_bound": contra_ci[1],
                "margin_of_error": contra_ci[2],
                "display": f"{invariant_report.contradiction_rate:.1%} ± {contra_ci[2]*100:.1f}%"
            },
            "evidence_validity_rate": {
                "point_estimate": invariant_report.evidence_validity_rate,
                "lower_bound": evidence_ci[0],
                "upper_bound": evidence_ci[1],
                "margin_of_error": evidence_ci[2],
                "display": f"{invariant_report.evidence_validity_rate:.1%} ± {evidence_ci[2]*100:.1f}%"
            },
            "schema_validity_rate": {
                "point_estimate": invariant_report.schema_validity_rate,
                "lower_bound": schema_ci[0],
                "upper_bound": schema_ci[1],
                "margin_of_error": schema_ci[2],
                "display": f"{invariant_report.schema_validity_rate:.1%} ± {schema_ci[2]*100:.1f}%"
            }
        },
        "interpretation": _interpret_confidence(invariant_report, hall_ci)
    }


def _interpret_confidence(report: InvariantReport, hall_ci: Tuple) -> str:
    """Generate human-readable interpretation of confidence intervals."""
    threshold = 0.05  # 5% hallucination threshold
    
    if hall_ci[0] > threshold:
        return f"Statistically significant: hallucination rate {report.hallucination_rate:.1%} exceeds {threshold:.0%} threshold even at lower 95% CI bound ({hall_ci[0]:.1%})"
    elif hall_ci[1] > threshold:
        return f"Uncertain: hallucination rate {report.hallucination_rate:.1%} may or may not exceed threshold. CI range [{hall_ci[0]:.1%}, {hall_ci[1]:.1%}] spans threshold."
    else:
        return f"Below threshold: hallucination rate {report.hallucination_rate:.1%} is safely below {threshold:.0%} threshold with 95% confidence."


def generate_human_review_sheet(
    invariant_report: InvariantReport,
    journals: Dict[str, str]
) -> str:
    """
    Generate a markdown sheet for human reviewers to use.
    Includes context, issue, and action checkboxes.
    """
    lines = []
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    lines.append(f"# Human Review Queue - {date_str}")
    lines.append("")
    lines.append(f"**Total items for review:** {len(invariant_report.violations)}")
    lines.append(f"**Hallucination rate:** {invariant_report.hallucination_rate:.1%}")
    lines.append(f"**Contradiction rate:** {invariant_report.contradiction_rate:.1%}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for i, violation in enumerate(invariant_report.violations[:20], 1):  # limit to 20
        journal_text = journals.get(violation.journal_id, "[journal not found]")
        # truncate journal for readability
        if len(journal_text) > 200:
            journal_text = journal_text[:200] + "..."
        
        lines.append(f"## Item {i}: {violation.journal_id} - {violation.violation_type}")
        lines.append("")
        lines.append(f"**Severity:** {violation.severity.value}")
        lines.append("")
        lines.append("**Journal excerpt:**")
        lines.append(f"> {journal_text}")
        lines.append("")
        lines.append(f"**Issue:** {violation.details}")
        lines.append("")
        lines.append("**Review decision:**")
        lines.append("- [ ] ✅ Approve (false positive - extraction is valid)")
        lines.append("- [ ] ❌ Reject (true positive - extraction is wrong)")
        lines.append("- [ ] ⚠️ Unclear (needs escalation)")
        lines.append("")
        lines.append("**Notes:**")
        lines.append("```")
        lines.append("")
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    lines.append("## Summary")
    lines.append("")
    lines.append("| Approved | Rejected | Unclear |")
    lines.append("|----------|----------|---------|")
    lines.append("|          |          |         |")
    lines.append("")
    lines.append("**Reviewer signature:** _________________")
    lines.append("")
    lines.append(f"**Date reviewed:** _________________")
    
    return "\n".join(lines)
