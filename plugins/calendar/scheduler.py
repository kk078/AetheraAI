"""
Calendar Scheduler for Aethera

Provides free time finding, meeting scheduling, and conflict detection.
Works with events from any CalDAV or API-backed calendar source.
"""
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple


class Scheduler:
    """Find free time, schedule meetings, and detect calendar conflicts."""

    def __init__(
        self,
        working_hours_start: int = 9,
        working_hours_end: int = 17,
        working_days: Optional[List[int]] = None,
        default_meeting_duration: int = 30,
        buffer_minutes: int = 15,
    ):
        """
        Args:
            working_hours_start:     Start of working hours (24h, default 9).
            working_hours_end:       End of working hours (24h, default 17).
            working_days:            List of weekday numbers (0=Monday ... 6=Sunday). Default: Mon-Fri.
            default_meeting_duration: Default meeting length in minutes.
            buffer_minutes:          Buffer between meetings in minutes.
        """
        self.working_hours_start = working_hours_start
        self.working_hours_end = working_hours_end
        self.working_days = working_days or [0, 1, 2, 3, 4]  # Mon-Fri
        self.default_meeting_duration = default_meeting_duration
        self.buffer_minutes = buffer_minutes

    # -- Free Time Finding --------------------------------------------------

    def find_free_time(
        self,
        events: List[Dict[str, Any]],
        start: datetime,
        end: datetime,
        duration_minutes: int = 0,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find available free time slots within a date range.

        Args:
            events:           List of event dicts with 'start' and 'end' keys.
            start:            Search window start.
            end:              Search window end.
            duration_minutes: Required minimum slot duration. Uses default if 0.
            max_results:      Maximum number of slots to return.

        Returns:
            List of free slot dicts with keys: start, end, duration_minutes.
        """
        duration = duration_minutes or self.default_meeting_duration

        # Parse and sort events
        parsed_events = self._parse_events(events)
        parsed_events.sort(key=lambda e: e[0])

        # Build blocks of working time per day
        free_slots: List[Dict[str, Any]] = []
        current_date = start.date() if hasattr(start, "date") else start
        end_date = end.date() if hasattr(end, "date") else end

        while current_date <= end_date and len(free_slots) < max_results:
            # Check if this is a working day
            weekday = current_date.weekday() if hasattr(current_date, "weekday") else 0
            if weekday in self.working_days:
                day_start = datetime(
                    current_date.year, current_date.month, current_date.day,
                    self.working_hours_start, 0, 0,
                )
                day_end = datetime(
                    current_date.year, current_date.month, current_date.day,
                    self.working_hours_end, 0, 0,
                )

                # Clip to search window
                if day_start < start:
                    day_start = start
                if day_end > end:
                    day_end = end

                # Get events for this day
                day_events = [
                    (s, e) for s, e in parsed_events
                    if s < day_end and e > day_start
                ]

                # Find gaps
                slots = self._find_gaps(day_start, day_end, day_events, duration, max_results - len(free_slots))
                free_slots.extend(slots)

            current_date = current_date + timedelta(days=1) if hasattr(current_date, "__add__") else current_date

        return free_slots[:max_results]

    def find_free_time_for_attendees(
        self,
        attendee_events: Dict[str, List[Dict[str, Any]]],
        start: datetime,
        end: datetime,
        duration_minutes: int = 0,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find free time slots across multiple attendees.

        Args:
            attendee_events: Dict mapping attendee name/email to their event list.
            start:          Search window start.
            end:            Search window end.
            duration_minutes: Required slot duration.
            max_results:    Maximum results.

        Returns:
            List of free slot dicts.
        """
        # Merge all events from all attendees
        all_events: List[Dict[str, Any]] = []
        for attendee, events in attendee_events.items():
            all_events.extend(events)

        return self.find_free_time(all_events, start, end, duration_minutes, max_results)

    def _find_gaps(
        self,
        day_start: datetime,
        day_end: datetime,
        events: List[Tuple[datetime, datetime]],
        duration: int,
        max_slots: int,
    ) -> List[Dict[str, Any]]:
        """Find gaps between events within a day."""
        gaps: List[Dict[str, Any]] = []
        current = day_start

        for event_start, event_end in sorted(events):
            # Add buffer before the event
            buffered_start = event_start - timedelta(minutes=self.buffer_minutes)

            if current < buffered_start:
                gap_minutes = (buffered_start - current).total_seconds() / 60
                if gap_minutes >= duration:
                    gaps.append({
                        "start": current.isoformat(),
                        "end": buffered_start.isoformat(),
                        "duration_minutes": int(gap_minutes),
                    })
                    if len(gaps) >= max_slots:
                        return gaps

            # Move current past the event (with buffer after)
            current = max(current, event_end + timedelta(minutes=self.buffer_minutes))

        # Check remaining time until day end
        if current < day_end:
            gap_minutes = (day_end - current).total_seconds() / 60
            if gap_minutes >= duration:
                gaps.append({
                    "start": current.isoformat(),
                    "end": day_end.isoformat(),
                    "duration_minutes": int(gap_minutes),
                })

        return gaps

    # -- Conflict Detection -------------------------------------------------

    def detect_conflicts(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect time conflicts (overlaps) between events.

        Args:
            events: List of event dicts with 'start', 'end', and 'summary' keys.

        Returns:
            List of conflict dicts, each containing the two overlapping events.
        """
        parsed = self._parse_events_with_data(events)
        parsed.sort(key=lambda e: e[0])

        conflicts: List[Dict[str, Any]] = []
        for i in range(len(parsed)):
            for j in range(i + 1, len(parsed)):
                start_a, end_a, data_a = parsed[i]
                start_b, end_b, data_b = parsed[j]

                # Check for overlap
                if start_a < end_b and start_b < end_a:
                    overlap_start = max(start_a, start_b)
                    overlap_end = min(end_a, end_b)
                    overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60

                    conflicts.append({
                        "event_a": {
                            "summary": data_a.get("summary", ""),
                            "start": start_a.isoformat(),
                            "end": end_a.isoformat(),
                        },
                        "event_b": {
                            "summary": data_b.get("summary", ""),
                            "start": start_b.isoformat(),
                            "end": end_b.isoformat(),
                        },
                        "overlap_minutes": int(overlap_minutes),
                        "overlap_start": overlap_start.isoformat(),
                        "overlap_end": overlap_end.isoformat(),
                    })

        return conflicts

    def detect_conflicts_for_new_event(
        self,
        new_event_start: datetime,
        new_event_end: datetime,
        existing_events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Detect conflicts for a proposed new event against existing events.

        Args:
            new_event_start:  Proposed event start.
            new_event_end:    Proposed event end.
            existing_events:  List of existing event dicts.

        Returns:
            List of conflict dicts with the conflicting existing events.
        """
        conflicts: List[Dict[str, Any]] = []
        parsed = self._parse_events_with_data(existing_events)

        for start, end, data in parsed:
            if new_event_start < end and start < new_event_end:
                overlap_start = max(new_event_start, start)
                overlap_end = min(new_event_end, end)
                overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60

                conflicts.append({
                    "conflicting_event": {
                        "summary": data.get("summary", ""),
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                    },
                    "overlap_minutes": int(overlap_minutes),
                    "overlap_start": overlap_start.isoformat(),
                    "overlap_end": overlap_end.isoformat(),
                })

        return conflicts

    # -- Meeting Scheduling --------------------------------------------------

    def suggest_meeting_times(
        self,
        events: List[Dict[str, Any]],
        duration_minutes: int = 0,
        preferred_start: Optional[datetime] = None,
        days_ahead: int = 7,
        max_suggestions: int = 5,
    ) -> List[Dict[str, Any]]:
        """Suggest optimal meeting times based on existing events.

        Args:
            events:          Existing events.
            duration_minutes: Required meeting duration.
            preferred_start:  Preferred start datetime (search begins here).
            days_ahead:      How many days ahead to search.
            max_suggestions: Maximum number of suggestions.

        Returns:
            List of suggested time slot dicts.
        """
        start = preferred_start or datetime.now()
        end = start + timedelta(days=days_ahead)
        duration = duration_minutes or self.default_meeting_duration

        free_slots = self.find_free_time(events, start, end, duration, max_results=50)

        # Score each slot based on preferences
        scored_slots: List[Dict[str, Any]] = []
        for slot in free_slots:
            slot_start = datetime.fromisoformat(slot["start"])
            score = self._score_slot(slot_start, slot["duration_minutes"])
            scored_slots.append({**slot, "score": score})

        # Sort by score descending
        scored_slots.sort(key=lambda s: s["score"], reverse=True)

        return scored_slots[:max_suggestions]

    def _score_slot(self, slot_start: datetime, duration_minutes: int) -> float:
        """Score a time slot based on preference heuristics.

        Higher score = better slot. Factors:
        - Morning slots preferred (9-12)
        - Tuesday-Thursday preferred
        - Longer gaps preferred
        - Closer to now is slightly preferred
        """
        score = 0.0

        # Morning preference (9-12)
        hour = slot_start.hour
        if 9 <= hour < 12:
            score += 3.0
        elif 13 <= hour < 15:
            score += 2.0
        elif 15 <= hour < 17:
            score += 1.0

        # Day preference (Tue=1, Wed=2, Thu=3 are best)
        weekday = slot_start.weekday()
        if weekday in (1, 2, 3):  # Tue, Wed, Thu
            score += 2.0
        elif weekday == 0:  # Monday
            score += 1.0
        elif weekday == 4:  # Friday
            score += 0.5

        # Duration preference (longer free time = better)
        if duration_minutes >= 60:
            score += 2.0
        elif duration_minutes >= 30:
            score += 1.0

        # Recency preference (sooner is slightly better)
        days_from_now = (slot_start - datetime.now()).total_seconds() / 86400
        if days_from_now <= 1:
            score += 1.5
        elif days_from_now <= 3:
            score += 1.0
        elif days_from_now <= 5:
            score += 0.5

        return round(score, 2)

    # -- Helpers ------------------------------------------------------------

    def _parse_events(self, events: List[Dict[str, Any]]) -> List[Tuple[datetime, datetime]]:
        """Parse events into (start, end) datetime tuples."""
        parsed = []
        for event in events:
            try:
                start = self._parse_datetime(event.get("start", ""))
                end = self._parse_datetime(event.get("end", ""))
                if start and end:
                    parsed.append((start, end))
            except (ValueError, TypeError):
                continue
        return parsed

    def _parse_events_with_data(
        self, events: List[Dict[str, Any]]
    ) -> List[Tuple[datetime, datetime, Dict[str, Any]]]:
        """Parse events into (start, end, data) tuples preserving event data."""
        parsed = []
        for event in events:
            try:
                start = self._parse_datetime(event.get("start", ""))
                end = self._parse_datetime(event.get("end", ""))
                if start and end:
                    parsed.append((start, end, event))
            except (ValueError, TypeError):
                continue
        return parsed

    @staticmethod
    def _parse_datetime(dt_str: str) -> Optional[datetime]:
        """Parse a datetime string in various formats."""
        if not dt_str:
            return None

        # Handle ISO format with timezone
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y%m%dT%H%M%SZ",
            "%Y%m%dT%H%M%S",
            "%Y-%m-%d",
        ]:
            try:
                return datetime.strptime(dt_str.replace("+00:00", "").replace("Z", ""), fmt)
            except ValueError:
                continue

        # Last resort: try fromisoformat
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            return None