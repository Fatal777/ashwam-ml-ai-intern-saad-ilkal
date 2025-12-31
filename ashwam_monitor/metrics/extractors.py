from typing import List
from ..models.inputs import ParserOutput, ParserItem
from ..models.enums import Domain


def compute_uncertainty_rate(items: List[ParserItem]) -> float:
    # proportion of items with unknown/uncertain values (intensity=unknown, emotion missing arousal, confidence<0.5)
    if not items:
        return 0.0

    uncertain_count = 0
    for item in items:
        is_uncertain = False

        if item.intensity_bucket == "unknown":
            is_uncertain = True

        if item.domain == Domain.EMOTION and item.arousal_bucket is None:
            is_uncertain = True

        if item.confidence < 0.5:
            is_uncertain = True

        if is_uncertain:
            uncertain_count += 1

    return uncertain_count / len(items)


def compute_extraction_volume(outputs: List[ParserOutput]) -> dict:
    # stats about number of items per journal
    if not outputs:
        return {"mean": 0, "std": 0, "zero_rate": 0}

    counts = [len(o.items) for o in outputs]
    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    std = variance ** 0.5
    zero_rate = sum(1 for c in counts if c == 0) / len(counts)

    return {
        "mean": mean,
        "std": std,
        "zero_rate": zero_rate,
        "total_items": sum(counts),
        "total_journals": len(outputs)
    }


def compute_domain_distribution(items: List[ParserItem]) -> dict:
    # percentage of each domain in extraction
    if not items:
        return {}

    counts = {}
    for item in items:
        d = item.domain.value
        counts[d] = counts.get(d, 0) + 1

    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


def compute_arousal_distribution(items: List[ParserItem]) -> dict:
    # arousal bucket distribution for emotion domain only
    emotion_items = [i for i in items if i.domain == Domain.EMOTION and i.arousal_bucket]
    if not emotion_items:
        return {}

    counts = {}
    for item in emotion_items:
        b = item.arousal_bucket
        counts[b] = counts.get(b, 0) + 1

    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}


def compute_intensity_distribution(items: List[ParserItem]) -> dict:
    # intensity bucket distribution for non-emotion domains
    relevant = [i for i in items if i.domain != Domain.EMOTION and i.intensity_bucket]
    if not relevant:
        return {}

    counts = {}
    for item in relevant:
        b = item.intensity_bucket
        counts[b] = counts.get(b, 0) + 1

    total = sum(counts.values())
    return {k: v / total for k, v in counts.items()}
