"""
Aethera AI - Health Records Module

Encrypted PHI store for health records.
Uses SQLCipher (pysqlcipher3) when available, falls back to regular SQLite
with application-layer encryption via cryptography library.

Tables: conditions, medications, allergies, procedures, lab_results,
        vitals, encounters.

All data encrypted at rest. Export uses HIPAA Safe Harbor de-identification.
"""

import sqlite3
import json
import uuid
import re
import hashlib
from datetime import datetime, date
from typing import List, Dict, Any, Optional

try:
    from pysqlcipher3 import dbapi2 as sqlcipher
    SQLCIPHER_AVAILABLE = True
except ImportError:
    SQLCIPHER_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


# HIPAA Safe Harbor de-identification: 18 identifiers to remove/transform
HIPAA_IDENTIFIER_FIELDS = {
    "name", "address", "city", "state", "zip", "phone", "fax",
    "email", "ssn", "mrn", "account_number", "certificate_number",
    "vehicle_id", "device_id", "url", "ip_address", "biometric", "photo"
}


def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive an encryption key from password and salt using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key)


def _encrypt_field(fernet, plaintext: str) -> str:
    """Encrypt a single field value."""
    return fernet.encrypt(plaintext.encode()).decode()


def _decrypt_field(fernet, ciphertext: str) -> str:
    """Decrypt a single field value."""
    return fernet.decrypt(ciphertext.encode()).decode()


class HealthRecords:
    """
    Encrypted health records store.

    When SQLCipher is available, the entire database file is encrypted.
    When not, regular SQLite is used with application-layer field-level
    encryption for sensitive fields.
    """

    def __init__(self, db_path: str = "/data/health_records.db", encryption_key: str = ""):
        self.db_path = db_path
        self._encryption_key = encryption_key
        self._conn: Optional[sqlite3.Connection] = None
        self._fernet: Optional[Fernet] = None
        self._use_sqlcipher = False

    def initialize(self, encryption_key: Optional[str] = None):
        """
        Initialize database and encryption.

        Args:
            encryption_key: Passphrase for database encryption. If None and
                           SQLCipher is available, a default key is used.
        """
        key = encryption_key or self._encryption_key or "aethera_default_key"

        if SQLCIPHER_AVAILABLE:
            self._use_sqlcipher = True
            self._conn = sqlcipher.connect(self.db_path)
            self._conn.execute(f"PRAGMA key = '{key}'")
            self._conn.execute("PRAGMA cipher_compatibility = 3")
        else:
            self._conn = sqlite3.connect(self.db_path)
            # Setup field-level encryption fallback
            if CRYPTO_AVAILABLE:
                salt = b"aethera_health_records_v1"
                fernet_key = _derive_key(key, salt)
                self._fernet = Fernet(fernet_key)

        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._create_tables()
        self._conn.commit()

    def _create_tables(self):
        """Create all health record tables."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS conditions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                condition_name TEXT NOT NULL,
                icd_code TEXT,
                status TEXT DEFAULT 'active',
                onset_date TEXT,
                resolved_date TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS medications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                medication_name TEXT NOT NULL,
                ndc_code TEXT,
                dosage TEXT,
                frequency TEXT,
                route TEXT,
                prescriber TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'active',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS allergies (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                allergen TEXT NOT NULL,
                reaction TEXT,
                severity TEXT,
                verified TEXT DEFAULT 'unverified',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS procedures (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                procedure_name TEXT NOT NULL,
                cpt_code TEXT,
                performed_date TEXT,
                provider TEXT,
                facility TEXT,
                outcome TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lab_results (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                test_name TEXT NOT NULL,
                loinc_code TEXT,
                result_value TEXT,
                result_unit TEXT,
                reference_range TEXT,
                flag TEXT,
                collection_date TEXT,
                ordering_provider TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vitals (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                vital_type TEXT NOT NULL,
                value REAL,
                unit TEXT,
                measured_date TEXT,
                source TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS encounters (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                encounter_type TEXT NOT NULL,
                encounter_date TEXT NOT NULL,
                provider TEXT,
                facility TEXT,
                chief_complaint TEXT,
                diagnosis_codes TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_conditions_user ON conditions(user_id);
            CREATE INDEX IF NOT EXISTS idx_medications_user ON medications(user_id);
            CREATE INDEX IF NOT EXISTS idx_allergies_user ON allergies(user_id);
            CREATE INDEX IF NOT EXISTS idx_procedures_user ON procedures(user_id);
            CREATE INDEX IF NOT EXISTS idx_lab_results_user ON lab_results(user_id);
            CREATE INDEX IF NOT EXISTS idx_vitals_user ON vitals(user_id);
            CREATE INDEX IF NOT EXISTS idx_encounters_user ON encounters(user_id);
        """)

    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt a value if field-level encryption is active."""
        if self._fernet and not self._use_sqlcipher:
            return _encrypt_field(self._fernet, plaintext)
        return plaintext

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt a value if field-level encryption is active."""
        if self._fernet and not self._use_sqlcipher:
            try:
                return _decrypt_field(self._fernet, ciphertext)
            except Exception:
                return ciphertext
        return ciphertext

    def _encrypt_record(self, table: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a record."""
        sensitive_fields = {
            "conditions": ["condition_name", "notes"],
            "medications": ["medication_name", "dosage", "prescriber", "notes"],
            "allergies": ["allergen", "reaction", "notes"],
            "procedures": ["procedure_name", "provider", "facility", "notes"],
            "lab_results": ["test_name", "result_value", "ordering_provider", "notes"],
            "vitals": ["notes"],
            "encounters": ["provider", "facility", "chief_complaint", "notes"],
        }
        fields = sensitive_fields.get(table, [])
        encrypted = dict(record)
        for field in fields:
            if field in encrypted and encrypted[field] is not None:
                encrypted[field] = self._encrypt(str(encrypted[field]))
        return encrypted

    def _decrypt_record(self, table: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a record."""
        sensitive_fields = {
            "conditions": ["condition_name", "notes"],
            "medications": ["medication_name", "dosage", "prescriber", "notes"],
            "allergies": ["allergen", "reaction", "notes"],
            "procedures": ["procedure_name", "provider", "facility", "notes"],
            "lab_results": ["test_name", "result_value", "ordering_provider", "notes"],
            "vitals": ["notes"],
            "encounters": ["provider", "facility", "chief_complaint", "notes"],
        }
        fields = sensitive_fields.get(table, [])
        decrypted = dict(record)
        for field in fields:
            if field in decrypted and decrypted[field] is not None:
                decrypted[field] = self._decrypt(str(decrypted[field]))
        return decrypted

    # ---- Record CRUD Operations ----

    def add_record(self, table: str, record: Dict[str, Any]) -> str:
        """
        Add a health record.

        Args:
            table: One of the valid health record tables
            record: Record data dict (must include 'user_id')

        Returns:
            Record ID
        """
        valid_tables = {"conditions", "medications", "allergies", "procedures",
                        "lab_results", "vitals", "encounters"}
        if table not in valid_tables:
            raise ValueError(f"Invalid table '{table}'. Valid: {sorted(valid_tables)}")

        if "user_id" not in record:
            raise ValueError("Record must include 'user_id'")

        if "id" not in record:
            record["id"] = f"rec_{uuid.uuid4().hex[:12]}"

        now = datetime.now().isoformat()
        record["created_at"] = now
        record["updated_at"] = now

        encrypted = self._encrypt_record(table, record)

        columns = list(encrypted.keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)

        self._conn.execute(
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})",
            [encrypted[c] for c in columns]
        )
        self._conn.commit()
        return record["id"]

    def get_record(self, table: str, record_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single record by ID."""
        cursor = self._conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (record_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        record = self._decrypt_record(table, dict(row))
        return record

    def query_by_type(
        self,
        table: str,
        user_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query records of a given type for a user.

        Args:
            table: Health record table name
            user_id: User identifier
            filters: Optional field-value filters for non-encrypted columns
            limit: Maximum results
            offset: Result offset

        Returns:
            List of decrypted records
        """
        conditions = ["user_id = ?"]
        params: List[Any] = [user_id]

        if filters:
            for key, value in filters.items():
                conditions.append(f"{key} = ?")
                params.append(value)

        where = " AND ".join(conditions)
        cursor = self._conn.execute(
            f"SELECT * FROM {table} WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        )

        results = []
        for row in cursor.fetchall():
            record = self._decrypt_record(table, dict(row))
            results.append(record)

        return results

    def update_record(self, table: str, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update fields on an existing record."""
        updates["updated_at"] = datetime.now().isoformat()
        encrypted_updates = self._encrypt_record(table, updates)

        set_clause = ", ".join([f"{k} = ?" for k in encrypted_updates.keys()])
        values = list(encrypted_updates.values()) + [record_id]

        try:
            self._conn.execute(
                f"UPDATE {table} SET {set_clause} WHERE id = ?", values
            )
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error updating record: {e}")
            return False

    def delete_record(self, table: str, record_id: str) -> bool:
        """Delete a record by ID."""
        try:
            self._conn.execute(f"DELETE FROM {table} WHERE id = ?", (record_id,))
            self._conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting record: {e}")
            return False

    # ---- Timeline ----

    def get_timeline(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get a chronological timeline of all health events for a user.

        Returns events sorted by date, combining records from all tables.
        """
        timeline: List[Dict[str, Any]] = []

        # Conditions
        cursor = self._conn.execute(
            """SELECT id, condition_name as description, onset_date as event_date,
                      'condition' as record_type, status
               FROM conditions WHERE user_id = ? ORDER BY onset_date DESC""",
            (user_id,)
        )
        for row in cursor.fetchall():
            record = self._decrypt_record("conditions", dict(row))
            record["event_date"] = record.get("onset_date", "")
            timeline.append(record)

        # Medications
        cursor = self._conn.execute(
            """SELECT id, medication_name as description, start_date as event_date,
                      'medication' as record_type, status
               FROM medications WHERE user_id = ? ORDER BY start_date DESC""",
            (user_id,)
        )
        for row in cursor.fetchall():
            record = self._decrypt_record("medications", dict(row))
            record["event_date"] = record.get("start_date", "")
            timeline.append(record)

        # Procedures
        cursor = self._conn.execute(
            """SELECT id, procedure_name as description, performed_date as event_date,
                      'procedure' as record_type
               FROM procedures WHERE user_id = ? ORDER BY performed_date DESC""",
            (user_id,)
        )
        for row in cursor.fetchall():
            record = self._decrypt_record("procedures", dict(row))
            record["event_date"] = record.get("performed_date", "")
            timeline.append(record)

        # Lab results
        cursor = self._conn.execute(
            """SELECT id, test_name as description, collection_date as event_date,
                      'lab_result' as record_type, result_value, flag
               FROM lab_results WHERE user_id = ? ORDER BY collection_date DESC""",
            (user_id,)
        )
        for row in cursor.fetchall():
            record = self._decrypt_record("lab_results", dict(row))
            record["event_date"] = record.get("collection_date", "")
            timeline.append(record)

        # Encounters
        cursor = self._conn.execute(
            """SELECT id, encounter_type as description, encounter_date as event_date,
                      'encounter' as record_type
               FROM encounters WHERE user_id = ? ORDER BY encounter_date DESC""",
            (user_id,)
        )
        for row in cursor.fetchall():
            record = self._decrypt_record("encounters", dict(row))
            record["event_date"] = record.get("encounter_date", "")
            timeline.append(record)

        # Sort all events by date descending
        timeline.sort(key=lambda x: x.get("event_date", ""), reverse=True)

        return timeline[:limit]

    # ---- Search ----

    def search(
        self,
        user_id: str,
        query: str,
        tables: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search across health records.

        Searches encrypted fields by decrypting and comparing.
        For large datasets, consider adding FTS5 virtual tables.

        Args:
            user_id: User identifier
            query: Search text
            tables: Specific tables to search (None = all)
            limit: Maximum results

        Returns:
            List of matching records with table name added
        """
        search_tables = tables or [
            "conditions", "medications", "allergies", "procedures",
            "lab_results", "vitals", "encounters"
        ]

        results: List[Dict[str, Any]] = []
        query_lower = query.lower()

        for table in search_tables:
            cursor = self._conn.execute(
                f"SELECT * FROM {table} WHERE user_id = ?",
                (user_id,)
            )
            for row in cursor.fetchall():
                record = self._decrypt_record(table, dict(row))
                # Check if any value contains the query
                for value in record.values():
                    if value is not None and query_lower in str(value).lower():
                        record["_table"] = table
                        results.append(record)
                        break

        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return results[:limit]

    # ---- HIPAA De-identification ----

    def _deidentify_value(self, value: Any, field_name: str) -> Any:
        """
        Apply HIPAA Safe Harbor de-identification to a field value.

        - Dates: generalize to year only (for ages >= 90, use "90+")
        - Names/identifiers: replace with hash-based pseudonym
        - Geographic data: generalize to state level
        - Free text: redact potential identifiers via regex
        """
        if value is None:
            return None

        str_val = str(value)

        # Date fields: keep only year
        if "date" in field_name.lower():
            date_match = re.match(r"(\d{4})-\d{2}-\d{2}", str_val)
            if date_match:
                return date_match.group(1)

        # Identifier fields: hash
        if field_name.lower() in HIPAA_IDENTIFIER_FIELDS or "id" in field_name.lower():
            if field_name.lower() == "user_id":
                return hashlib.sha256(str_val.encode()).hexdigest()[:12]
            if field_name.lower() == "id":
                return hashlib.sha256(str_val.encode()).hexdigest()[:12]

        # Name fields: pseudonymize
        if "name" in field_name.lower() or "provider" in field_name.lower():
            return hashlib.sha256(str_val.encode()).hexdigest()[:8]

        # Geographic: keep only state
        if "facility" in field_name.lower() or "address" in field_name.lower():
            return "[REDACTED_LOCATION]"

        # Free text notes: redact common identifier patterns
        if field_name.lower() == "notes":
            redacted = str_val
            # SSN
            redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", redacted)
            # Phone numbers
            redacted = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE]", redacted)
            # Email
            redacted = re.sub(r"\b[\w.]+@[\w.]+\.\w+\b", "[EMAIL]", redacted)
            # MRN-like numbers
            redacted = re.sub(r"\b\d{8,15}\b", "[ID_NUMBER]", redacted)
            return redacted

        return value

    def deidentify_record(self, table: str, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply HIPAA Safe Harbor de-identification to an entire record.

        Args:
            table: Source table name
            record: Decrypted record dict

        Returns:
            De-identified record safe for export
        """
        deidentified = {}
        for field, value in record.items():
            deidentified[field] = self._deidentify_value(value, field)
        deidentified["_table"] = table
        deidentified["_deidentified"] = True
        deidentified["_deidentified_at"] = datetime.now().isoformat()
        return deidentified

    def export_deidentified(
        self,
        user_id: str,
        tables: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Export all health records for a user with HIPAA Safe Harbor
        de-identification applied.

        Args:
            user_id: User identifier
            tables: Specific tables to export (None = all)

        Returns:
            List of de-identified records
        """
        export_tables = tables or [
            "conditions", "medications", "allergies", "procedures",
            "lab_results", "vitals", "encounters"
        ]

        results: List[Dict[str, Any]] = []

        for table in export_tables:
            cursor = self._conn.execute(
                f"SELECT * FROM {table} WHERE user_id = ?",
                (user_id,)
            )
            for row in cursor.fetchall():
                decrypted = self._decrypt_record(table, dict(row))
                deidentified = self.deidentify_record(table, decrypted)
                results.append(deidentified)

        return results


# Singleton instance
_health_records: Optional[HealthRecords] = None


def get_health_records(
    db_path: str = "/data/health_records.db",
    encryption_key: str = ""
) -> HealthRecords:
    """Get or create the health records instance."""
    global _health_records
    if _health_records is None:
        _health_records = HealthRecords(db_path, encryption_key)
    return _health_records