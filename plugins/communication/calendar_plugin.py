"""
Calendar Plugin for Aethera
Manages calendar events via Google Calendar API or Microsoft Graph.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from ..plugin_base import AetheraPlugin, PluginConfig, PluginParameter, PluginResult


class CalendarPlugin(AetheraPlugin):
    """Calendar integration plugin supporting Google and Microsoft."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.provider = config.get('provider', 'google')  # google, microsoft
        self.credentials = config.get('credentials', {})
        self._session = None

    def get_config(self) -> PluginConfig:
        return PluginConfig(
            name='calendar',
            version='1.0.0',
            description='Manage calendar events via Google Calendar or Microsoft Graph',
            author='Aethera AI',
            parameters=[
                PluginParameter(
                    name='action',
                    type='action',
                    description='Action to perform',
                    required=True,
                    choices=[
                        'list_events', 'get_event', 'create_event', 'update_event', 'delete_event',
                        'find_free_time', 'accept_event', 'decline_event',
                    ]
                ),
                PluginParameter(name='event_id', type='str', description='Event ID', required=False),
                PluginParameter(name='title', type='str', description='Event title', required=False),
                PluginParameter(name='description', type='str', description='Event description', required=False),
                PluginParameter(name='location', type='str', description='Event location', required=False),
                PluginParameter(name='start', type='str', description='Start time (ISO format)', required=False),
                PluginParameter(name='end', type='str', description='End time (ISO format)', required=False),
                PluginParameter(name='attendees', type='list', description='Attendee emails', required=False),
                PluginParameter(name='duration_minutes', type='int', description='Duration in minutes', required=False),
                PluginParameter(name='within_days', type='int', description='Search window in days', required=False, default=7),
                PluginParameter(name='response', type='str', description='RSVP response', required=False, choices=['accepted', 'declined', 'tentative']),
            ],
            permissions=['calendar:read', 'calendar:write'],
            dependencies=['aiohttp'],
        )

    async def _do_initialize(self) -> None:
        """Initialize based on provider."""
        if self.provider == 'google' and not self.credentials.get('token'):
            raise ValueError("Google Calendar credentials required")
        elif self.provider == 'microsoft' and not self.credentials.get('access_token'):
            raise ValueError("Microsoft Graph credentials required")

    async def execute(self, action: str, parameters: Dict[str, Any]) -> PluginResult:
        """Execute calendar action."""
        action_map = {
            'list_events': self._list_events,
            'get_event': self._get_event,
            'create_event': self._create_event,
            'update_event': self._update_event,
            'delete_event': self._delete_event,
            'find_free_time': self._find_free_time,
            'accept_event': self._rsvp_event,
            'decline_event': self._rsvp_event,
        }

        if action not in action_map:
            return PluginResult(success=False, error=f"Unknown action: {action}")

        try:
            result = await action_map[action](parameters)
            return PluginResult(success=True, data=result)
        except Exception as e:
            return PluginResult(success=False, error=str(e))

    async def _list_events(self, params: Dict) -> List[Dict]:
        """List calendar events."""
        start = params.get('start', datetime.now().isoformat())
        end = params.get('end', (datetime.now() + timedelta(days=7)).isoformat())

        if self.provider == 'google':
            return await self._google_list_events(start, end)
        else:
            return await self._microsoft_list_events(start, end)

    async def _google_list_events(self, start: str, end: str) -> List[Dict]:
        """List Google Calendar events."""
        import aiohttp

        url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
        token = self.credentials.get('token', '')

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.get(url, params={
                'timeMin': start,
                'timeMax': end,
                'singleEvents': 'true',
                'orderBy': 'startTime',
            }) as resp:
                data = await resp.json()
                return [
                    {
                        'id': e['id'],
                        'summary': e.get('summary', 'No Title'),
                        'start': e['start'].get('dateTime', e['start'].get('date')),
                        'end': e['end'].get('dateTime', e['end'].get('date')),
                        'attendees': [a['email'] for a in e.get('attendees', [])],
                        'location': e.get('location', ''),
                    }
                    for e in data.get('items', [])
                ]

    async def _microsoft_list_events(self, start: str, end: str) -> List[Dict]:
        """List Microsoft Graph events."""
        import aiohttp

        url = 'https://graph.microsoft.com/v1.0/me/events'
        token = self.credentials.get('access_token', '')

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.get(url, params={
                'startdatetime': start,
                'enddatetime': end,
            }) as resp:
                data = await resp.json()
                return [
                    {
                        'id': e['id'],
                        'subject': e.get('subject', 'No Title'),
                        'start': e['start']['dateTime'],
                        'end': e['end']['dateTime'],
                        'attendees': [a['emailAddress']['address'] for a in e.get('attendees', [])],
                        'location': e.get('location', {}).get('displayName', ''),
                    }
                    for e in data.get('value', [])
                ]

    async def _get_event(self, params: Dict) -> Dict:
        """Get event details."""
        event_id = params.get('event_id')
        if not event_id:
            raise ValueError("Event ID required")

        if self.provider == 'google':
            return await self._google_get_event(event_id)
        else:
            return await self._microsoft_get_event(event_id)

    async def _google_get_event(self, event_id: str) -> Dict:
        """Get Google Calendar event."""
        import aiohttp

        url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
        token = self.credentials.get('token', '')

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.get(url) as resp:
                e = await resp.json()
                return {
                    'id': e['id'],
                    'summary': e.get('summary', 'No Title'),
                    'description': e.get('description', ''),
                    'start': e['start'].get('dateTime', e['start'].get('date')),
                    'end': e['end'].get('dateTime', e['end'].get('date')),
                    'attendees': [a['email'] for a in e.get('attendees', [])],
                    'location': e.get('location', ''),
                }

    async def _microsoft_get_event(self, event_id: str) -> Dict:
        """Get Microsoft Graph event."""
        import aiohttp

        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        token = self.credentials.get('access_token', '')

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.get(url) as resp:
                e = await resp.json()
                return {
                    'id': e['id'],
                    'subject': e.get('subject', 'No Title'),
                    'body': e.get('body', {}).get('content', ''),
                    'start': e['start']['dateTime'],
                    'end': e['end']['dateTime'],
                    'attendees': [a['emailAddress']['address'] for a in e.get('attendees', [])],
                    'location': e.get('location', {}).get('displayName', ''),
                }

    async def _create_event(self, params: Dict) -> Dict:
        """Create calendar event."""
        if not params.get('title'):
            raise ValueError("Event title required")
        if not params.get('start') or not params.get('end'):
            raise ValueError("Start and end times required")

        if self.provider == 'google':
            return await self._google_create_event(params)
        else:
            return await self._microsoft_create_event(params)

    async def _google_create_event(self, params: Dict) -> Dict:
        """Create Google Calendar event."""
        import aiohttp

        url = 'https://www.googleapis.com/calendar/v3/calendars/primary/events'
        token = self.credentials.get('token', '')

        data = {
            'summary': params['title'],
            'description': params.get('description', ''),
            'location': params.get('location', ''),
            'start': {'dateTime': params['start'], 'timeZone': 'UTC'},
            'end': {'dateTime': params['end'], 'timeZone': 'UTC'},
        }

        if params.get('attendees'):
            data['attendees'] = [{'email': a} for a in params['attendees']]

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.post(url, json=data) as resp:
                e = await resp.json()
                return {
                    'id': e['id'],
                    'url': e.get('htmlLink', ''),
                }

    async def _microsoft_create_event(self, params: Dict) -> Dict:
        """Create Microsoft Graph event."""
        import aiohttp

        url = 'https://graph.microsoft.com/v1.0/me/events'
        token = self.credentials.get('access_token', '')

        data = {
            'subject': params['title'],
            'body': {'contentType': 'text', 'content': params.get('description', '')},
            'location': {'displayName': params.get('location', '')},
            'start': {'dateTime': params['start'], 'timeZone': 'UTC'},
            'end': {'dateTime': params['end'], 'timeZone': 'UTC'},
        }

        if params.get('attendees'):
            data['attendees'] = [
                {'emailAddress': {'address': a}, 'type': 'required'}
                for a in params['attendees']
            ]

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.post(url, json=data) as resp:
                e = await resp.json()
                return {
                    'id': e['id'],
                    'url': e.get('webLink', ''),
                }

    async def _update_event(self, params: Dict) -> Dict:
        """Update calendar event."""
        event_id = params.get('event_id')
        if not event_id:
            raise ValueError("Event ID required")

        if self.provider == 'google':
            return await self._google_update_event(event_id, params)
        else:
            return await self._microsoft_update_event(event_id, params)

    async def _google_update_event(self, event_id: str, params: Dict) -> Dict:
        """Update Google Calendar event."""
        import aiohttp

        url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
        token = self.credentials.get('token', '')

        data = {}
        if params.get('title'):
            data['summary'] = params['title']
        if params.get('description'):
            data['description'] = params['description']
        if params.get('location'):
            data['location'] = params['location']
        if params.get('start'):
            data['start'] = {'dateTime': params['start'], 'timeZone': 'UTC'}
        if params.get('end'):
            data['end'] = {'dateTime': params['end'], 'timeZone': 'UTC'}

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.put(url, json=data) as resp:
                e = await resp.json()
                return {'id': e['id'], 'updated': True}

    async def _microsoft_update_event(self, event_id: str, params: Dict) -> Dict:
        """Update Microsoft Graph event."""
        import aiohttp

        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        token = self.credentials.get('access_token', '')

        data = {}
        if params.get('title'):
            data['subject'] = params['title']
        if params.get('description'):
            data['body'] = {'contentType': 'text', 'content': params['description']}
        if params.get('location'):
            data['location'] = {'displayName': params['location']}
        if params.get('start'):
            data['start'] = {'dateTime': params['start'], 'timeZone': 'UTC'}
        if params.get('end'):
            data['end'] = {'dateTime': params['end'], 'timeZone': 'UTC'}

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.patch(url, json=data) as resp:
                await resp.json()
                return {'id': event_id, 'updated': True}

    async def _delete_event(self, params: Dict) -> bool:
        """Delete calendar event."""
        event_id = params.get('event_id')
        if not event_id:
            raise ValueError("Event ID required")

        if self.provider == 'google':
            await self._google_delete_event(event_id)
        else:
            await self._microsoft_delete_event(event_id)
        return True

    async def _google_delete_event(self, event_id: str) -> None:
        """Delete Google Calendar event."""
        import aiohttp

        url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
        token = self.credentials.get('token', '')

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.delete(url):
                pass

    async def _microsoft_delete_event(self, event_id: str) -> None:
        """Delete Microsoft Graph event."""
        import aiohttp

        url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}'
        token = self.credentials.get('access_token', '')

        async with aiohttp.ClientSession(
            headers={'Authorization': f'Bearer {token}'}
        ) as session:
            async with session.delete(url):
                pass

    async def _find_free_time(self, params: Dict) -> List[Dict]:
        """Find free time slots."""
        duration = params.get('duration_minutes', 30)
        within_days = params.get('within_days', 7)

        events = await self._list_events({
            'start': datetime.now().isoformat(),
            'end': (datetime.now() + timedelta(days=within_days)).isoformat(),
        })

        # Find gaps between events
        free_slots = []
        current_time = datetime.now()
        end_search = current_time + timedelta(days=within_days)

        sorted_events = sorted(events, key=lambda e: e['start'])

        for event in sorted_events:
            # Parse ISO datetime strings, preserving timezone info
            start_str = event['start']
            end_str = event['end']
            # Handle Z suffix and +00:00 properly
            if start_str.endswith('Z'):
                start_str = start_str[:-1] + '+00:00'
            if end_str.endswith('Z'):
                end_str = end_str[:-1] + '+00:00'
            event_start = datetime.fromisoformat(start_str)
            event_end = datetime.fromisoformat(end_str)

            if current_time < event_start:
                gap_minutes = (event_start - current_time).total_seconds() / 60
                if gap_minutes >= duration:
                    free_slots.append({
                        'start': current_time.isoformat(),
                        'end': event_start.isoformat(),
                        'duration_minutes': int(gap_minutes),
                    })

            current_time = max(current_time, event_end)

        # Check remaining time until end_search
        if current_time < end_search:
            gap_minutes = (end_search - current_time).total_seconds() / 60
            if gap_minutes >= duration:
                free_slots.append({
                    'start': current_time.isoformat(),
                    'end': end_search.isoformat(),
                    'duration_minutes': int(gap_minutes),
                })

        return free_slots[:10]  # Return top 10 slots

    async def _rsvp_event(self, params: Dict) -> Dict:
        """Accept or decline a calendar event invitation."""
        import aiohttp

        event_id = params.get('event_id')
        response = params.get('response', 'accepted')  # accepted, tentative, declined

        if not event_id:
            raise ValueError("Event ID required")

        valid_responses = ['accepted', 'tentative', 'declined']
        if response not in valid_responses:
            raise ValueError(f"Invalid response '{response}'. Must be one of: {valid_responses}")

        if self.provider == 'google':
            # Google Calendar: events.respond endpoint
            url = f'https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}'
            token = self.credentials.get('token', '')

            async with aiohttp.ClientSession(
                headers={'Authorization': f'Bearer {token}'}
            ) as session:
                # First get the event to find the attendees
                async with session.get(url) as resp:
                    if resp.status >= 400:
                        error = await resp.json()
                        raise Exception(f"Google Calendar API error: {error.get('message', 'Unknown')}")
                    event = await resp.json()

                # Update the attendee's response status
                attendees = event.get('attendees', [])
                updated = False
                for attendee in attendees:
                    if attendee.get('self', False):
                        attendee['responseStatus'] = response
                        updated = True
                        break

                if not updated:
                    # Add self as attendee if not present
                    attendees.append({'self': True, 'responseStatus': response})

                update_data = {'attendees': attendees}
                async with session.patch(url, json=update_data) as resp:
                    if resp.status >= 400:
                        error = await resp.json()
                        raise Exception(f"Google Calendar RSVP error: {error.get('message', 'Unknown')}")
                    result = await resp.json()

                return {'event_id': event_id, 'response': response, 'status': 'confirmed'}

        else:
            # Microsoft Graph: events/{id}/accept, decline, or tentativelyAccept
            action_map = {
                'accepted': 'accept',
                'tentative': 'tentativelyAccept',
                'declined': 'decline',
            }
            action = action_map.get(response, 'accept')
            url = f'https://graph.microsoft.com/v1.0/me/events/{event_id}/{action}'
            token = self.credentials.get('access_token', '')

            async with aiohttp.ClientSession(
                headers={'Authorization': f'Bearer {token}'}
            ) as session:
                async with session.post(url, json={}) as resp:
                    if resp.status >= 400:
                        error = await resp.json()
                        raise Exception(f"Microsoft Graph RSVP error: {error.get('message', 'Unknown')}")

                return {'event_id': event_id, 'response': response, 'status': 'confirmed'}


def register_plugin():
    """Register the Calendar plugin."""
    import os
    return CalendarPlugin, {
        'provider': os.getenv('CALENDAR_PROVIDER', 'google'),
        'credentials': {
            'token': os.getenv('GOOGLE_CALENDAR_TOKEN', ''),
            'access_token': os.getenv('MICROSOFT_ACCESS_TOKEN', ''),
        },
        'enabled': True,
    }
