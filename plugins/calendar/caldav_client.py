"""
CalDAV Client for Aethera

Provides CalDAV-compatible calendar operations. Works with any
CalDAV server including Google Calendar (via CalDAV), Outlook,
Nextcloud, Radicle, and others.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree as ET

import aiohttp


# CalDAV XML namespace map
CALDAV_NS = {
    "d": "DAV:",
    "c": "urn:ietf:params:xml:ns:caldav",
    "cs": "http://calendarserver.org/ns/",
}


class CalDAVClient:
    """CalDAV client for calendar operations across multiple providers."""

    def __init__(
        self,
        server_url: str,
        username: str = "",
        password: str = "",
        calendar_path: str = "",
    ):
        """
        Args:
            server_url:    Base CalDAV server URL.
            username:      Authentication username.
            password:      Authentication password or app-specific password.
            calendar_path: Path to the specific calendar (appended to server_url).
        """
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self.calendar_path = calendar_path
        self._session: Optional[aiohttp.ClientSession] = None

    # -- Session lifecycle --------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth(self.username, self.password) if self.username else None
            self._session = aiohttp.ClientSession(
                auth=auth,
                headers={
                    "Content-Type": "application/xml; charset=utf-8",
                    "Depth": "1",
                },
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # -- Low-level CalDAV request -------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> aiohttp.ClientResponse:
        session = await self._ensure_session()
        url = f"{self.server_url}/{path}".replace("//", "/").replace(":/", "://")
        merged_headers = dict(session.headers)
        if headers:
            merged_headers.update(headers)
        async with session.request(method, url, data=body, headers=merged_headers) as resp:
            return resp

    async def _request_text(
        self,
        method: str,
        path: str,
        body: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        session = await self._ensure_session()
        url = f"{self.server_url}/{path}".replace("//", "/").replace(":/", "://")
        merged_headers = dict(session.headers)
        if headers:
            merged_headers.update(headers)
        async with session.request(method, url, data=body, headers=merged_headers) as resp:
            if resp.status >= 400:
                text = await resp.text()
                raise Exception(f"CalDAV error ({resp.status}): {text[:500]}")
            return await resp.text()

    # -- Calendar Discovery --------------------------------------------------

    async def list_calendars(self) -> List[Dict[str, Any]]:
        """Discover available calendars on the CalDAV server.

        Returns:
            List of dicts with keys: href, display_name, calendar_color.
        """
        body = """<?xml version="1.0" encoding="utf-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
            <d:prop>
                <d:displayname/>
                <c:calendar-color/>
                <d:resourcetype/>
            </d:prop>
        </d:propfind>"""

        text = await self._request_text("PROPFIND", "", body, {"Depth": "0"})
        # Also query the well-known path
        try:
            text = await self._request_text("PROPFIND", ".well-known/caldav", body, {"Depth": "1"})
        except Exception:
            pass

        calendars = []
        try:
            root = ET.fromstring(text)
            for response in root.findall(".//d:response", CALDAV_NS):
                href = response.find("d:href", CALDAV_NS)
                display_name = response.find(".//d:displayname", CALDAV_NS)
                color = response.find(".//c:calendar-color", CALDAV_NS)

                calendars.append({
                    "href": href.text if href is not None else "",
                    "display_name": display_name.text if display_name is not None else "",
                    "calendar_color": color.text if color is not None else "",
                })
        except ET.ParseError:
            pass

        return calendars

    async def get_calendar_home(self) -> str:
        """Get the calendar home set URL.

        Returns:
            Calendar home URL path.
        """
        body = """<?xml version="1.0" encoding="utf-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
            <d:prop>
                <c:calendar-home-set/>
            </d:prop>
        </d:propfind>"""

        text = await self._request_text("PROPFIND", "", body, {"Depth": "0"})
        try:
            root = ET.fromstring(text)
            href = root.find(".//c:calendar-home-set/d:href", CALDAV_NS)
            if href is not None and href.text:
                return href.text
        except ET.ParseError:
            pass
        return ""

    # -- Event Operations ---------------------------------------------------

    async def list_events(
        self,
        start: datetime,
        end: datetime,
        calendar_path: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List events in a time range using CalDAV calendar-query.

        Args:
            start:         Start datetime.
            end:           End datetime.
            calendar_path: Override default calendar path.

        Returns:
            List of event dicts with keys: uid, summary, start, end, location.
        """
        cal_path = calendar_path or self.calendar_path
        start_str = start.strftime("%Y%m%dT%H%M%SZ")
        end_str = end.strftime("%Y%m%dT%H%M%SZ")

        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
            <d:prop>
                <d:getetag/>
                <c:calendar-data/>
            </d:prop>
            <c:filter>
                <c:comp-filter name="VCALENDAR">
                    <c:comp-filter name="VEVENT">
                        <c:time-range start="{start_str}" end="{end_str}"/>
                    </c:comp-filter>
                </c:comp-filter>
            </c:filter>
        </c:calendar-query>"""

        text = await self._request_text("REPORT", cal_path, body, {"Depth": "1"})

        events = []
        try:
            root = ET.fromstring(text)
            for response in root.findall(".//d:response", CALDAV_NS):
                caldata = response.find(".//c:calendar-data", CALDAV_NS)
                if caldata is not None and caldata.text:
                    event = self._parse_icalendar(caldata.text)
                    if event:
                        events.append(event)
        except ET.ParseError:
            pass

        return events

    async def get_event(self, event_uid: str, calendar_path: Optional[str] = None) -> Dict[str, Any]:
        """Get a specific event by UID.

        Returns:
            Dict with event details.
        """
        cal_path = calendar_path or self.calendar_path

        body = f"""<?xml version="1.0" encoding="utf-8"?>
        <c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
            <d:prop>
                <c:calendar-data/>
            </d:prop>
            <c:filter>
                <c:comp-filter name="VCALENDAR">
                    <c:comp-filter name="VEVENT">
                        <c:prop-filter name="UID">
                            <c:text-match collation="i;ascii-casemap">{event_uid}</c:text-match>
                        </c:prop-filter>
                    </c:comp-filter>
                </c:comp-filter>
            </c:filter>
        </c:calendar-query>"""

        text = await self._request_text("REPORT", cal_path, body, {"Depth": "0"})

        try:
            root = ET.fromstring(text)
            caldata = root.find(".//c:calendar-data", CALDAV_NS)
            if caldata is not None and caldata.text:
                event = self._parse_icalendar(caldata.text)
                if event:
                    return event
        except ET.ParseError:
            pass

        raise Exception(f"Event {event_uid} not found")

    async def create_event(
        self,
        uid: str,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        location: str = "",
        attendees: Optional[List[str]] = None,
        calendar_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new calendar event via CalDAV PUT.

        Args:
            uid:           Unique event identifier.
            summary:       Event title/summary.
            start:         Start datetime.
            end:           End datetime.
            description:   Event description.
            location:      Event location.
            attendees:     List of attendee email addresses.
            calendar_path: Override default calendar path.

        Returns:
            Dict with created event details.
        """
        cal_path = calendar_path or self.calendar_path
        event_path = f"{cal_path}/{uid}.ics"

        # Build iCalendar content
        dtstart = start.strftime("%Y%m%dT%H%M%SZ")
        dtend = end.strftime("%Y%m%dT%H%M%SZ")
        dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

        attendee_lines = ""
        if attendees:
            for att in attendees:
                attendee_lines += f"\r\nATTENDEE;CN={att};RSVP=TRUE:mailto:{att}"

        ical = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//AetheraAI//CalDAVClient//EN\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{dtstamp}\r\n"
            f"DTSTART:{dtstart}\r\n"
            f"DTEND:{dtend}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DESCRIPTION:{description}\r\n"
            f"LOCATION:{location}\r\n"
            f"{attendee_lines}\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )

        await self._request_text(
            "PUT",
            event_path,
            ical,
            {"Content-Type": "text/calendar; charset=utf-8"},
        )

        return {
            "uid": uid,
            "summary": summary,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }

    async def update_event(
        self,
        uid: str,
        summary: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update an existing event. Fetches the current event and re-PUTs with changes.

        Returns:
            Dict with updated event details.
        """
        cal_path = calendar_path or self.calendar_path

        # Get current event
        current = await self.get_event(uid, cal_path)

        # Merge updates
        new_summary = summary if summary is not None else current.get("summary", "")
        new_description = description if description is not None else current.get("description", "")
        new_location = location if location is not None else current.get("location", "")

        # Parse current start/end or use provided
        new_start = start
        new_end = end
        if new_start is None:
            start_str = current.get("start", "")
            if start_str:
                try:
                    new_start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                except ValueError:
                    new_start = datetime.utcnow()
            else:
                new_start = datetime.utcnow()
        if new_end is None:
            end_str = current.get("end", "")
            if end_str:
                try:
                    new_end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                except ValueError:
                    new_end = new_start + timedelta(hours=1)
            else:
                new_end = new_start + timedelta(hours=1)

        # Re-create the event (CalDAV PUT overwrites)
        return await self.create_event(
            uid=uid,
            summary=new_summary,
            start=new_start,
            end=new_end,
            description=new_description,
            location=new_location,
            calendar_path=cal_path,
        )

    async def delete_event(self, uid: str, calendar_path: Optional[str] = None) -> bool:
        """Delete an event.

        Returns:
            True on success.
        """
        cal_path = calendar_path or self.calendar_path
        event_path = f"{cal_path}/{uid}.ics"

        session = await self._ensure_session()
        url = f"{self.server_url}/{event_path}".replace("//", "/").replace(":/", "://")
        async with session.delete(url) as resp:
            return resp.status in (200, 204, 404)

    # -- iCalendar Parsing --------------------------------------------------

    @staticmethod
    def _parse_icalendar(ical_text: str) -> Optional[Dict[str, Any]]:
        """Parse a simple VEVENT from iCalendar text.

        This is a lightweight parser for the common VEVENT fields.
        For full iCalendar support, use the icalendar library.

        Returns:
            Dict with event details or None.
        """
        event: Dict[str, Any] = {
            "uid": "",
            "summary": "",
            "description": "",
            "start": "",
            "end": "",
            "location": "",
            "attendees": [],
        }

        in_event = False
        for line in ical_text.splitlines():
            line = line.strip()
            if line == "BEGIN:VEVENT":
                in_event = True
                continue
            if line == "END:VEVENT":
                break
            if not in_event:
                continue

            if line.startswith("UID:"):
                event["uid"] = line[4:]
            elif line.startswith("SUMMARY:"):
                event["summary"] = line[8:]
            elif line.startswith("DESCRIPTION:"):
                event["description"] = line[12:]
            elif line.startswith("DTSTART"):
                # Handle DTSTART;VALUE=DATE: and DTSTART: formats
                if ":" in line:
                    event["start"] = line.split(":", 1)[1]
            elif line.startswith("DTEND"):
                if ":" in line:
                    event["end"] = line.split(":", 1)[1]
            elif line.startswith("LOCATION:"):
                event["location"] = line[9:]
            elif line.startswith("ATTENDEE"):
                # Extract email from ATTENDEE lines
                if "mailto:" in line:
                    email = line.split("mailto:")[-1].strip()
                    event["attendees"].append(email)

        if not event["uid"]:
            return None
        return event