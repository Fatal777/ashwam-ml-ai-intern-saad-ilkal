from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum

from ..models.enums import AlertLevel
from ..config import config


class ReviewState(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


@dataclass
class ReviewItem:
    # single item that needs human review
    id: str
    journal_id: str
    violation_type: str
    severity: AlertLevel
    evidence_span: str
    details: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.now)
    state: ReviewState = ReviewState.PENDING
    assigned_to: Optional[str] = None
    notes: str = ""


class ReviewQueue:
    # priority queue for human review
    # handles limited clinician time by prioritizing critical items


    def __init__(self):
        self.items: List[ReviewItem] = []
        self.cfg = config.human_review

    def add(self, item: ReviewItem) -> None:
        self.items.append(item)

    def get_priority_score(self, item: ReviewItem) -> float:

        # higher score = higher priority
        # based on severity weight x age factor x inverse confidence

        weights = {
            AlertLevel.CRITICAL: self.cfg.critical_weight,
            AlertLevel.WARNING: self.cfg.warning_weight,
            AlertLevel.INFO: self.cfg.info_weight
        }
        severity_weight = weights.get(item.severity, 10)

        # older items get higher priority
        age_hours = (datetime.now() - item.created_at).total_seconds() / 3600
        age_factor = min(2.0, 1.0 + age_hours / 24)

        # lower confidence = higher priority
        conf_factor = 1.0 - item.confidence

        return severity_weight * age_factor * conf_factor

    def get_pending(self) -> List[ReviewItem]:
        return [i for i in self.items if i.state == ReviewState.PENDING]

    def get_daily_batch(self) -> List[ReviewItem]:
        # get prioritized batch for daily review
        # respects max_daily_reviews limit
        pending = self.get_pending()
        sorted_items = sorted(pending, key=self.get_priority_score, reverse=True)
        return sorted_items[:self.cfg.max_daily_reviews]

    def get_critical_items(self) -> List[ReviewItem]:
        # critical items always need review regardless of daily limit
        return [i for i in self.items 
                if i.severity == AlertLevel.CRITICAL 
                and i.state == ReviewState.PENDING]

    def escalate_aged_items(self) -> List[ReviewItem]:
        # items pending too long get escalated
        escalated = []
        for item in self.items:
            if item.state != ReviewState.PENDING:
                continue
            age_hours = (datetime.now() - item.created_at).total_seconds() / 3600
            if age_hours > self.cfg.escalation_timeout_hours:
                item.state = ReviewState.ESCALATED
                escalated.append(item)
        return escalated

    def mark_reviewed(self, item_id: str, approved: bool, notes: str = "") -> bool:
        for item in self.items:
            if item.id == item_id:
                item.state = ReviewState.APPROVED if approved else ReviewState.REJECTED
                item.notes = notes
                return True
        return False
