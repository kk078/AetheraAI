"""
GitHub Plugin Package for Aethera

Sub-modules:
    repos        - Repository management, code search
    issues       - Issue/PR management
    actions      - CI/CD workflow status
    code_review  - Automated code review suggestions
"""

from .repos import RepoManager
from .issues import IssueManager
from .actions import ActionsManager
from .code_review import CodeReviewManager

__all__ = [
    "RepoManager",
    "IssueManager",
    "ActionsManager",
    "CodeReviewManager",
]

__version__ = "1.0.0"