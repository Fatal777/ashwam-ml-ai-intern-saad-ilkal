from dataclasses import dataclass


@dataclass
class InvariantThresholds:
    """thresholds for invariant checks - conservative for health apps"""
    min_schema_validity: float = 0.95
    min_evidence_validity: float = 0.90
    max_hallucination_rate: float = 0.05
    max_contradiction_rate: float = 0.01


@dataclass
class DriftThresholds:
    """when to flag drift vs breakage"""
    js_drift: float = 0.10  # jensen shannon above this is drift
    js_breakage: float = 0.20  # above this is breakage
    ks_alpha: float = 0.05  # significance level for ks test
    domain_shift_pct: float = 15.0  # absolute percent shift
    arousal_shift_pct: float = 20.0
    volume_change_pct: float = 25.0


@dataclass
class CanaryThresholds:
    """f1 levels for different actions"""
    f1_pass: float = 0.70
    f1_alert: float = 0.60
    f1_human_review: float = 0.50
    f1_rollback: float = 0.40
    min_evidence_match: float = 0.80


@dataclass
class HumanReviewConfig:
    max_daily_reviews: int = 30
    escalation_timeout_hours: int = 24
    critical_weight: int = 100
    warning_weight: int = 50
    info_weight: int = 10


@dataclass
class Config:
    invariants: InvariantThresholds = None
    drift: DriftThresholds = None
    canary: CanaryThresholds = None
    human_review: HumanReviewConfig = None

    def __post_init__(self):
        # defaults
        if self.invariants is None:
            self.invariants = InvariantThresholds()
        if self.drift is None:
            self.drift = DriftThresholds()
        if self.canary is None:
            self.canary = CanaryThresholds()
        if self.human_review is None:
            self.human_review = HumanReviewConfig()


# global config instance
config = Config()
