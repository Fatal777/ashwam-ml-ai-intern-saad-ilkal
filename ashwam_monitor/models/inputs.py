from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from .enums import Domain, Polarity


class ParserItem(BaseModel):
    domain: Domain
    text: str
    evidence_span: str
    polarity: Polarity
    time_bucket: str
    intensity_bucket: Optional[str] = None
    arousal_bucket: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("intensity_bucket")
    @classmethod
    def check_intensity_values(cls, v):
        if v is not None and v not in ["low", "medium", "high", "unknown"]:
            raise ValueError(f"bad intensity bucket: {v}")
        return v

    @field_validator("arousal_bucket")
    @classmethod
    def check_arousal_values(cls, v):
        if v is not None and v not in ["low", "medium", "high"]:
            raise ValueError(f"bad arousal bucket: {v}")
        return v


class ParserOutput(BaseModel):
    journal_id: str
    items: List[ParserItem] = []


class JournalEntry(BaseModel):
    journal_id: str
    created_at: str
    text: str
    lang_hint: str


class GoldItem(BaseModel):
    # canary gold labels - doesnt have text or confidence
    domain: Domain
    evidence_span: str
    polarity: Polarity
    time_bucket: str
    intensity_bucket: Optional[str] = None
    arousal_bucket: Optional[str] = None


class GoldLabel(BaseModel):
    journal_id: str
    items: List[GoldItem] = []
