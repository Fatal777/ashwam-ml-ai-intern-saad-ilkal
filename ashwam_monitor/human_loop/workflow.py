"""
human review workflow design

this module documents the human-in-the-loop strategy
per PRD task 4 requirements
"""

from dataclasses import dataclass
from typing import List
from datetime import datetime
import uuid

from ..models.outputs import InvariantReport
from ..models.enums import AlertLevel
from .queue import ReviewQueue, ReviewItem


# what gets reviewed and what doesnt

REVIEW_TRIGGERS = """
WHAT HUMANS REVIEW:
- hallucinations: evidence span not in source (clinician reviews)
- contradictions: conflicting polarity for same span (clinician reviews)
- low confidence items: confidence < 0.5 (analyst samples daily)
- drift alerts: domain or arousal shift (PM + clinician on alert)
- canary failures: f1 below threshold (engineering immediate)

WHAT HUMANS DO NOT REVIEW:
- schema valid items with confidence >= 0.7
- evidence grounded items in stable domains
- successful canary runs
- routine batches with no alerts
"""

REVIEW_CADENCE = """
REVIEW FREQUENCY:
- critical (hallucination/contradiction): real-time notification, 15 min response sla
- daily digest: once daily, 30 min analyst review
- weekly summary: weekly, 1 hour PM review
- monthly audit: monthly, 2 hour deep dive
"""

SCALING_STRATEGY = """
SCALING WITH LIMITED TIME:
- max 30 reviews per day per reviewer
- critical items always included regardless of limit
- priority scoring: severity x age x (1 - confidence)
- overflow handling:
  - auto-approve low-risk after 48 hours with warning flag
  - escalate aged critical items to secondary reviewer
  - log skipped items for weekly aggregate review
"""

PRIVACY_CONSIDERATIONS = """
SENSITIVE DATA HANDLING:
- reviewers see extraction + evidence span only, not full journal
- user ids anonymized in review queue
- reviews logged for audit trail not linked to user identity
- minimum necessary context principle
"""


def build_review_queue_from_invariants(report: InvariantReport) -> ReviewQueue:
    """
    convert invariant violations to review items
    """
    queue = ReviewQueue()

    for violation in report.violations:
        item = ReviewItem(
            id=f"rev-{uuid.uuid4().hex[:8]}",
            journal_id=violation.journal_id,
            violation_type=violation.violation_type,
            severity=violation.severity,
            evidence_span=violation.details.split("'")[1] if "'" in violation.details else "",
            details=violation.details,
            confidence=0.5,  # default since we dont have it in violation
            created_at=datetime.now()
        )
        queue.add(item)

    return queue


def get_review_summary(queue: ReviewQueue) -> dict:
    """
    summary of review queue state for reporting
    """
    pending = queue.get_pending()
    critical = queue.get_critical_items()
    daily = queue.get_daily_batch()

    return {
        "total_pending": len(pending),
        "critical_pending": len(critical),
        "daily_batch_size": len(daily),
        "review_triggers": REVIEW_TRIGGERS.strip(),
        "cadence": REVIEW_CADENCE.strip(),
        "scaling_strategy": SCALING_STRATEGY.strip(),
        "privacy": PRIVACY_CONSIDERATIONS.strip()
    }
