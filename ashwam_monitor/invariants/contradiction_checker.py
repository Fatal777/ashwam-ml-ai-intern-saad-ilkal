from typing import List
from collections import defaultdict

from ..models.inputs import ParserOutput


def find_contradictions(outputs: List[ParserOutput]) -> tuple:
    """
    find items where same evidence span has conflicting polarity
    eg no cramps today marked as both present and absent
    returns (contradiction_rate, list of contradictions)
    """
    total_items = 0
    contradictions = []

    for output in outputs:
        # group items by normalized evidence span
        span_map = defaultdict(list)

        for idx, item in enumerate(output.items):
            total_items += 1
            span_key = item.evidence_span.lower().strip()
            span_map[span_key].append({
                "index": idx,
                "item": item
            })

        # check for polarity conflicts
        for span, items in span_map.items():
            if len(items) < 2:
                continue

            polarities = set(i["item"].polarity for i in items)
            if len(polarities) > 1:
                # got a conflict
                contradictions.append({
                    "journal_id": output.journal_id,
                    "evidence_span": span,
                    "conflicting_items": [
                        {
                            "index": i["index"],
                            "polarity": i["item"].polarity.value,
                            "confidence": i["item"].confidence,
                            "domain": i["item"].domain.value
                        }
                        for i in items
                    ]
                })

    rate = len(contradictions) / total_items if total_items > 0 else 0.0
    return rate, contradictions
