from typing import List
from ..models.inputs import ParserItem
from .templates import USER_TEMPLATE


def generate_user_view(items: List[ParserItem], needs_confirmation: bool = False) -> str:
    """
    generate user facing friendly summary
    non alarming trust preserving language
    """
    if not items:
        return USER_TEMPLATE.render(
            summary="Nothing specific noted from your journal today.",
            items=[],
            needs_confirmation=False
        )

    # group by domain for friendly summary
    symptoms = [i for i in items if i.domain.value == "symptom"]
    emotions = [i for i in items if i.domain.value == "emotion"]
    foods = [i for i in items if i.domain.value == "food"]

    summary_parts = []
    if symptoms:
        summary_parts.append("some health notes")
    if emotions:
        summary_parts.append("how you were feeling")
    if foods:
        summary_parts.append("what you ate")

    if summary_parts:
        summary = f"From your journal, we noticed {', '.join(summary_parts)}."
    else:
        summary = "We captured a few things from your journal."

    # friendly item descriptions based on domain
    item_texts = []
    for item in items[:5]:  # limit to 5
        domain = item.domain.value
        span = item.evidence_span

        if item.polarity.value == "absent":
            item_texts.append(f"No {span.lower()} mentioned ✓")
        elif domain == "symptom":
            item_texts.append(f"You mentioned: {span}")
        elif domain == "emotion":
            item_texts.append(f"Feeling: {span}")
        elif domain == "food":
            item_texts.append(f"Food: {span}")
        elif domain == "mind":
            item_texts.append(f"Mental state: {span}")
        else:
            item_texts.append(span)

    return USER_TEMPLATE.render(
        summary=summary,
        items=item_texts,
        needs_confirmation=needs_confirmation
    )
