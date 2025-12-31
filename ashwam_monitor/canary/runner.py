from typing import List, Dict
from datetime import datetime
from pathlib import Path
import uuid

from ..models.inputs import ParserOutput, GoldLabel
from ..models.outputs import CanaryReport, CanaryJournalResult
from ..config import config
from ..io.loader import load_parser_outputs, load_gold_labels

from .matcher import match_items
from .evaluator import compute_precision_recall_f1, compute_evidence_match_rate
from .actions import determine_action


def run_canary_evaluation(
    parser_outputs: List[ParserOutput],
    gold_labels: List[GoldLabel]
) -> CanaryReport:
    """
    evaluate parser outputs against gold labels
    """
    run_id = f"canary-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    # build lookup by journal_id
    parser_by_id = {o.journal_id: o for o in parser_outputs}
    gold_by_id = {g.journal_id: g for g in gold_labels}

    total_matched = 0
    total_missed = 0
    total_extra = 0
    per_journal = []

    for journal_id in gold_by_id:
        gold = gold_by_id[journal_id]
        parser = parser_by_id.get(journal_id)

        if parser is None:
            # parser didnt output anything for this journal
            missed = len(gold.items)
            per_journal.append(CanaryJournalResult(
                journal_id=journal_id,
                gold_count=len(gold.items),
                parser_count=0,
                matched=0,
                missed=missed,
                extra=0
            ))
            total_missed += missed
            continue

        matched, missed, extra = match_items(parser.items, gold.items)
        total_matched += matched
        total_missed += missed
        total_extra += extra

        per_journal.append(CanaryJournalResult(
            journal_id=journal_id,
            gold_count=len(gold.items),
            parser_count=len(parser.items),
            matched=matched,
            missed=missed,
            extra=extra
        ))

    # compute overall metrics
    precision, recall, f1 = compute_precision_recall_f1(total_matched, total_missed, total_extra)

    # evidence match rate across all items
    all_parser_items = [item for o in parser_outputs for item in o.items if o.journal_id in gold_by_id]
    all_gold_items = [item for g in gold_labels for item in g.items]
    evidence_rate = compute_evidence_match_rate(all_parser_items, all_gold_items)

    # determine action
    action, reason = determine_action(f1, evidence_rate)

    thresholds = config.canary

    return CanaryReport(
        timestamp=datetime.now(),
        run_id=run_id,
        precision=round(precision, 3),
        recall=round(recall, 3),
        f1=round(f1, 3),
        evidence_match_rate=round(evidence_rate, 3),
        matched_count=total_matched,
        missed_count=total_missed,
        extra_count=total_extra,
        action=action,
        action_reason=reason,
        per_journal=per_journal,
        thresholds_used={
            "f1_pass": thresholds.f1_pass,
            "f1_alert": thresholds.f1_alert,
            "f1_human_review": thresholds.f1_human_review,
            "f1_rollback": thresholds.f1_rollback,
            "min_evidence_match": thresholds.min_evidence_match
        },
        threshold_rationale=thresholds.threshold_rationale,
        run_frequency=thresholds.run_frequency
    )


def run_canary_from_paths(
    parser_outputs_path: Path,
    canary_gold_path: Path
) -> CanaryReport:
    """
    convenience function to run canary from file paths
    """
    outputs, _ = load_parser_outputs(parser_outputs_path)
    gold, _ = load_gold_labels(canary_gold_path)
    return run_canary_evaluation(outputs, gold)
