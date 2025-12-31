from typing import List, Dict
from collections import Counter

from ..models.inputs import ParserOutput


def check_evidence_exists(evidence_span: str, journal_text: str) -> bool:
    # check if evidence span appears in journal text, handles partial matches
    evidence = evidence_span.lower().strip()
    text = journal_text.lower()

    if evidence in text:
        return True

    # check if source contains a shorter version of evidence
    words = evidence.split()
    for i in range(len(words), 1, -1):
        partial = " ".join(words[:i])
        if partial in text and len(partial) > 5:
            return True

    return False


def find_hallucinations(outputs: List[ParserOutput], journals: Dict[str, str]) -> tuple:
    # find items where evidence span doesnt exist in source, returns (rate, list, clustered)
    total_items = 0
    hallucinations = []

    for output in outputs:
        journal_text = journals.get(output.journal_id, "")

        for idx, item in enumerate(output.items):
            total_items += 1

            if not check_evidence_exists(item.evidence_span, journal_text):
                hallucinations.append({
                    "journal_id": output.journal_id,
                    "item_index": idx,
                    "evidence_span": item.evidence_span,
                    "domain": item.domain.value
                })

    rate = len(hallucinations) / total_items if total_items > 0 else 0.0
    clustered = Counter(h["evidence_span"] for h in hallucinations)

    return rate, hallucinations, dict(clustered)


def compute_evidence_validity(outputs: List[ParserOutput], journals: Dict[str, str]) -> tuple:
    # returns (validity_rate, list of invalid items), validity is inverse of hallucination
    hall_rate, hallucinations, _ = find_hallucinations(outputs, journals)
    validity_rate = 1.0 - hall_rate
    return validity_rate, hallucinations
