"""
Aethera AI - AR Follow-up Prioritizer Skill

Turn an accounts-receivable worklist into a prioritized follow-up queue:
bucket by aging, score each account by dollars-at-risk and collectibility, and
flag accounts approaching timely-filing limits.
"""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

# Rough relative collectibility by payer class (1.0 = best). Heuristic, tunable.
PAYER_COLLECTIBILITY = {
    "commercial": 0.95,
    "medicare": 0.93,
    "medicaid": 0.85,
    "managed_medicaid": 0.82,
    "workers_comp": 0.80,
    "self_pay": 0.40,
    "auto": 0.70,
    "other": 0.75,
}

# Default timely-filing windows (days) by payer class.
TIMELY_FILING_DAYS = {
    "commercial": 90,
    "medicare": 365,
    "medicaid": 95,
    "managed_medicaid": 95,
    "workers_comp": 365,
    "self_pay": 0,
    "auto": 180,
    "other": 180,
}

AGING_BUCKETS = [(0, 30), (31, 60), (61, 90), (91, 120), (121, None)]


def _bucket_label(age_days: int) -> str:
    for lo, hi in AGING_BUCKETS:
        if hi is None:
            if age_days >= lo:
                return f"{lo}+"
        elif lo <= age_days <= hi:
            return f"{lo}-{hi}"
    return "0-30"


def _age_days(account: Dict[str, Any]) -> int:
    if account.get("age_days") is not None:
        try:
            return max(0, int(account["age_days"]))
        except (ValueError, TypeError):
            return 0
    dos = account.get("date_of_service") or account.get("dos")
    if dos:
        try:
            d = datetime.fromisoformat(str(dos)[:10]).date()
            return max(0, (date.today() - d).days)
        except (ValueError, TypeError):
            return 0
    return 0


@skill(name="ar_prioritizer", category="healthcare")
class ARPrioritizerSkill(AetheraSkill):

    @property
    def name(self) -> str:
        return "ar_prioritizer"

    @property
    def description(self) -> str:
        return (
            "Prioritize an accounts-receivable worklist for follow-up. Buckets "
            "accounts by aging, scores them by dollars-at-risk and payer "
            "collectibility, and flags accounts nearing timely-filing limits."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["prioritize", "aging_summary"],
                    "description": "prioritize = ranked worklist; aging_summary = bucket totals only",
                },
                "accounts": {
                    "type": "array",
                    "description": "AR accounts",
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string"},
                            "balance": {"type": "number"},
                            "age_days": {"type": "integer"},
                            "date_of_service": {"type": "string"},
                            "payer_class": {"type": "string"},
                        },
                    },
                },
                "limit": {"type": "integer", "description": "Max accounts in the ranked worklist"},
            },
            "required": ["accounts"],
        }

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "prioritize")
        accounts = kwargs.get("accounts") or []
        if not isinstance(accounts, list):
            return SkillResult(success=False, error="'accounts' must be a list")

        try:
            enriched = []
            buckets: Dict[str, Dict[str, Any]] = {}
            total_ar = 0.0
            for acct in accounts:
                balance = float(acct.get("balance", 0) or 0)
                age = _age_days(acct)
                payer = str(acct.get("payer_class", "other")).lower()
                collect = PAYER_COLLECTIBILITY.get(payer, PAYER_COLLECTIBILITY["other"])
                # Older balances are worth more attention; score blends $ and age.
                age_weight = 1.0 + min(age, 180) / 90.0
                score = round(balance * age_weight * collect, 2)

                tf_days = TIMELY_FILING_DAYS.get(payer, TIMELY_FILING_DAYS["other"])
                tf_at_risk = bool(tf_days and age >= tf_days - 15 and age < tf_days)
                tf_expired = bool(tf_days and age >= tf_days)

                label = _bucket_label(age)
                b = buckets.setdefault(label, {"bucket": label, "count": 0, "balance": 0.0})
                b["count"] += 1
                b["balance"] = round(b["balance"] + balance, 2)
                total_ar += balance

                enriched.append({
                    "account_id": acct.get("account_id"),
                    "balance": round(balance, 2),
                    "age_days": age,
                    "aging_bucket": label,
                    "payer_class": payer,
                    "priority_score": score,
                    "timely_filing_at_risk": tf_at_risk,
                    "timely_filing_expired": tf_expired,
                })

            ordered_buckets = [
                buckets[lbl] for lbl in ["0-30", "31-60", "61-90", "91-120", "121+"]
                if lbl in buckets
            ]
            summary = {
                "total_accounts": len(accounts),
                "total_ar": round(total_ar, 2),
                "buckets": ordered_buckets,
                "at_risk_timely_filing": sum(1 for e in enriched if e["timely_filing_at_risk"]),
                "expired_timely_filing": sum(1 for e in enriched if e["timely_filing_expired"]),
            }

            if action == "aging_summary":
                return SkillResult(success=True, data=summary)

            enriched.sort(key=lambda e: e["priority_score"], reverse=True)
            limit = kwargs.get("limit")
            worklist = enriched[: int(limit)] if limit else enriched
            return SkillResult(success=True, data={"summary": summary, "worklist": worklist})
        except Exception as e:
            return SkillResult(success=False, error=str(e))
