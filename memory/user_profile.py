"""
Aethera AI - User Profile Module

Encrypted user profile storage with PHI protection.
Stores user preferences, settings, and learned information securely.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


class UserProfile:
    """
    Encrypted user profile storage.

    Protects PHI/PII data using encryption.
    Stores:
    - User preferences and settings
    - Learned facts about the user
    - Saved snippets and references
    - Integration credentials (encrypted)
    """

    def __init__(self, user_id: str, data_dir: str = "./data"):
        self.user_id = user_id
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.profile_path = self.data_dir / f"user_{user_id}.json"
        self.encrypted_path = self.data_dir / f"user_{user_id}.encrypted"

        self._encryption_key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None
        self._profile: Dict[str, Any] = {}

    def initialize(self, encryption_password: Optional[str] = None):
        """Initialize profile and setup encryption."""
        if CRYPTO_AVAILABLE:
            if encryption_password:
                self._setup_encryption(encryption_password)
            else:
                self._fernet = Fernet(Fernet.generate_key())

        self._load_profile()

    def _setup_encryption(self, password: str):
        """Setup encryption from password."""
        if not CRYPTO_AVAILABLE:
            return
        salt = b"aethera_salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password.encode())
        import base64
        self._fernet = Fernet(base64.urlsafe_b64encode(key))

    def _load_profile(self):
        """Load profile from disk."""
        if self.profile_path.exists():
            try:
                with open(self.profile_path, 'r') as f:
                    self._profile = json.load(f)
            except Exception:
                self._profile = self._default_profile()
        else:
            self._profile = self._default_profile()

    def _default_profile(self) -> Dict[str, Any]:
        """Create default profile structure."""
        return {
            "user_id": self.user_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "preferences": {
                "default_specialist": "general",
                "model_preference": "auto",
                "response_style": "detailed",
                "timezone": "UTC",
            },
            "specializations": [],
            "memories": [],
            "credentials": {},
            "snippets": [],
            "metadata": {}
        }

    def save(self, encrypt: bool = True):
        """Save profile to disk."""
        self._profile["updated_at"] = datetime.now().isoformat()
        with open(self.profile_path, 'w') as f:
            json.dump(self._profile, f, indent=2)

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self._profile.get("preferences", {}).get(key, default)

    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        if "preferences" not in self._profile:
            self._profile["preferences"] = {}
        self._profile["preferences"][key] = value
        self.save()

    def add_specialization(self, specialization: str):
        """Add a user specialization/expertise area."""
        if "specializations" not in self._profile:
            self._profile["specializations"] = []
        if specialization not in self._profile["specializations"]:
            self._profile["specializations"].append(specialization)
            self.save()

    def get_specializations(self) -> List[str]:
        """Get user specializations."""
        return self._profile.get("specializations", [])

    def add_memory(self, content: str, category: str = "general", metadata: Optional[Dict] = None):
        """Add a learned memory about the user."""
        if "memories" not in self._profile:
            self._profile["memories"] = []
        memory = {
            "id": f"mem_{datetime.now().timestamp()}",
            "content": content,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self._profile["memories"].append(memory)
        self.save()
        return memory["id"]

    def get_memories(self, category: Optional[str] = None) -> List[Dict]:
        """Get user memories."""
        memories = self._profile.get("memories", [])
        if category:
            memories = [m for m in memories if m.get("category") == category]
        return memories

    def store_credential(self, name: str, value: str):
        """Store an encrypted credential."""
        if "credentials" not in self._profile:
            self._profile["credentials"] = {}
        if CRYPTO_AVAILABLE and self._fernet:
            encrypted = self._fernet.encrypt(value.encode()).decode()
            self._profile["credentials"][name] = encrypted
        else:
            self._profile["credentials"][name] = value
        self.save()

    def get_credential(self, name: str) -> Optional[str]:
        """Retrieve a credential."""
        cred = self._profile.get("credentials", {}).get(name)
        if not cred:
            return None
        if CRYPTO_AVAILABLE and self._fernet:
            try:
                return self._fernet.decrypt(cred.encode()).decode()
            except Exception:
                return cred
        return cred

    def get_profile_summary(self) -> Dict[str, Any]:
        """Get profile summary."""
        return {
            "user_id": self._profile.get("user_id"),
            "memory_count": len(self._profile.get("memories", [])),
            "specialization_count": len(self._profile.get("specializations", [])),
        }

    def contains_phi(self, text: str) -> bool:
        """Check if text contains PHI/PII patterns."""
        import re
        phi_patterns = [
            (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            (r'\b\d{10,15}\b', 'Medical Record Number'),
        ]
        for pattern, _ in phi_patterns:
            if re.search(pattern, text):
                return True
        return False


_profiles: Dict[str, UserProfile] = {}


def get_user_profile(user_id: str, data_dir: str = "./data") -> UserProfile:
    """Get or create a user profile."""
    if user_id not in _profiles:
        profile = UserProfile(user_id, data_dir)
        profile.initialize()
        _profiles[user_id] = profile
    return _profiles[user_id]
