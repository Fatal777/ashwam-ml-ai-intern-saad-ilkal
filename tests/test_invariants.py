import pytest
from ashwam_monitor.invariants.evidence_checker import check_evidence_exists, find_hallucinations
from ashwam_monitor.invariants.contradiction_checker import find_contradictions
from ashwam_monitor.invariants.schema_checker import check_item_schema
from ashwam_monitor.models.inputs import ParserOutput, ParserItem
from ashwam_monitor.models.enums import Domain, Polarity


class TestEvidenceChecker:

    def test_exact_match(self):
        assert check_evidence_exists("mild headache", "Woke up with mild headache today")

    def test_case_insensitive(self):
        assert check_evidence_exists("MILD HEADACHE", "woke up with mild headache")

    def test_partial_match_extension(self):
        # parser extended no cramps to no cramps today
        assert check_evidence_exists("no cramps today", "No cramps. Feeling good")

    def test_no_match(self):
        assert not check_evidence_exists("intrusive thoughts", "Feeling calm and clear")

    def test_find_hallucinations_basic(self):
        outputs = [
            ParserOutput(journal_id="C001", items=[
                ParserItem(
                    domain=Domain.SYMPTOM,
                    text="headache",
                    evidence_span="mild headache",
                    polarity=Polarity.PRESENT,
                    time_bucket="today",
                    confidence=0.8
                ),
                ParserItem(
                    domain=Domain.MIND,
                    text="thoughts",
                    evidence_span="intrusive thoughts",
                    polarity=Polarity.PRESENT,
                    time_bucket="today",
                    confidence=0.6
                )
            ])
        ]
        journals = {"C001": "Woke up with mild headache. Feeling calm."}

        rate, hallucinations, clustered = find_hallucinations(outputs, journals)

        assert rate == 0.5  # 1 out of 2
        assert len(hallucinations) == 1
        assert hallucinations[0]["evidence_span"] == "intrusive thoughts"


class TestContradictionChecker:

    def test_no_contradiction(self):
        outputs = [
            ParserOutput(journal_id="C001", items=[
                ParserItem(
                    domain=Domain.SYMPTOM,
                    text="cramps",
                    evidence_span="no cramps",
                    polarity=Polarity.ABSENT,
                    time_bucket="today",
                    confidence=0.8
                )
            ])
        ]
        rate, contradictions = find_contradictions(outputs)
        assert rate == 0
        assert len(contradictions) == 0

    def test_finds_contradiction(self):
        outputs = [
            ParserOutput(journal_id="C016", items=[
                ParserItem(
                    domain=Domain.SYMPTOM,
                    text="cramps",
                    evidence_span="No cramps today",
                    polarity=Polarity.ABSENT,
                    time_bucket="today",
                    confidence=0.85
                ),
                ParserItem(
                    domain=Domain.SYMPTOM,
                    text="cramps",
                    evidence_span="No cramps today",
                    polarity=Polarity.PRESENT,
                    time_bucket="today",
                    confidence=0.4
                )
            ])
        ]
        rate, contradictions = find_contradictions(outputs)
        assert len(contradictions) == 1
        assert contradictions[0]["journal_id"] == "C016"


class TestSchemaChecker:

    def test_valid_emotion_item(self):
        item = ParserItem(
            domain=Domain.EMOTION,
            text="calm",
            evidence_span="felt calm",
            polarity=Polarity.PRESENT,
            time_bucket="today",
            arousal_bucket="low",
            confidence=0.8
        )
        errors = check_item_schema(item)
        assert len(errors) == 0

    def test_emotion_missing_arousal(self):
        item = ParserItem(
            domain=Domain.EMOTION,
            text="calm",
            evidence_span="felt calm",
            polarity=Polarity.PRESENT,
            time_bucket="today",
            confidence=0.8
        )
        errors = check_item_schema(item)
        assert "arousal_bucket" in errors[0]

    def test_symptom_missing_intensity(self):
        item = ParserItem(
            domain=Domain.SYMPTOM,
            text="headache",
            evidence_span="mild headache",
            polarity=Polarity.PRESENT,
            time_bucket="today",
            confidence=0.8
        )
        errors = check_item_schema(item)
        assert "intensity_bucket" in errors[0]
