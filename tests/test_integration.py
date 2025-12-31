import pytest
from pathlib import Path
from ashwam_monitor.io.loader import load_parser_outputs, load_journals_as_dict, load_gold_labels
from ashwam_monitor.invariants.runner import run_invariant_checks
from ashwam_monitor.metrics.comparator import run_drift_analysis
from ashwam_monitor.canary.runner import run_canary_evaluation


class TestIntegration:
    # tests on actual provided data
    
    @pytest.fixture
    def data_path(self):
        return Path("data")

    def test_load_day0_outputs(self, data_path):
        outputs, errors = load_parser_outputs(data_path / "parser_outputs_day0.jsonl")
        assert len(outputs) == 20
        assert len(errors) == 0

    def test_load_day1_outputs(self, data_path):
        outputs, errors = load_parser_outputs(data_path / "parser_outputs_day1.jsonl")
        assert len(outputs) == 20
        assert len(errors) == 0

    def test_day1_has_hallucinations(self, data_path):
        outputs, _ = load_parser_outputs(data_path / "parser_outputs_day1.jsonl")
        journals = load_journals_as_dict(data_path / "journals.jsonl")
        
        report = run_invariant_checks(outputs, journals)
        
        # day1 should have high hallucination rate
        assert report.hallucination_rate > 0.15
        # should detect intrusive thoughts pattern
        assert any("intrusive thoughts" in a for a in report.alerts)

    def test_day1_has_contradiction(self, data_path):
        outputs, _ = load_parser_outputs(data_path / "parser_outputs_day1.jsonl")
        journals = load_journals_as_dict(data_path / "journals.jsonl")
        
        report = run_invariant_checks(outputs, journals)
        
        # day1 should have at least one contradiction
        assert report.contradiction_rate > 0

    def test_drift_detects_arousal_collapse(self, data_path):
        baseline, _ = load_parser_outputs(data_path / "parser_outputs_day0.jsonl")
        current, _ = load_parser_outputs(data_path / "parser_outputs_day1.jsonl")
        
        report = run_drift_analysis(baseline, current)
        
        # should detect arousal breakage
        arousal_metric = next(m for m in report.metrics if m.name == "arousal_distribution")
        assert arousal_metric.status.value == "BREAKAGE"

    def test_canary_evaluation(self, data_path):
        outputs, _ = load_parser_outputs(data_path / "parser_outputs_day0.jsonl")
        gold, _ = load_gold_labels(data_path / "canary" / "gold.jsonl")
        
        canary_ids = {g.journal_id for g in gold}
        canary_outputs = [o for o in outputs if o.journal_id in canary_ids]
        
        report = run_canary_evaluation(canary_outputs, gold)
        
        # should have precision, recall, f1
        assert report.precision > 0
        assert report.f1 < 0.6  # day0 has low recall
