from ..models.inputs import ParserItem
from .templates import CLINICIAN_TEMPLATE


def generate_clinician_view(
    item: ParserItem,
    journal_text: str,
    conflict: str = None
) -> str:
    """
    generate clinician focused review
    shows evidence grounding and limitations
    """
    # find context around evidence span
    evidence = item.evidence_span
    lower_text = journal_text.lower()
    lower_evidence = evidence.lower()

    start = lower_text.find(lower_evidence)
    if start >= 0:
        # show some context before and after
        ctx_start = max(0, start - 20)
        ctx_end = min(len(journal_text), start + len(evidence) + 20)
        context = journal_text[ctx_start:ctx_end]
        if ctx_start > 0:
            context = "..." + context
        if ctx_end < len(journal_text):
            context = context + "..."
    else:
        context = f"[span not found in source: '{evidence}']"

    # domain specific limitations
    limitations = []
    if item.domain.value == "emotion":
        limitations.append("emotion detection may miss sarcasm or complex expressions")
    if item.domain.value == "symptom":
        limitations.append("negation detection accuracy ~90%")
    if item.domain.value == "mind":
        limitations.append("mind domain requires inference may be less reliable")
    if item.confidence < 0.7:
        limitations.append(f"low confidence ({item.confidence:.0%}) - review carefully")

    return CLINICIAN_TEMPLATE.render(
        journal_id="[anonymized]",
        evidence_span=item.evidence_span,
        domain=item.domain.value,
        polarity=item.polarity.value,
        confidence=int(item.confidence * 100),
        context=context,
        conflict=conflict,
        limitations=limitations
    )
