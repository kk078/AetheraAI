"""
Cloudflare Plugin Package for Aethera

Sub-modules:
    dns_manager      - DNS record CRUD operations via Cloudflare API v4
    tunnel_manager   - Tunnel create/delete/status/config
    pages_manager    - Pages project deployment
    workers_manager  - Workers script management
    analytics        - Traffic/security/performance analytics
    security         - WAF, DDoS, SSL, firewall rules
    access_manager   - Zero Trust access policies
    r2_storage       - R2 object storage operations
"""

from .dns_manager import DNSManager
from .tunnel_manager import TunnelManager
from .pages_manager import PagesManager
from .workers_manager import WorkersManager
from .analytics import CloudflareAnalytics
from .security import SecurityManager
from .access_manager import AccessManager
from .r2_storage import R2StorageManager

__all__ = [
    "DNSManager",
    "TunnelManager",
    "PagesManager",
    "WorkersManager",
    "CloudflareAnalytics",
    "SecurityManager",
    "AccessManager",
    "R2StorageManager",
]

__version__ = "1.0.0"