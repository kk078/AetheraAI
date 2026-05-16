"""
Calendar Plugin Package for Aethera

Sub-modules:
    caldav_client - CalDAV client (works with Google, Outlook, Nextcloud)
    scheduler     - Find free time, schedule meetings, detect conflicts
"""

from .caldav_client import CalDAVClient
from .scheduler import Scheduler

__all__ = [
    "CalDAVClient",
    "Scheduler",
]

__version__ = "1.0.0"