"""
engine/scorer.py
Combines eligibility output + context into final ranked result list.
Applies UX confidence thresholds to hide low-confidence results.
"""
import logging
from dataclasses import dataclass, field
from typing import List

from app.engine.eligibility import ELIGIBLE, POSSIBLE, INELIGIBLE

log = logging.getLogger(__name__)

# UX thresholds
THRESH_ELIGIBLE = 0.75
THRESH_POSSIBLE = 0.55
THRESH_MAYBE    = 0.35


@dataclass
class RankedScheme:
    scheme_id:       str
    scheme_name:     str
    result:          str
    confidence:      float
    display_label:   str
    action_label:    str
    missing_fields:  list = field(default_factory=list)
    acquirable:      list = field(default_factory=list)
    blocking_reason: str = ""
    top_insight:     str = ""   # single compressed insight for UX

    def to_dict(self):
        return {
            "scheme_id":      self.scheme_id,
            "scheme_name":    self.scheme_name,
            "result":         self.result,
            "confidence":     round(self.confidence, 3),
            "display_label":  self.display_label,
            "action_label":   self.action_label,
            "missing_fields": self.missing_fields,
            "acquirable":     self.acquirable,
            "blocking_reason":self.blocking_reason,
            "top_insight":    self.top_insight,
        }


def _display_label(confidence: float, result: str) -> tuple:
    """Return (display_label, action_label)."""
    if result == INELIGIBLE:
        return "Not Eligible", "See Why"
    if confidence >= THRESH_ELIGIBLE:
        return "Likely Eligible", "Apply Now"
    if confidence >= THRESH_POSSIBLE:
        return "Possibly Eligible", "Check & Apply"
    return "May Qualify", "Explore"


def _top_insight(elig_out, scheme_name: str) -> str:
    """Produce a single compressed actionable sentence for the UX card."""
    if elig_out.result == INELIGIBLE:
        bf = elig_out.blocking_field or "a required condition"
        return f"You don't meet the {bf.replace('_', ' ')} requirement."

    if elig_out.missing_fields:
        top = elig_out.missing_fields[0].replace("_", " ")
        return f"Confirm your {top} to improve your match."

    if elig_out.acquirable:
        top = elig_out.acquirable[0].replace("_", " ")
        return f"You'll need a {top} to apply."

    if elig_out.confidence >= THRESH_ELIGIBLE:
        return "You appear to meet all known requirements."

    return "Partial match — some conditions could not be verified."


class ResultRanker:

    def rank(
        self,
        scheme_results: list,    # list of (scheme, EligibilityOutput)
        include_ineligible: bool = False,
        max_results: int = 20,
    ) -> List[RankedScheme]:
        """
        scheme_results: [(Scheme ORM, EligibilityOutput), ...]
        Returns sorted RankedScheme list.
        """
        ranked = []

        for scheme, elig_out in scheme_results:
            c = elig_out.confidence

            # Apply UX visibility filter - keep schemes with missing_fields (can become eligible after questions)
            if elig_out.result == INELIGIBLE:
                if not include_ineligible:
                    continue
            elif c < THRESH_MAYBE and not elig_out.missing_fields:
                continue   # too uncertain to show

            dl, al = _display_label(c, elig_out.result)
            insight = _top_insight(elig_out, scheme.name)

            ranked.append(RankedScheme(
                scheme_id=scheme.id,
                scheme_name=scheme.name,
                result=elig_out.result,
                confidence=c,
                display_label=dl,
                action_label=al,
                missing_fields=elig_out.missing_fields,
                acquirable=elig_out.acquirable,
                blocking_reason=elig_out.blocking_reason,
                top_insight=insight,
            ))

        # Sort: eligible first, then by confidence desc
        ranked.sort(key=lambda r: (
            0 if r.result == ELIGIBLE else 1 if r.result == POSSIBLE else 2,
            -r.confidence,
        ))

        return ranked[:max_results]
