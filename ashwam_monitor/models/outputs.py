from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from .enums import AlertLevel, CanaryAction, DriftStatus


class InvariantViolation(BaseModel):
    journal_id: str
    item_index: int
    invariant_name: str
    violation_type: str
    details: str
    severity: AlertLevel


class InvariantReport(BaseModel):
    timestamp: datetime
    run_id: str
    total_items: int
    total_journals: int
    schema_validity_rate: float
    evidence_validity_rate: float
    hallucination_rate: float
    contradiction_rate: float
    violations: List[InvariantViolation]
    alerts: List[str]
    thresholds_used: Dict[str, float]


class DriftMetric(BaseModel):
    name: str
    baseline_value: float
    current_value: float
    change_pct: float
    js_divergence: Optional[float] = None  # jensen shannon
    ks_statistic: Optional[float] = None
    ks_pvalue: Optional[float] = None
    status: DriftStatus


class DriftReport(BaseModel):
    timestamp: datetime
    run_id: str
    baseline_source: str
    current_source: str
    metrics: List[DriftMetric]
    alerts: List[str]
    thresholds_used: Dict[str, float]


class CanaryJournalResult(BaseModel):
    journal_id: str
    gold_count: int
    parser_count: int
    matched: int
    missed: int
    extra: int


class CanaryReport(BaseModel):
    timestamp: datetime
    run_id: str
    precision: float
    recall: float
    f1: float
    evidence_match_rate: float
    matched_count: int
    missed_count: int
    extra_count: int
    action: CanaryAction
    action_reason: str
    per_journal: List[CanaryJournalResult]
    thresholds_used: Dict[str, float]


class SummaryReport(BaseModel):
    timestamp: datetime
    run_id: str
    overall_status: str
    invariant_summary: Dict[str, float]
    drift_summary: Dict[str, str]
    canary_summary: Dict[str, float]
    critical_alerts: List[str]
    recommended_action: str
