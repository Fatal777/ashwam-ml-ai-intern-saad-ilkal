from enum import Enum


class Domain(str, Enum):
    SYMPTOM = "symptom"
    FOOD = "food"
    EMOTION = "emotion"
    MIND = "mind"


class Polarity(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class CanaryAction(str, Enum):
    PASS = "PASS"
    ALERT = "ALERT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ROLLBACK = "ROLLBACK"


class DriftStatus(str, Enum):
    STABLE = "STABLE"
    DRIFT = "DRIFT"
    BREAKAGE = "BREAKAGE"
