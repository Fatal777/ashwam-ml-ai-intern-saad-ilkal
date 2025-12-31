import pytest
from ashwam_monitor.metrics.statistical import jensen_shannon_divergence, ks_test
from ashwam_monitor.metrics.extractors import (
    compute_uncertainty_rate,
    compute_domain_distribution,
    compute_extraction_volume
)
from ashwam_monitor.models.inputs import ParserOutput, ParserItem
from ashwam_monitor.models.enums import Domain, Polarity


class TestJensenShannonDivergence:

    def test_identical_distributions(self):
        p = [0.5, 0.3, 0.2]
        q = [0.5, 0.3, 0.2]
        jsd = jensen_shannon_divergence(p, q)
        assert jsd < 0.01  # should be near zero

    def test_completely_different(self):
        p = [1.0, 0.0, 0.0]
        q = [0.0, 0.0, 1.0]
        jsd = jensen_shannon_divergence(p, q)
        assert jsd > 0.5  # should be high

    def test_slight_shift(self):
        p = [0.5, 0.3, 0.2]
        q = [0.4, 0.4, 0.2]
        jsd = jensen_shannon_divergence(p, q)
        assert 0 < jsd < 0.1  # small shift


class TestKSTest:

    def test_same_distribution(self):
        a = [0.6, 0.7, 0.8, 0.65, 0.75]
        b = [0.65, 0.72, 0.78, 0.68, 0.73]
        stat, pval = ks_test(a, b)
        assert pval > 0.05  # not significantly different

    def test_different_distribution(self):
        a = [0.1, 0.2, 0.15, 0.18, 0.12]
        b = [0.8, 0.9, 0.85, 0.88, 0.82]
        stat, pval = ks_test(a, b)
        assert pval < 0.05  # significantly different


class TestExtractors:

    def make_item(self, domain, confidence=0.7, intensity="medium", arousal=None):
        return ParserItem(
            domain=domain,
            text="test",
            evidence_span="test span",
            polarity=Polarity.PRESENT,
            time_bucket="today",
            intensity_bucket=intensity,
            arousal_bucket=arousal,
            confidence=confidence
        )

    def test_uncertainty_rate_low_confidence(self):
        items = [
            self.make_item(Domain.SYMPTOM, confidence=0.3),
            self.make_item(Domain.SYMPTOM, confidence=0.8),
        ]
        rate = compute_uncertainty_rate(items)
        assert rate == 0.5  # 1 low confidence out of 2

    def test_uncertainty_rate_unknown_intensity(self):
        items = [
            self.make_item(Domain.FOOD, intensity="unknown"),
            self.make_item(Domain.FOOD, intensity="medium"),
        ]
        rate = compute_uncertainty_rate(items)
        assert rate == 0.5

    def test_domain_distribution(self):
        items = [
            self.make_item(Domain.SYMPTOM),
            self.make_item(Domain.SYMPTOM),
            self.make_item(Domain.FOOD),
            self.make_item(Domain.EMOTION, arousal="high"),
        ]
        dist = compute_domain_distribution(items)
        assert dist["symptom"] == 0.5
        assert dist["food"] == 0.25
        assert dist["emotion"] == 0.25

    def test_extraction_volume(self):
        outputs = [
            ParserOutput(journal_id="C001", items=[
                self.make_item(Domain.SYMPTOM),
                self.make_item(Domain.FOOD)
            ]),
            ParserOutput(journal_id="C002", items=[]),
            ParserOutput(journal_id="C003", items=[
                self.make_item(Domain.EMOTION, arousal="low")
            ]),
        ]
        vol = compute_extraction_volume(outputs)
        assert vol["mean"] == 1.0  # (2+0+1)/3
        assert vol["zero_rate"] == pytest.approx(0.333, rel=0.01)
