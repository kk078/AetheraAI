"""
Aethera AI - Confidence Scoring

Calculates confidence scores for responses based on multiple factors.
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ConfidenceFactors:
    """Factors affecting confidence."""
    source_quality: float  # 0-1, quality of source data
    recency: float  # 0-1, how recent the information is
    consistency: float  # 0-1, consistency across sources
    specificity: float  # 0-1, how specific vs vague
    evidence_count: int  # Number of supporting evidence pieces
    model_confidence: float  # 0-1, raw model confidence


class ConfidenceCalculator:
    """
    Calculates confidence scores for AI responses.

    Factors considered:
    - Source quality (peer-reviewed > general web)
    - Recency (newer information weighted higher)
    - Consistency (agreement across sources)
    - Specificity (detailed vs vague answers)
    - Evidence count (number of supporting sources)
    - Model self-assessment
    """

    # Weights for each factor
    WEIGHTS = {
        "source_quality": 0.25,
        "recency": 0.15,
        "consistency": 0.20,
        "specificity": 0.15,
        "evidence_count": 0.15,
        "model_confidence": 0.10,
    }

    # Confidence thresholds
    THRESHOLDS = {
        "high": 0.8,
        "medium": 0.5,
        "low": 0.0,
    }

    def calculate(
        self,
        factors: ConfidenceFactors
    ) -> Dict[str, Any]:
        """
        Calculate overall confidence score.

        Args:
            factors: Confidence factors

        Returns:
            Confidence score and breakdown
        """
        # Weighted average
        score = (
            factors.source_quality * self.WEIGHTS["source_quality"] +
            factors.recency * self.WEIGHTS["recency"] +
            factors.consistency * self.WEIGHTS["consistency"] +
            factors.specificity * self.WEIGHTS["specificity"] +
            min(factors.evidence_count / 5, 1.0) * self.WEIGHTS["evidence_count"] +
            factors.model_confidence * self.WEIGHTS["model_confidence"]
        )

        # Determine level
        if score >= self.THRESHOLDS["high"]:
            level = "high"
        elif score >= self.THRESHOLDS["medium"]:
            level = "medium"
        else:
            level = "low"

        return {
            "score": round(score, 3),
            "level": level,
            "breakdown": {
                "source_quality": round(factors.source_quality, 3),
                "recency": round(factors.recency, 3),
                "consistency": round(factors.consistency, 3),
                "specificity": round(factors.specificity, 3),
                "evidence_count": factors.evidence_count,
                "model_confidence": round(factors.model_confidence, 3),
            },
            "weights": self.WEIGHTS
        }

    def calculate_from_response(
        self,
        response_text: str,
        sources: List[Dict],
        model_confidence: float
    ) -> Dict[str, Any]:
        """
        Calculate confidence from a generated response.

        Args:
            response_text: The AI response text
            sources: List of sources used
            model_confidence: Raw model confidence

        Returns:
            Confidence score and breakdown
        """
        # Source quality assessment
        source_quality = self._assess_source_quality(sources)

        # Recency assessment
        recency = self._assess_recency(sources)

        # Consistency (if multiple sources)
        consistency = self._assess_consistency(sources)

        # Specificity from response text
        specificity = self._assess_specificity(response_text)

        factors = ConfidenceFactors(
            source_quality=source_quality,
            recency=recency,
            consistency=consistency,
            specificity=specificity,
            evidence_count=len(sources),
            model_confidence=model_confidence
        )

        return self.calculate(factors)

    def _assess_source_quality(self, sources: List[Dict]) -> float:
        """Assess overall source quality."""
        if not sources:
            return 0.5  # Neutral if no sources

        quality_scores = {
            "cms.gov": 1.0,
            "nih.gov": 0.95,
            "pubmed": 0.95,
            "fda.gov": 0.95,
            "cdc.gov": 0.9,
            "who.int": 0.9,
            "journal": 0.85,
            "professional_org": 0.8,
            "news": 0.5,
            "general_web": 0.3,
        }

        total = 0
        for source in sources:
            source_type = source.get("type", "general_web")
            total += quality_scores.get(source_type, 0.5)

        return total / len(sources)

    def _assess_recency(self, sources: List[Dict]) -> float:
        """Assess information recency."""
        from datetime import datetime

        if not sources:
            return 0.5

        now = datetime.now()
        recency_scores = []

        for source in sources:
            date_str = source.get("date")
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str)
                    days_old = (now - date).days
                    # Score: 1.0 for today, 0.5 for 1 year old, 0.0 for 5+ years
                    score = max(0, 1 - (days_old / 1825))
                    recency_scores.append(score)
                except Exception:
                    recency_scores.append(0.5)
            else:
                recency_scores.append(0.5)  # Unknown date

        return sum(recency_scores) / len(recency_scores)

    def _assess_consistency(self, sources: List[Dict]) -> float:
        """Assess consistency across sources."""
        if len(sources) <= 1:
            return 0.8  # Can't assess consistency with 1 source

        # Check if sources agree on key facts
        # Simplified: assume consistency if sources are from similar quality tiers
        quality_tiers = []
        for source in sources:
            quality_tiers.append(source.get("type", "general"))

        # If all same tier, high consistency
        if len(set(quality_tiers)) == 1:
            return 1.0

        # If mixed tiers, moderate consistency
        return 0.7

    def _assess_specificity(self, text: str) -> float:
        """Assess response specificity."""
        if not text:
            return 0.0

        # Indicators of specificity
        specific_indicators = [
            len(text) > 200,  # Detailed response
            any(c.isdigit() for c in text),  # Contains numbers
            "specifically" in text.lower(),
            "according to" in text.lower(),
            "section" in text.lower() or "code" in text.lower(),
            text.count(".") > 3,  # Multiple sentences
        ]

        return sum(specific_indicators) / len(specific_indicators)

    def get_confidence_label(self, score: float) -> str:
        """Get human-readable confidence label."""
        if score >= self.THRESHOLDS["high"]:
            return "High"
        elif score >= self.THRESHOLDS["medium"]:
            return "Medium"
        else:
            return "Low"


# Singleton instance
_calculator: Optional[ConfidenceCalculator] = None


def get_confidence_calculator() -> ConfidenceCalculator:
    """Get the confidence calculator."""
    global _calculator
    if _calculator is None:
        _calculator = ConfidenceCalculator()
    return _calculator
