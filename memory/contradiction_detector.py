"""
Aethera AI - Contradiction Detector Module

Detects conflicting stored facts by comparing new facts against existing ones.
Uses negation detection, contradictory value detection, and temporal conflict
analysis to identify inconsistencies in the knowledge base.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


# Negation words that flip the meaning of a statement
NEGATION_WORDS = frozenset({
    "not", "never", "no", "none", "nobody", "nothing", "nowhere",
    "neither", "nor", "cannot", "can't", "doesn't", "doesn't exist",
    "does not", "is not", "isn't", "was not", "wasn't", "will not",
    "won't", "should not", "shouldn't", "would not", "wouldn't",
    "has not", "hasn't", "have not", "haven't", "had not", "hadn't",
    "denies", "denied", "without", "lacks", "absent", "negative for",
    "ruled out", "ruled-out"
})

# Pairs of contradictory terms
CONTRADICTORY_PAIRS: List[Tuple[str, str]] = [
    ("active", "resolved"),
    ("active", "inactive"),
    ("active", "remission"),
    ("present", "absent"),
    ("positive", "negative"),
    ("increased", "decreased"),
    ("elevated", "depressed"),
    ("elevated", "low"),
    ("high", "low"),
    ("above normal", "below normal"),
    ("malignant", "benign"),
    ("covered", "excluded"),
    ("covered", "not covered"),
    ("approved", "denied"),
    ("approved", "rejected"),
    ("in-network", "out-of-network"),
    ("reimbursable", "non-reimbursable"),
    ("required", "not required"),
    ("indicated", "contraindicated"),
    ("normal", "abnormal"),
    ("stable", "unstable"),
    ("improved", "worsened"),
    ("yes", "no"),
    ("true", "false"),
    ("on", "off"),
    ("enabled", "disabled"),
]

# Temporal relation indicators
TEMPORAL_INDICATORS = frozenset({
    "before", "after", "during", "since", "until", "at", "on",
    "starting", "ending", "from", "to", "between"
})


class Contradiction:
    """Represents a detected contradiction between facts."""

    def __init__(
        self,
        new_fact: str,
        existing_fact: str,
        existing_fact_id: str,
        conflict_type: str,
        reason: str,
        severity: str = "medium",
        resolution_suggestion: str = ""
    ):
        self.new_fact = new_fact
        self.existing_fact = existing_fact
        self.existing_fact_id = existing_fact_id
        self.conflict_type = conflict_type  # negation, value, temporal
        self.reason = reason
        self.severity = severity  # low, medium, high
        self.resolution_suggestion = resolution_suggestion
        self.detected_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize contradiction to dictionary."""
        return {
            "new_fact": self.new_fact,
            "existing_fact": self.existing_fact,
            "existing_fact_id": self.existing_fact_id,
            "conflict_type": self.conflict_type,
            "reason": self.reason,
            "severity": self.severity,
            "resolution_suggestion": self.resolution_suggestion,
            "detected_at": self.detected_at
        }


class ContradictionDetector:
    """
    Detects contradictions between a new fact and a set of existing facts.

    Detection strategies:
    1. Negation detection: One statement negates the other
    2. Contradictory values: Mutually exclusive attribute values
    3. Temporal conflicts: Date-based contradictions
    """

    def __init__(self):
        self._contradictory_map = self._build_contradictory_map()

    def _build_contradictory_map(self) -> Dict[str, str]:
        """Build a bidirectional map of contradictory term pairs."""
        mapping: Dict[str, str] = {}
        for term_a, term_b in CONTRADICTORY_PAIRS:
            mapping[term_a.lower()] = term_b.lower()
            mapping[term_b.lower()] = term_a.lower()
        return mapping

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words."""
        return re.findall(r"\b[a-z]+(?:['-][a-z]+)*\b", text.lower())

    def _extract_negation_scope(self, text: str) -> Tuple[bool, List[str]]:
        """
        Determine if text contains negation and extract the scope.

        Returns:
            Tuple of (has_negation, content_words_without_negation)
        """
        tokens = self._tokenize(text)
        has_negation = False
        content_words = []

        for token in tokens:
            if token in NEGATION_WORDS:
                has_negation = True
            else:
                content_words.append(token)

        return has_negation, content_words

    def _extract_dates(self, text: str) -> List[str]:
        """Extract date-like strings from text."""
        date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w* \d{1,4}\b",
        ]
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text.lower()))
        return dates

    def _check_negation_conflict(
        self,
        new_text: str,
        existing_text: str
    ) -> Optional[str]:
        """
        Check for negation-based contradiction.

        Returns reason string if conflict found, None otherwise.
        """
        new_negated, new_content = self._extract_negation_scope(new_text)
        existing_negated, existing_content = self._extract_negation_scope(existing_text)

        # If one is negated and the other is not, check content overlap
        if new_negated != existing_negated:
            new_set = set(new_content)
            existing_set = set(existing_content)
            overlap = new_set & existing_set

            # Require meaningful content overlap (not just stop words)
            if len(overlap) >= 2:
                negated_side = "new" if new_negated else "existing"
                overlap_str = ", ".join(sorted(overlap)[:5])
                return (
                    f"Negation conflict ({negated_side} fact is negated): "
                    f"overlapping terms [{overlap_str}] appear with "
                    f"opposite polarity"
                )

        return None

    def _check_value_conflict(
        self,
        new_text: str,
        existing_text: str
    ) -> Optional[str]:
        """
        Check for contradictory value pairs.

        Returns reason string if conflict found, None otherwise.
        """
        new_tokens = set(self._tokenize(new_text))
        existing_tokens = set(self._tokenize(existing_text))

        for new_token in new_tokens:
            contradictory = self._contradictory_map.get(new_token)
            if contradictory and contradictory in existing_tokens:
                return (
                    f"Contradictory values: '{new_token}' in new fact vs "
                    f"'{contradictory}' in existing fact"
                )

        return None

    def _check_temporal_conflict(
        self,
        new_text: str,
        existing_text: str
    ) -> Optional[str]:
        """
        Check for temporal contradictions.

        Detects cases where:
        - Same entity has mutually exclusive dates (e.g., "before X" vs "after X")
        - A condition is claimed resolved before it was claimed active
        """
        new_dates = self._extract_dates(new_text)
        existing_dates = self._extract_dates(existing_text)

        if not new_dates or not existing_dates:
            return None

        new_tokens = set(self._tokenize(new_text))
        existing_tokens = set(self._tokenize(existing_text))

        # Check for "before" vs "after" conflicts on same reference
        if "before" in new_tokens and "after" in existing_tokens:
            # Extract the reference point (word after before/after)
            return self._check_before_after_conflict(new_text, existing_text)

        if "after" in new_tokens and "before" in existing_tokens:
            return self._check_before_after_conflict(new_text, existing_text)

        # Check for resolved before active: if one fact says "resolved on DATE"
        # and another says "active on LATER_DATE" for the same condition
        if "resolved" in new_tokens and "active" in existing_tokens:
            return self._check_resolved_active_conflict(new_text, existing_text, new_dates, existing_dates)

        if "active" in new_tokens and "resolved" in existing_tokens:
            return self._check_resolved_active_conflict(existing_text, new_text, existing_dates, new_dates)

        return None

    def _check_before_after_conflict(
        self,
        text_before: str,
        text_after: str
    ) -> Optional[str]:
        """Check if 'before X' and 'after X' refer to the same event."""
        before_match = re.search(r"before\s+(\w+)", text_before.lower())
        after_match = re.search(r"after\s+(\w+)", text_after.lower())

        if before_match and after_match:
            if before_match.group(1) == after_match.group(1):
                return (
                    f"Temporal conflict: 'before {before_match.group(1)}' vs "
                    f"'after {after_match.group(1)}' - mutually exclusive timing"
                )

        return None

    def _check_resolved_active_conflict(
        self,
        resolved_text: str,
        active_text: str,
        resolved_dates: List[str],
        active_dates: List[str]
    ) -> Optional[str]:
        """Check if a condition is resolved before being active."""
        if resolved_dates and active_dates:
            try:
                resolved_dt = datetime.fromisoformat(resolved_dates[0])
                active_dt = datetime.fromisoformat(active_dates[0])
                if resolved_dt < active_dt:
                    return (
                        f"Temporal conflict: condition resolved on {resolved_dates[0]} "
                        f"but active on {active_dates[0]}"
                    )
            except (ValueError, TypeError):
                pass

        return None

    def check_new_fact(
        self,
        new_fact: str,
        existing_facts: List[Dict[str, Any]]
    ) -> List[Contradiction]:
        """
        Check a new fact against a list of existing facts for contradictions.

        Args:
            new_fact: The fact text to check
            existing_facts: List of dicts with at least 'id' and 'fact_text' keys

        Returns:
            List of Contradiction objects for each conflict found
        """
        contradictions: List[Contradiction] = []

        for existing in existing_facts:
            existing_text = existing.get("fact_text", "")
            existing_id = existing.get("id", "")

            if not existing_text:
                continue

            # Check negation conflict
            negation_reason = self._check_negation_conflict(new_fact, existing_text)
            if negation_reason:
                contradictions.append(Contradiction(
                    new_fact=new_fact,
                    existing_fact=existing_text,
                    existing_fact_id=existing_id,
                    conflict_type="negation",
                    reason=negation_reason,
                    severity="high"
                ))
                continue  # Skip further checks for this pair

            # Check value conflict
            value_reason = self._check_value_conflict(new_fact, existing_text)
            if value_reason:
                contradictions.append(Contradiction(
                    new_fact=new_fact,
                    existing_fact=existing_text,
                    existing_fact_id=existing_id,
                    conflict_type="value",
                    reason=value_reason,
                    severity="medium"
                ))
                continue

            # Check temporal conflict
            temporal_reason = self._check_temporal_conflict(new_fact, existing_text)
            if temporal_reason:
                contradictions.append(Contradiction(
                    new_fact=new_fact,
                    existing_fact=existing_text,
                    existing_fact_id=existing_id,
                    conflict_type="temporal",
                    reason=temporal_reason,
                    severity="low"
                ))

        return contradictions

    def resolve_contradiction(
        self,
        contradiction: Contradiction,
        strategy: str = "newer_wins"
    ) -> Dict[str, Any]:
        """
        Resolve a contradiction using the specified strategy.

        Args:
            contradiction: The Contradiction to resolve
            strategy: Resolution strategy:
                - 'newer_wins': Keep the newer fact
                - 'higher_confidence': Keep the fact with higher confidence
                - 'flag_for_review': Mark for human review without auto-resolving

        Returns:
            Dict with resolution details: strategy, action, winning_fact, losing_fact
        """
        if strategy == "flag_for_review":
            return {
                "strategy": strategy,
                "action": "flagged",
                "winning_fact": None,
                "losing_fact": None,
                "message": "Contradiction flagged for human review"
            }

        if strategy == "newer_wins":
            return {
                "strategy": strategy,
                "action": "keep_new",
                "winning_fact": contradiction.new_fact,
                "losing_fact_id": contradiction.existing_fact_id,
                "losing_fact": contradiction.existing_fact,
                "message": (
                    f"Keeping newer fact; existing fact "
                    f"'{contradiction.existing_fact[:80]}' should be "
                    f"deprecated or removed"
                )
            }

        if strategy == "higher_confidence":
            # Without confidence data, default to keeping existing
            return {
                "strategy": strategy,
                "action": "keep_existing",
                "winning_fact": contradiction.existing_fact,
                "winning_fact_id": contradiction.existing_fact_id,
                "losing_fact": contradiction.new_fact,
                "message": (
                    f"Insufficient confidence data to determine winner; "
                    f"defaulting to existing fact. Provide confidence scores "
                    f"for automatic resolution."
                )
            }

        return {
            "strategy": strategy,
            "action": "unknown",
            "message": f"Unknown resolution strategy: {strategy}"
        }

    def resolve_contradiction_with_confidence(
        self,
        contradiction: Contradiction,
        new_confidence: float,
        existing_confidence: float,
        new_date: Optional[str] = None,
        existing_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve a contradiction with explicit confidence and date information.

        When confidence is equal, falls back to the newer fact.

        Args:
            contradiction: The Contradiction to resolve
            new_confidence: Confidence of the new fact (0-1)
            existing_confidence: Confidence of the existing fact (0-1)
            new_date: ISO date of the new fact
            existing_date: ISO date of the existing fact

        Returns:
            Dict with resolution details
        """
        # Prefer higher confidence
        if new_confidence > existing_confidence:
            return {
                "strategy": "higher_confidence",
                "action": "keep_new",
                "winning_fact": contradiction.new_fact,
                "losing_fact_id": contradiction.existing_fact_id,
                "losing_fact": contradiction.existing_fact,
                "confidence_new": new_confidence,
                "confidence_existing": existing_confidence,
                "message": (
                    f"New fact has higher confidence "
                    f"({new_confidence:.2f} > {existing_confidence:.2f})"
                )
            }

        if existing_confidence > new_confidence:
            return {
                "strategy": "higher_confidence",
                "action": "keep_existing",
                "winning_fact": contradiction.existing_fact,
                "winning_fact_id": contradiction.existing_fact_id,
                "losing_fact": contradiction.new_fact,
                "confidence_new": new_confidence,
                "confidence_existing": existing_confidence,
                "message": (
                    f"Existing fact has higher confidence "
                    f"({existing_confidence:.2f} > {new_confidence:.2f})"
                )
            }

        # Equal confidence: fall back to newer date
        if new_date and existing_date:
            try:
                new_dt = datetime.fromisoformat(new_date)
                existing_dt = datetime.fromisoformat(existing_date)
                if new_dt >= existing_dt:
                    return {
                        "strategy": "newer_wins",
                        "action": "keep_new",
                        "winning_fact": contradiction.new_fact,
                        "losing_fact_id": contradiction.existing_fact_id,
                        "losing_fact": contradiction.existing_fact,
                        "message": (
                            f"Equal confidence; newer fact wins "
                            f"(new: {new_date}, existing: {existing_date})"
                        )
                    }
                else:
                    return {
                        "strategy": "newer_wins",
                        "action": "keep_existing",
                        "winning_fact": contradiction.existing_fact,
                        "winning_fact_id": contradiction.existing_fact_id,
                        "losing_fact": contradiction.new_fact,
                        "message": (
                            f"Equal confidence; newer fact wins "
                            f"(existing: {existing_date}, new: {new_date})"
                        )
                    }
            except (ValueError, TypeError):
                pass

        # Cannot determine: flag for review
        return {
            "strategy": "flag_for_review",
            "action": "flagged",
            "winning_fact": None,
            "losing_fact": None,
            "message": (
                "Cannot automatically resolve: equal confidence and "
                "no valid date comparison available"
            )
        }

    def flag_for_review(self, contradiction: Contradiction) -> Dict[str, Any]:
        """
        Flag a contradiction for manual human review.

        Returns:
            Dict with flag details
        """
        return {
            "action": "flagged_for_review",
            "conflict_type": contradiction.conflict_type,
            "reason": contradiction.reason,
            "severity": contradiction.severity,
            "new_fact": contradiction.new_fact,
            "existing_fact": contradiction.existing_fact,
            "existing_fact_id": contradiction.existing_fact_id,
            "flagged_at": datetime.now().isoformat(),
            "message": (
                f"Contradiction flagged for review: {contradiction.reason}"
            )
        }


# Singleton instance
_contradiction_detector: Optional[ContradictionDetector] = None


def get_contradiction_detector() -> ContradictionDetector:
    """Get or create the contradiction detector instance."""
    global _contradiction_detector
    if _contradiction_detector is None:
        _contradiction_detector = ContradictionDetector()
    return _contradiction_detector