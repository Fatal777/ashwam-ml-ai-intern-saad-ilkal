import json
from pathlib import Path
from datetime import datetime
from typing import Any

from ..models.outputs import InvariantReport, DriftReport, CanaryReport, SummaryReport
from ..models.enums import AlertLevel


def to_json_serializable(obj: Any) -> Any:
    # convert pydantic models and enums to json serializable dicts
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    elif hasattr(obj, "value"):
        return obj.value
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, list):
        return [to_json_serializable(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: to_json_serializable(v) for k, v in obj.items()}
    return obj


def write_json_report(report: Any, path: Path) -> None:
    # write a report to json file
    path.parent.mkdir(parents=True, exist_ok=True)
    
    data = to_json_serializable(report)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def write_invariant_report(report: InvariantReport, out_dir: Path) -> Path:
    path = out_dir / "invariant_report.json"
    write_json_report(report, path)
    return path


def write_drift_report(report: DriftReport, out_dir: Path) -> Path:
    path = out_dir / "drift_report.json"
    write_json_report(report, path)
    return path


def write_canary_report(report: CanaryReport, out_dir: Path) -> Path:
    path = out_dir / "canary_report.json"
    write_json_report(report, path)
    return path


def write_summary_report(
    invariant: InvariantReport,
    drift: DriftReport,
    canary: CanaryReport,
    out_dir: Path
) -> Path:
    # write combined summary report
    critical = sum(1 for a in invariant.alerts if "CRITICAL" in a)
    if critical > 0 or canary.action.value == "ROLLBACK":
        status = "CRITICAL"
    elif invariant.hallucination_rate > 0.05:
        status = "DEGRADED"
    else:
        status = "HEALTHY"

    if canary.action.value == "ROLLBACK":
        action = "rollback to previous model version"
    elif critical > 0:
        action = "block batch and investigate"
    else:
        action = "continue monitoring"

    summary = SummaryReport(
        timestamp=datetime.now(),
        run_id=invariant.run_id,
        overall_status=status,
        invariant_summary={
            "hallucination_rate": invariant.hallucination_rate,
            "contradiction_rate": invariant.contradiction_rate,
            "schema_validity": invariant.schema_validity_rate
        },
        drift_summary={
            m.name: m.status.value for m in drift.metrics
        },
        canary_summary={
            "f1": canary.f1,
            "precision": canary.precision,
            "recall": canary.recall
        },
        critical_alerts=[a for a in invariant.alerts + drift.alerts if "CRITICAL" in a],
        recommended_action=action
    )

    path = out_dir / "summary.json"
    write_json_report(summary, path)
    return path
