"""
Aethera AI - Automation Engine

Natural language automation builder. Users describe automations in plain English:
- Trigger: "when X" (scheduled or event-based)
- Condition: "if Y" (optional filter)
- Action: "do Z" (what to execute)

Parses natural language descriptions into structured automation rules,
then converts them to scheduled or event-triggered jobs via the scheduler.

Supports: create automation, list automations, delete automation,
         execute automation, natural language parsing.
"""

import json
import logging
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.environ.get("AUTOMATIONS_DB_PATH", "/data/proactive_automations.db")

# ---------------------------------------------------------------------------
# Trigger Types
# ---------------------------------------------------------------------------

TRIGGER_TYPES = [
    "schedule_cron",       # Cron expression (e.g., "every Monday at 9am")
    "schedule_interval",   # Interval (e.g., "every 4 hours")
    "event_alert",         # When a new alert is created
    "event_knowledge",    # When a knowledge update is available
    "event_claim",         # When a claim status changes
    "event_deadline",      # When a deadline is approaching
    "event_usage",         # When a usage threshold is crossed
    "event_manual",       # Manual trigger only
]

# ---------------------------------------------------------------------------
# Action Types
# ---------------------------------------------------------------------------

ACTION_TYPES = [
    "send_notification",       # Send alert/notification
    "generate_briefing",      # Generate a briefing
    "run_report",             # Run a report
    "fetch_knowledge",        # Fetch knowledge updates
    "fetch_news",             # Fetch news feeds
    "check_threshold",        # Check a threshold
    "webhook",                # Call a webhook URL
    "log_message",            # Log a message
    "custom_callable",       # Call a Python callable
]

# ---------------------------------------------------------------------------
# Condition Operators
# ---------------------------------------------------------------------------

CONDITION_OPERATORS = {
    "equals": lambda a, b: str(a) == str(b),
    "not_equals": lambda a, b: str(a) != str(b),
    "contains": lambda a, b: str(b) in str(a),
    "greater_than": lambda a, b: float(a) > float(b),
    "less_than": lambda a, b: float(a) < float(b),
    "greater_equal": lambda a, b: float(a) >= float(b),
    "less_equal": lambda a, b: float(a) <= float(b),
    "is_true": lambda a, _: bool(a),
    "is_false": lambda a, _: not bool(a),
}


class AutomationRule:
    """Represents a parsed automation rule."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        trigger_type: str,
        trigger_config: Dict[str, Any],
        conditions: List[Dict[str, Any]],
        action_type: str,
        action_config: Dict[str, Any],
        enabled: bool = True,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        last_run_at: Optional[str] = None,
        run_count: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
        scheduler_job_id: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.trigger_type = trigger_type
        self.trigger_config = trigger_config
        self.conditions = conditions
        self.action_type = action_type
        self.action_config = action_config
        self.enabled = enabled
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()
        self.updated_at = updated_at or self.created_at
        self.last_run_at = last_run_at
        self.run_count = run_count
        self.metadata = metadata or {}
        self.scheduler_job_id = scheduler_job_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "conditions": self.conditions,
            "action_type": self.action_type,
            "action_config": self.action_config,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_run_at": self.last_run_at,
            "run_count": self.run_count,
            "metadata": self.metadata,
            "scheduler_job_id": self.scheduler_job_id,
        }


class NaturalLanguageParser:
    """
    Parses natural language automation descriptions into structured rules.

    Recognizes patterns:
    - Trigger: "when X", "every X", "at X", "on X"
    - Condition: "if X", "only when X", "where X"
    - Action: "do X", "send X", "notify X", "run X", "check X", "fetch X"
    """

    # Time pattern mappings
    TIME_PATTERNS = [
        (r"every\s+monday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * 1"),
        (r"every\s+tuesday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * 2"),
        (r"every\s+wednesday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * 3"),
        (r"every\s+thursday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * 4"),
        (r"every\s+friday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * 5"),
        (r"every\s+weekday\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * 1-5"),
        (r"every\s+day\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * *"),
        (r"daily\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", "cron", "0 {minute} {hour_converted} * * *"),
        (r"every\s+(\d+)\s+hours?", "interval", "hours"),
        (r"every\s+(\d+)\s+minutes?", "interval", "minutes"),
        (r"every\s+(\d+)\s+days?", "interval", "days"),
        (r"every\s+hour", "interval", "hours_1"),
        (r"every\s+week", "interval", "weeks_1"),
        (r"at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)", "cron", "0 {minute} {hour_converted} * * *"),
    ]

    # Event trigger patterns
    EVENT_PATTERNS = [
        (r"when\s+(?:a\s+)?new\s+alert\s+(?:is\s+)?created", "event_alert"),
        (r"when\s+(?:a\s+)?knowledge\s+update\s+(?:is\s+)?available", "event_knowledge"),
        (r"when\s+(?:a\s+)?claim\s+status\s+changes", "event_claim"),
        (r"when\s+(?:a\s+)?deadline\s+(?:is\s+)?approaching", "event_deadline"),
        (r"when\s+(?:a\s+)?usage\s+(?:limit|threshold)\s+(?:is\s+)?(?:crossed|exceeded|reached)", "event_usage"),
    ]

    # Action patterns
    ACTION_PATTERNS = [
        (r"(?:send|notify)\s+(?:me\s+)?(?:a\s+)?notification", "send_notification"),
        (r"(?:send|notify)\s+(?:me\s+)?(?:an\s+)?alert", "send_notification"),
        (r"generate\s+(?:a\s+)?briefing", "generate_briefing"),
        (r"run\s+(?:a\s+)?report", "run_report"),
        (r"fetch\s+(?:the\s+)?(?:latest\s+)?knowledge\s+updates?", "fetch_knowledge"),
        (r"fetch\s+(?:the\s+)?(?:latest\s+)?news", "fetch_news"),
        (r"check\s+(?:the\s+)?threshold", "check_threshold"),
        (r"call\s+(?:the\s+)?webhook\s+(\S+)", "webhook"),
        (r"log\s+(?:a\s+)?message", "log_message"),
    ]

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse a natural language automation description.

        Returns a dict with:
        - trigger_type: str
        - trigger_config: dict
        - conditions: list of condition dicts
        - action_type: str
        - action_config: dict
        - name: str (auto-generated)
        """
        text_lower = text.lower().strip()
        result = {
            "trigger_type": "event_manual",
            "trigger_config": {},
            "conditions": [],
            "action_type": "log_message",
            "action_config": {},
            "name": "",
        }

        # Parse trigger
        trigger = self._parse_trigger(text_lower)
        if trigger:
            result["trigger_type"] = trigger[0]
            result["trigger_config"] = trigger[1]

        # Parse conditions
        conditions = self._parse_conditions(text_lower)
        result["conditions"] = conditions

        # Parse action
        action = self._parse_action(text_lower)
        if action:
            result["action_type"] = action[0]
            result["action_config"] = action[1]

        # Generate name from the original text
        result["name"] = self._generate_name(text)

        return result

    def _parse_trigger(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse the trigger portion of the description."""
        # Check event patterns first
        for pattern, trigger_type in self.EVENT_PATTERNS:
            if re.search(pattern, text):
                return (trigger_type, {"pattern_matched": pattern})

        # Check time patterns
        for pattern, trigger_kind, template in self.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                if trigger_kind == "cron":
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if match.group(2) else 0
                    ampm = match.group(3) if len(match.groups()) >= 3 and match.group(3) else None

                    if ampm == "pm" and hour < 12:
                        hour += 12
                    elif ampm == "am" and hour == 12:
                        hour = 0

                    cron_expr = template.replace("{minute}", str(minute)).replace("{hour_converted}", str(hour))
                    return ("schedule_cron", {"cron_expr": cron_expr, "hour": hour, "minute": minute})

                elif trigger_kind == "interval":
                    value = int(match.group(1))
                    unit = template  # "hours", "minutes", "days"
                    return ("schedule_interval", {unit: value, "unit": unit, "value": value})

                elif trigger_kind == "hours_1":
                    return ("schedule_interval", {"hours": 1, "unit": "hours", "value": 1})
                elif trigger_kind == "weeks_1":
                    return ("schedule_interval", {"weeks": 1, "unit": "weeks", "value": 1})

        # Check for generic "when" patterns
        when_match = re.search(r"when\s+(.+?)(?:\s+(?:then|do|if|,))", text)
        if when_match:
            event_text = when_match.group(1).strip()
            # Try to match against known event types
            for pattern, trigger_type in self.EVENT_PATTERNS:
                if re.search(pattern, event_text):
                    return (trigger_type, {"description": event_text})
            return ("event_manual", {"description": event_text})

        return None

    def _parse_conditions(self, text: str) -> List[Dict[str, Any]]:
        """Parse condition clauses from the description."""
        conditions = []

        # Pattern: "if X is/greater than/less than Y"
        cond_patterns = [
            (r"if\s+(.+?)\s+(?:is\s+)?greater\s+than\s+(\S+)", "greater_than"),
            (r"if\s+(.+?)\s+(?:is\s+)?less\s+than\s+(\S+)", "less_than"),
            (r"if\s+(.+?)\s+(?:is\s+)?equal\s+to\s+(\S+)", "equals"),
            (r"if\s+(.+?)\s+equals?\s+(\S+)", "equals"),
            (r"if\s+(.+?)\s+contains?\s+(\S+)", "contains"),
            (r"if\s+(.+?)\s+(?:is\s+)?above\s+(\S+)", "greater_than"),
            (r"if\s+(.+?)\s+(?:is\s+)?below\s+(\S+)", "less_than"),
            (r"if\s+(.+?)\s+(?:is\s+)?over\s+(\S+)", "greater_than"),
            (r"if\s+(.+?)\s+(?:is\s+)?under\s+(\S+)", "less_than"),
            (r"only\s+if\s+(.+?)\s+(?:is\s+)?true", "is_true"),
            (r"only\s+if\s+(.+?)\s+(?:is\s+)?false", "is_false"),
        ]

        for pattern, operator in cond_patterns:
            match = re.search(pattern, text)
            if match:
                field = match.group(1).strip()
                value = match.group(2).strip() if len(match.groups()) > 1 else None
                conditions.append({
                    "field": field,
                    "operator": operator,
                    "value": value,
                })

        return conditions

    def _parse_action(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Parse the action portion of the description."""
        for pattern, action_type in self.ACTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                config: Dict[str, Any] = {}
                if action_type == "webhook" and match.groups():
                    config["url"] = match.group(1)
                return (action_type, config)

        # Fallback: look for "do" or "then" keywords
        do_match = re.search(r"(?:do|then)\s+(.+)", text)
        if do_match:
            action_text = do_match.group(1).strip()
            return ("log_message", {"message": action_text})

        return None

    @staticmethod
    def _generate_name(text: str) -> str:
        """Generate a short automation name from the description."""
        # Take the first ~50 chars, clean up
        name = text.strip()[:60]
        # Remove common prefixes
        for prefix in ["when ", "every ", "at "]:
            if name.lower().startswith(prefix):
                name = name[len(prefix):]
                break
        # Capitalize first letter
        if name:
            name = name[0].upper() + name[1:]
        return name


class AutomationEngine:
    """
    Natural language automation builder and executor.

    Parses trigger/condition/action from plain English,
    persists rules in SQLite, and executes them via the scheduler.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        scheduler: Optional[Any] = None,
        alert_manager: Optional[Any] = None,
        action_queue: Optional[Any] = None,
        knowledge_updater: Optional[Any] = None,
        news_aggregator: Optional[Any] = None,
        briefing_generator: Optional[Any] = None,
        report_generator: Optional[Any] = None,
    ):
        self._db_path = db_path
        self._scheduler = scheduler
        self._alert_manager = alert_manager
        self._action_queue = action_queue
        self._knowledge_updater = knowledge_updater
        self._news_aggregator = news_aggregator
        self._briefing_generator = briefing_generator
        self._report_generator = report_generator
        self._parser = NaturalLanguageParser()
        self._custom_callables: Dict[str, Callable] = {}
        self._conn: Optional[sqlite3.Connection] = None
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Create the automations table."""
        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS automations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                trigger_type TEXT NOT NULL,
                trigger_config JSON NOT NULL DEFAULT '{}',
                conditions JSON NOT NULL DEFAULT '[]',
                action_type TEXT NOT NULL,
                action_config JSON NOT NULL DEFAULT '{}',
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_run_at TEXT,
                run_count INTEGER DEFAULT 0,
                metadata JSON DEFAULT '{}',
                scheduler_job_id TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_automations_enabled ON automations(enabled);
            CREATE INDEX IF NOT EXISTS idx_automations_trigger ON automations(trigger_type);
        """)
        self._conn.commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ---------------------------------------------------------------------------
    # Create Automation (from natural language)
    # ---------------------------------------------------------------------------

    def create_automation(self, description: str, name: Optional[str] = None) -> AutomationRule:
        """
        Create an automation from a natural language description.

        Example descriptions:
        - "Every Monday at 9am send me a notification if there are new alerts"
        - "When a claim status changes, notify me"
        - "Every 4 hours fetch knowledge updates"
        - "Every day at 7am generate a briefing"

        Args:
            description: Natural language automation description.
            name: Optional custom name. Auto-generated from description if None.

        Returns:
            The created AutomationRule.
        """
        parsed = self._parser.parse(description)

        now = datetime.now(timezone.utc).isoformat()
        rule = AutomationRule(
            id=f"auto_{uuid.uuid4().hex[:12]}",
            name=name or parsed["name"],
            description=description,
            trigger_type=parsed["trigger_type"],
            trigger_config=parsed["trigger_config"],
            conditions=parsed["conditions"],
            action_type=parsed["action_type"],
            action_config=parsed["action_config"],
            created_at=now,
            updated_at=now,
        )

        self._conn.execute(
            """INSERT INTO automations
               (id, name, description, trigger_type, trigger_config,
                conditions, action_type, action_config, enabled,
                created_at, updated_at, metadata, scheduler_job_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, '{}', NULL)""",
            (
                rule.id, rule.name, rule.description,
                rule.trigger_type, json.dumps(rule.trigger_config),
                json.dumps(rule.conditions),
                rule.action_type, json.dumps(rule.action_config),
                rule.created_at, rule.updated_at,
            ),
        )
        self._conn.commit()

        # Register with scheduler if it's a scheduled trigger
        if rule.enabled and self._scheduler:
            self._register_with_scheduler(rule)

        logger.info("Created automation %s: %s (trigger=%s, action=%s)",
                     rule.id, rule.name, rule.trigger_type, rule.action_type)
        return rule

    # ---------------------------------------------------------------------------
    # Create Automation (structured)
    # ---------------------------------------------------------------------------

    def create_structured_automation(
        self,
        name: str,
        description: str,
        trigger_type: str,
        trigger_config: Dict[str, Any],
        conditions: List[Dict[str, Any]],
        action_type: str,
        action_config: Dict[str, Any],
        enabled: bool = True,
    ) -> AutomationRule:
        """
        Create an automation with explicit structured configuration.

        Args:
            name: Automation name.
            description: Description.
            trigger_type: One of TRIGGER_TYPES.
            trigger_config: Trigger configuration dict.
            conditions: List of condition dicts with field/operator/value.
            action_type: One of ACTION_TYPES.
            action_config: Action configuration dict.
            enabled: Whether the automation is active.

        Returns:
            The created AutomationRule.
        """
        now = datetime.now(timezone.utc).isoformat()
        rule = AutomationRule(
            id=f"auto_{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            conditions=conditions,
            action_type=action_type,
            action_config=action_config,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

        self._conn.execute(
            """INSERT INTO automations
               (id, name, description, trigger_type, trigger_config,
                conditions, action_type, action_config, enabled,
                created_at, updated_at, metadata, scheduler_job_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}', NULL)""",
            (
                rule.id, rule.name, rule.description,
                rule.trigger_type, json.dumps(rule.trigger_config),
                json.dumps(rule.conditions),
                rule.action_type, json.dumps(rule.action_config),
                1 if enabled else 0,
                rule.created_at, rule.updated_at,
            ),
        )
        self._conn.commit()

        if rule.enabled and self._scheduler:
            self._register_with_scheduler(rule)

        logger.info("Created structured automation %s: %s", rule.id, rule.name)
        return rule

    # ---------------------------------------------------------------------------
    # List / Get / Delete
    # ---------------------------------------------------------------------------

    def list_automations(
        self,
        enabled_only: bool = False,
        trigger_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List automations, optionally filtered."""
        query = "SELECT * FROM automations WHERE 1=1"
        params: List[Any] = []

        if enabled_only:
            query += " AND enabled = 1"
        if trigger_type:
            query += " AND trigger_type = ?"
            params.append(trigger_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [dict(self._row_to_rule(r).to_dict()) for r in rows]

    def get_automation(self, automation_id: str) -> Optional[Dict[str, Any]]:
        """Get a single automation by ID."""
        row = self._conn.execute(
            "SELECT * FROM automations WHERE id = ?", (automation_id,)
        ).fetchone()
        if not row:
            return None
        return dict(self._row_to_rule(row).to_dict())

    def delete_automation(self, automation_id: str) -> bool:
        """Delete an automation and remove its scheduler job."""
        row = self._conn.execute(
            "SELECT * FROM automations WHERE id = ?", (automation_id,)
        ).fetchone()
        if not row:
            return False

        rule = self._row_to_rule(row)

        # Remove scheduler job if registered
        if rule.scheduler_job_id and self._scheduler:
            try:
                self._scheduler.remove_job(rule.scheduler_job_id)
            except Exception:
                pass

        self._conn.execute("DELETE FROM automations WHERE id = ?", (automation_id,))
        self._conn.commit()
        logger.info("Deleted automation %s", automation_id)
        return True

    # ---------------------------------------------------------------------------
    # Enable / Disable
    # ---------------------------------------------------------------------------

    def enable_automation(self, automation_id: str) -> Optional[AutomationRule]:
        """Enable an automation and register with scheduler."""
        row = self._conn.execute(
            "SELECT * FROM automations WHERE id = ?", (automation_id,)
        ).fetchone()
        if not row:
            return None

        now_iso = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE automations SET enabled = 1, updated_at = ? WHERE id = ?",
            (now_iso, automation_id),
        )
        self._conn.commit()

        rule = self._row_to_rule(row)
        rule.enabled = True
        rule.updated_at = now_iso

        if self._scheduler:
            self._register_with_scheduler(rule)

        return rule

    def disable_automation(self, automation_id: str) -> Optional[AutomationRule]:
        """Disable an automation and remove its scheduler job."""
        row = self._conn.execute(
            "SELECT * FROM automations WHERE id = ?", (automation_id,)
        ).fetchone()
        if not row:
            return None

        rule = self._row_to_rule(row)

        # Remove scheduler job
        if rule.scheduler_job_id and self._scheduler:
            try:
                self._scheduler.remove_job(rule.scheduler_job_id)
            except Exception:
                pass

        now_iso = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE automations SET enabled = 0, updated_at = ?, scheduler_job_id = NULL WHERE id = ?",
            (now_iso, automation_id),
        )
        self._conn.commit()

        rule.enabled = False
        rule.updated_at = now_iso
        return rule

    # ---------------------------------------------------------------------------
    # Execute
    # ---------------------------------------------------------------------------

    def execute_automation(self, automation_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an automation manually.

        Args:
            automation_id: The automation to execute.
            context: Optional execution context (event data, etc.)

        Returns:
            Execution result dict with status and details.
        """
        row = self._conn.execute(
            "SELECT * FROM automations WHERE id = ?", (automation_id,)
        ).fetchone()
        if not row:
            return {"status": "error", "message": f"Automation {automation_id} not found"}

        rule = self._row_to_rule(row)

        # Check conditions
        if context and not self._evaluate_conditions(rule.conditions, context):
            return {
                "status": "skipped",
                "message": "Conditions not met",
                "automation_id": automation_id,
            }

        # Execute the action
        try:
            result = self._execute_action(rule, context or {})
        except Exception as exc:
            logger.error("Automation %s execution failed: %s", automation_id, exc)
            result = {"status": "error", "message": str(exc)}

        # Update run stats
        now_iso = datetime.now(timezone.utc).isoformat()
        new_count = rule.run_count + 1
        self._conn.execute(
            "UPDATE automations SET last_run_at = ?, run_count = ?, updated_at = ? WHERE id = ?",
            (now_iso, new_count, now_iso, automation_id),
        )
        self._conn.commit()

        return {
            "status": result.get("status", "completed"),
            "automation_id": automation_id,
            "action_result": result,
            "run_count": new_count,
        }

    def _evaluate_conditions(
        self,
        conditions: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate all conditions against the execution context."""
        for cond in conditions:
            field = cond.get("field", "")
            operator = cond.get("operator", "equals")
            expected = cond.get("value")

            actual = context.get(field)
            if actual is None:
                # Try nested lookup
                parts = field.split(".")
                obj = context
                for part in parts:
                    if isinstance(obj, dict):
                        obj = obj.get(part)
                    else:
                        obj = None
                        break
                actual = obj

            op_func = CONDITION_OPERATORS.get(operator)
            if not op_func:
                logger.warning("Unknown condition operator: %s", operator)
                continue

            try:
                if not op_func(actual, expected):
                    return False
            except (TypeError, ValueError) as exc:
                logger.warning("Condition evaluation error: %s", exc)
                return False

        return True

    def _execute_action(
        self,
        rule: AutomationRule,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute the automation's action."""
        action_type = rule.action_type
        config = rule.action_config

        if action_type == "send_notification":
            return self._action_send_notification(config, context)
        elif action_type == "generate_briefing":
            return self._action_generate_briefing(config, context)
        elif action_type == "run_report":
            return self._action_run_report(config, context)
        elif action_type == "fetch_knowledge":
            return self._action_fetch_knowledge(config, context)
        elif action_type == "fetch_news":
            return self._action_fetch_news(config, context)
        elif action_type == "check_threshold":
            return self._action_check_threshold(config, context)
        elif action_type == "webhook":
            return self._action_webhook(config, context)
        elif action_type == "log_message":
            return self._action_log_message(config, context)
        elif action_type == "custom_callable":
            return self._action_custom_callable(config, context)
        else:
            return {"status": "error", "message": f"Unknown action type: {action_type}"}

    # ---------------------------------------------------------------------------
    # Action Implementations
    # ---------------------------------------------------------------------------

    def _action_send_notification(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Send a notification via the alert manager."""
        if not self._alert_manager:
            return {"status": "error", "message": "Alert manager not configured"}

        title = config.get("title", "Automated Notification")
        message = config.get("message", context.get("message", "Automation triggered notification"))
        priority = config.get("priority", "info")
        alert_type = config.get("alert_type", "system_health")

        alert = self._alert_manager.create_alert(
            alert_type=alert_type,
            title=title,
            message=message,
            priority=priority,
            source="automation",
        )
        return {"status": "completed", "alert_id": alert.id}

    def _action_generate_briefing(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a morning briefing."""
        if not self._briefing_generator:
            return {"status": "error", "message": "Briefing generator not configured"}

        briefing = self._briefing_generator.generate()
        channels = config.get("channels", ["chat"])
        delivery = self._briefing_generator.deliver(briefing, channels)
        return {"status": "completed", "briefing_id": briefing.id, "delivery": delivery}

    def _action_run_report(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a weekly report."""
        if not self._report_generator:
            return {"status": "error", "message": "Report generator not configured"}

        report = self._report_generator.generate_report()
        return {"status": "completed", "report_id": report.id}

    def _action_fetch_knowledge(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch knowledge updates."""
        if not self._knowledge_updater:
            return {"status": "error", "message": "Knowledge updater not configured"}

        sources = config.get("sources")
        results = self._knowledge_updater.check_updates(sources=sources)
        total = sum(len(v) for v in results.values())
        return {"status": "completed", "new_updates": total, "sources_checked": list(results.keys())}

    def _action_fetch_news(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch news feeds."""
        if not self._news_aggregator:
            return {"status": "error", "message": "News aggregator not configured"}

        categories = config.get("categories")
        results = self._news_aggregator.fetch_feeds(categories=categories)
        total = sum(len(v) for v in results.values())
        return {"status": "completed", "new_articles": total}

    def _action_check_threshold(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check a threshold and create an alert if crossed."""
        if not self._alert_manager:
            return {"status": "error", "message": "Alert manager not configured"}

        metric = config.get("metric", "unknown")
        threshold = float(config.get("threshold", 0))
        current = float(context.get(metric, config.get("current_value", 0)))
        comparison = config.get("comparison", "gt")
        priority = config.get("priority", "warning")

        alert = self._alert_manager.check_threshold(
            alert_type=config.get("alert_type", "usage_limit"),
            source=config.get("source", "automation"),
            metric_name=metric,
            current_value=current,
            threshold=threshold,
            comparison=comparison,
            priority=priority,
        )
        if alert:
            return {"status": "completed", "alert_id": alert.id, "threshold_crossed": True}
        return {"status": "completed", "threshold_crossed": False}

    def _action_webhook(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Call a webhook URL."""
        url = config.get("url", "")
        if not url:
            return {"status": "error", "message": "No webhook URL configured"}

        method = config.get("method", "POST").upper()
        headers = config.get("headers", {"Content-Type": "application/json"})
        payload = config.get("payload", context)

        try:
            with httpx.Client(timeout=30) as client:
                if method == "POST":
                    resp = client.post(url, json=payload, headers=headers)
                elif method == "GET":
                    resp = client.get(url, params=payload, headers=headers)
                elif method == "PUT":
                    resp = client.put(url, json=payload, headers=headers)
                else:
                    resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()

            return {"status": "completed", "status_code": resp.status_code}
        except Exception as exc:
            return {"status": "error", "message": str(exc)[:200]}

    def _action_log_message(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Log a message."""
        message = config.get("message", "Automation executed")
        level = config.get("level", "info")
        log_func = getattr(logger, level, logger.info)
        log_func("Automation: %s (context: %s)", message, json.dumps(context)[:200])
        return {"status": "completed", "message": message}

    def _action_custom_callable(self, config: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Call a registered custom Python callable."""
        callable_name = config.get("callable", "")
        if not callable_name:
            return {"status": "error", "message": "No callable name specified"}

        func = self._custom_callables.get(callable_name)
        if not func:
            return {"status": "error", "message": f"Callable '{callable_name}' not registered"}

        try:
            result = func(context)
            return {"status": "completed", "result": result}
        except Exception as exc:
            return {"status": "error", "message": str(exc)[:200]}

    # ---------------------------------------------------------------------------
    # Scheduler Integration
    # ---------------------------------------------------------------------------

    def _register_with_scheduler(self, rule: AutomationRule) -> Optional[str]:
        """Register a scheduled automation with the scheduler."""
        if not self._scheduler:
            return None

        def _run_automation():
            self.execute_automation(rule.id)

        job_id = None

        if rule.trigger_type == "schedule_cron":
            cron_expr = rule.trigger_config.get("cron_expr", "0 0 * * *")
            job_id = self._scheduler.add_cron_job(
                _run_automation,
                job_id=f"auto_{rule.id}",
                name=rule.name,
                cron_expr=cron_expr,
            )
        elif rule.trigger_type == "schedule_interval":
            interval_config = rule.trigger_config
            job_id = self._scheduler.add_interval_job(
                _run_automation,
                job_id=f"auto_{rule.id}",
                name=rule.name,
                hours=interval_config.get("hours", 0),
                minutes=interval_config.get("minutes", 0),
                days=interval_config.get("days", 0),
                weeks=interval_config.get("weeks", 0),
            )

        if job_id:
            self._conn.execute(
                "UPDATE automations SET scheduler_job_id = ? WHERE id = ?",
                (job_id, rule.id),
            )
            self._conn.commit()
            rule.scheduler_job_id = job_id

        return job_id

    # ---------------------------------------------------------------------------
    # Event Dispatch
    # ---------------------------------------------------------------------------

    def dispatch_event(self, event_type: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Dispatch an event to all matching automations.

        Used for event-based triggers (alert, knowledge, claim, etc.)

        Args:
            event_type: The event type (e.g., "event_alert").
            context: Event context data.

        Returns:
            List of execution results.
        """
        rows = self._conn.execute(
            "SELECT * FROM automations WHERE trigger_type = ? AND enabled = 1",
            (event_type,),
        ).fetchall()

        results = []
        for row in rows:
            rule = self._row_to_rule(row)
            result = self.execute_automation(rule.id, context)
            results.append(result)

        if results:
            logger.info("Dispatched event %s to %d automations", event_type, len(results))

        return results

    # ---------------------------------------------------------------------------
    # Custom Callables
    # ---------------------------------------------------------------------------

    def register_callable(self, name: str, func: Callable) -> None:
        """Register a custom Python callable for use in automations."""
        self._custom_callables[name] = func
        logger.info("Registered custom callable: %s", name)

    # ---------------------------------------------------------------------------
    # Parse (expose parser)
    # ---------------------------------------------------------------------------

    def parse_description(self, text: str) -> Dict[str, Any]:
        """
        Parse a natural language description without creating an automation.
        Useful for previewing what an automation would look like.
        """
        return self._parser.parse(text)

    # ---------------------------------------------------------------------------
    # Stats
    # ---------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get automation engine statistics."""
        total = self._conn.execute("SELECT COUNT(*) FROM automations").fetchone()[0]
        enabled = self._conn.execute("SELECT COUNT(*) FROM automations WHERE enabled = 1").fetchone()[0]

        by_trigger = {}
        for t in TRIGGER_TYPES:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM automations WHERE trigger_type = ?", (t,)
            ).fetchone()[0]
            if count > 0:
                by_trigger[t] = count

        by_action = {}
        for a in ACTION_TYPES:
            count = self._conn.execute(
                "SELECT COUNT(*) FROM automations WHERE action_type = ?", (a,)
            ).fetchone()[0]
            if count > 0:
                by_action[a] = count

        total_runs = self._conn.execute("SELECT SUM(run_count) FROM automations").fetchone()[0] or 0

        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "total_runs": total_runs,
            "by_trigger_type": by_trigger,
            "by_action_type": by_action,
        }

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    @staticmethod
    def _row_to_rule(row: sqlite3.Row) -> AutomationRule:
        """Convert a database row to an AutomationRule."""
        d = dict(row)

        def _parse_json(raw, default):
            if isinstance(raw, str):
                try:
                    return json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    return default
            return raw or default

        return AutomationRule(
            id=d["id"],
            name=d["name"],
            description=d["description"],
            trigger_type=d["trigger_type"],
            trigger_config=_parse_json(d.get("trigger_config"), {}),
            conditions=_parse_json(d.get("conditions"), []),
            action_type=d["action_type"],
            action_config=_parse_json(d.get("action_config"), {}),
            enabled=bool(d.get("enabled", 1)),
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_run_at=d.get("last_run_at"),
            run_count=d.get("run_count", 0),
            metadata=_parse_json(d.get("metadata"), {}),
            scheduler_job_id=d.get("scheduler_job_id"),
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_engine: Optional[AutomationEngine] = None


def get_automation_engine(**kwargs) -> AutomationEngine:
    """Get or create the singleton AutomationEngine instance."""
    global _engine
    if _engine is None:
        _engine = AutomationEngine(**kwargs)
    return _engine