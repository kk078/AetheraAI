"""
Email Auto-Processor for Aethera

Provides automatic email categorization and action item extraction.
"""
import re
from typing import Any, Dict, List, Optional, Tuple


class AutoProcessor:
    """Auto-categorize emails and extract action items."""

    # Category definitions with keyword patterns
    CATEGORIES = {
        "urgent": {
            "keywords": ["urgent", "asap", "immediately", "critical", "emergency", "time-sensitive"],
            "weight": 10,
        },
        "action_required": {
            "keywords": ["action required", "please review", "approval needed", "sign off", "please approve", "needs your attention"],
            "weight": 8,
        },
        "meeting": {
            "keywords": ["meeting", "call", "schedule", "calendar invite", "zoom", "teams meeting", "google meet", "standup"],
            "weight": 6,
        },
        "notification": {
            "keywords": ["notification", "alert", "update", "newsletter", "digest", "weekly report", "automated"],
            "weight": 2,
        },
        "social": {
            "keywords": ["linkedin", "twitter", "facebook", "instagram", "connection request", "followed you", "endorsement"],
            "weight": 1,
        },
        "finance": {
            "keywords": ["invoice", "payment", "billing", "receipt", "refund", "charge", "subscription", "transaction"],
            "weight": 5,
        },
        "security": {
            "keywords": ["security", "login attempt", "password", "2fa", "verification", "suspicious", "unauthorized"],
            "weight": 9,
        },
        "travel": {
            "keywords": ["flight", "hotel", "reservation", "booking", "itinerary", "check-in", "boarding pass"],
            "weight": 4,
        },
    }

    # Action item patterns
    ACTION_PATTERNS = [
        r"(?i)please\s+(review|approve|sign|check|confirm|respond|reply|complete|finish|send)",
        r"(?i)need\s+(you|your)\s+(to|approval|review|input|feedback|signature)",
        r"(?i)(must|have\s+to|need\s+to)\s+(be\s+)?(completed|done|finished|submitted)\s+by",
        r"(?i)deadline[:\s]+\s*.+",
        r"(?i)due\s+(by|date|on|before)\s+.+",
        r"(?i)action\s+item[:\s]+\s*.+",
        r"(?i)todo[:\s]+\s*.+",
        r"(?i)reminder[:\s]+\s*.+",
        r"(?i)(can you|could you|would you)\s+.+",
    ]

    # Deadline patterns
    DEADLINE_PATTERNS = [
        r"(?i)by\s+(?:end\s+of\s+)?(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|eod|eow|cob)",
        r"(?i)by\s+\w+\s+\d{1,2}(?:st|nd|rd|th)?",
        r"(?i)before\s+\w+\s+\d{1,2}",
        r"(?i)deadline[:\s]+.+",
        r"(?i)due\s+(?:by|on|date)\s*.+",
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"\d{4}-\d{2}-\d{2}",
    ]

    def __init__(self, custom_categories: Optional[Dict[str, Dict]] = None):
        """
        Args:
            custom_categories: Optional additional category definitions.
                               Format: {"category_name": {"keywords": [...], "weight": N}}
        """
        self.categories = dict(self.CATEGORIES)
        if custom_categories:
            self.categories.update(custom_categories)

    # -- Categorization -----------------------------------------------------

    def categorize(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Categorize an email based on its content.

        Args:
            email_data: Dict with keys: subject, body_text, from_email (at minimum).

        Returns:
            Dict with keys: categories (list of category names with scores),
                            primary_category (str), confidence (float).
        """
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body_text", "").lower()
        from_email = email_data.get("from_email", "").lower()
        combined_text = f"{subject} {body}"

        scores: Dict[str, float] = {}

        for category, config in self.categories.items():
            score = 0.0
            for keyword in config["keywords"]:
                count = combined_text.count(keyword.lower())
                if count > 0:
                    score += count * config["weight"]
            if score > 0:
                scores[category] = score

        # Sort by score
        sorted_categories = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Normalize confidence
        total_score = sum(scores.values()) if scores else 0
        if total_score > 0:
            primary_category = sorted_categories[0][0]
            confidence = sorted_categories[0][1] / total_score
        else:
            primary_category = "general"
            confidence = 0.0

        return {
            "categories": [cat for cat, _ in sorted_categories],
            "scores": {cat: round(score, 2) for cat, score in sorted_categories},
            "primary_category": primary_category,
            "confidence": round(confidence, 2),
        }

    def categorize_batch(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Categorize a batch of emails.

        Returns:
            List of categorization results in the same order.
        """
        return [self.categorize(email) for email in emails]

    # -- Action Item Extraction ----------------------------------------------

    def extract_action_items(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract action items from an email.

        Args:
            email_data: Dict with keys: subject, body_text, from_email, date.

        Returns:
            Dict with keys: action_items, deadlines, summary.
        """
        subject = email_data.get("subject", "")
        body = email_data.get("body_text", "")
        from_email = email_data.get("from_email", "")
        date = email_data.get("date", "")
        combined = f"{subject} {body}"

        # Find action items
        action_items: List[Dict[str, Any]] = []
        for pattern in self.ACTION_PATTERNS:
            matches = re.finditer(pattern, combined, re.IGNORECASE)
            for match in matches:
                # Get surrounding context (the sentence containing the match)
                start = max(0, match.start() - 50)
                end = min(len(combined), match.end() + 100)
                context = combined[start:end].strip()

                # Try to get the full sentence
                sentence_start = combined.rfind(".", start, match.start())
                sentence_end = combined.find(".", match.end())
                if sentence_start >= 0 and sentence_end >= 0:
                    context = combined[sentence_start + 1:sentence_end].strip()

                action_items.append({
                    "text": context,
                    "pattern": pattern,
                    "source": "subject" if match.start() < len(subject) else "body",
                })

        # Find deadlines
        deadlines: List[Dict[str, str]] = []
        for pattern in self.DEADLINE_PATTERNS:
            matches = re.finditer(pattern, combined, re.IGNORECASE)
            for match in matches:
                deadlines.append({
                    "text": match.group(0),
                    "pattern": pattern,
                })

        # Generate summary
        summary_parts = []
        if action_items:
            summary_parts.append(f"{len(action_items)} action item(s) found")
        if deadlines:
            summary_parts.append(f"{len(deadlines)} deadline(s) detected")
        if not summary_parts:
            summary_parts.append("No action items or deadlines detected")

        summary = f"From: {from_email} | Subject: {subject} | " + " | ".join(summary_parts)

        return {
            "action_items": action_items,
            "deadlines": deadlines,
            "summary": summary,
            "has_urgent_items": any(
                re.search(r"(?i)(urgent|asap|immediately|critical)", item.get("text", ""))
                for item in action_items
            ),
        }

    def extract_batch(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract action items from a batch of emails.

        Returns:
            List of extraction results in the same order.
        """
        return [self.extract_action_items(email) for email in emails]

    # -- Email Prioritization -----------------------------------------------

    def prioritize(self, emails: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize emails based on categorization and action items.

        Returns:
            List of email dicts with added "priority" field, sorted by priority (highest first).
        """
        prioritized = []
        for email_data in emails:
            cat_result = self.categorize(email_data)
            action_result = self.extract_action_items(email_data)

            priority_score = 0

            # Category-based priority
            primary = cat_result["primary_category"]
            if primary == "urgent":
                priority_score += 100
            elif primary == "security":
                priority_score += 90
            elif primary == "action_required":
                priority_score += 80
            elif primary == "finance":
                priority_score += 60
            elif primary == "meeting":
                priority_score += 50
            elif primary == "travel":
                priority_score += 40
            elif primary == "notification":
                priority_score += 10
            elif primary == "social":
                priority_score += 5

            # Action items boost
            priority_score += len(action_result["action_items"]) * 15
            priority_score += len(action_result["deadlines"]) * 20
            if action_result.get("has_urgent_items"):
                priority_score += 30

            email_with_priority = {
                **email_data,
                "priority_score": priority_score,
                "priority": "high" if priority_score >= 80 else "medium" if priority_score >= 40 else "low",
                "category": cat_result["primary_category"],
                "action_items_count": len(action_result["action_items"]),
                "deadlines_count": len(action_result["deadlines"]),
            }
            prioritized.append(email_with_priority)

        # Sort by priority score descending
        prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
        return prioritized

    # -- Sender Analysis ----------------------------------------------------

    def analyze_sender(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the sender to help determine email importance.

        Returns:
            Dict with sender analysis including domain type.
        """
        from_email = email_data.get("from_email", "")
        domain = from_email.split("@")[-1].lower() if "@" in from_email else ""

        # Classify domain
        domain_type = "unknown"
        if domain:
            corporate_tlds = (".com", ".org", ".net", ".io", ".co")
            if domain.endswith(corporate_tlds):
                domain_type = "corporate"
            noreply_patterns = ("noreply@", "no-reply@", "notification@", "alerts@", "automated@")
            if any(p in from_email.lower() for p in noreply_patterns):
                domain_type = "automated"

        is_noreply = any(
            p in from_email.lower()
            for p in ["noreply", "no-reply", "notification", "automated"]
        )

        return {
            "email": from_email,
            "domain": domain,
            "domain_type": domain_type,
            "is_noreply": is_noreply,
            "likely_requires_response": not is_noreply,
        }