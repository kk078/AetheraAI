"""
Email Plugin Package for Aethera

Sub-modules:
    reader         - Read/search/categorize emails via IMAP
    composer       - Draft/send emails with approval flow
    auto_processor - Auto-categorize and extract action items
    templates      - Email template management
"""

from .reader import EmailReader
from .composer import EmailComposer
from .auto_processor import AutoProcessor
from .templates import TemplateManager

__all__ = [
    "EmailReader",
    "EmailComposer",
    "AutoProcessor",
    "TemplateManager",
]

__version__ = "1.0.0"