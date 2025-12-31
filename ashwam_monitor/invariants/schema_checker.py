from typing import List
from ..models.inputs import ParserItem, ParserOutput
from ..models.enums import Domain


def check_item_schema(item: ParserItem) -> List[str]:
    # check if a single item has valid schema, returns list of errors found
    errors = []

    if item.domain == Domain.EMOTION:
        if item.arousal_bucket is None:
            errors.append("emotion item missing arousal_bucket")
    else:
        if item.intensity_bucket is None:
            errors.append(f"{item.domain.value} item missing intensity_bucket")

    if item.confidence < 0 or item.confidence > 1:
        errors.append(f"confidence out of range: {item.confidence}")

    if not item.evidence_span or not item.evidence_span.strip():
        errors.append("empty evidence span")

    return errors


def compute_schema_validity(outputs: List[ParserOutput]) -> tuple:
    # returns (validity_rate, list of violations)
    total_items = 0
    valid_items = 0
    violations = []

    for output in outputs:
        for idx, item in enumerate(output.items):
            total_items += 1
            errors = check_item_schema(item)
            if errors:
                violations.append({
                    "journal_id": output.journal_id,
                    "item_index": idx,
                    "errors": errors
                })
            else:
                valid_items += 1

    rate = valid_items / total_items if total_items > 0 else 1.0
    return rate, violations
