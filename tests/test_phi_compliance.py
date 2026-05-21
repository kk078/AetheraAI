"""
Tests for the PHI/HIPAA code-level controls:
- orchestrator/phi_logging.py  (redact PHI/PII from logs)
- orchestrator/phi_guard.py     (pin PHI-tainted conversations to local models)
- infrastructure/backup.py      (encrypted backups, fail-closed)
"""

import logging

import pytest

from orchestrator.phi_logging import PHIRedactionFilter, install_phi_log_redaction
from orchestrator.phi_guard import ConversationSensitivityTracker, apply_taint
from infrastructure.backup import BackupManager, ENCRYPTED_SUFFIX


def _crypto_works() -> bool:
    """True only if cryptography's native backend actually runs (not just imports)."""
    try:
        from cryptography.fernet import Fernet
        Fernet(Fernet.generate_key()).encrypt(b"x")
        return True
    except BaseException:
        # pyo3 raises BaseException-derived PanicException when the native
        # backend is broken (e.g. missing _cffi_backend in this sandbox).
        return False


requires_crypto = pytest.mark.skipif(
    not _crypto_works(),
    reason="cryptography native backend unavailable in this environment",
)


# ---------------------------------------------------------------------------
# PHI log redaction
# ---------------------------------------------------------------------------

def _record(msg, args=()):
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )


def test_redacts_ssn_and_email_in_message():
    f = PHIRedactionFilter()
    rec = _record("patient SSN 123-45-6789 email john@example.com")
    f.filter(rec)
    out = rec.getMessage()
    assert "123-45-6789" not in out
    assert "john@example.com" not in out
    assert "[REDACTED]" in out


def test_redacts_phi_in_format_args():
    f = PHIRedactionFilter()
    rec = _record("contact for %s is %s", ("patient", "555-44-3333"))
    f.filter(rec)
    out = rec.getMessage()
    assert "555-44-3333" not in out


def test_clean_message_untouched():
    f = PHIRedactionFilter()
    rec = _record("routing query to healthcare_provider specialist")
    f.filter(rec)
    assert rec.getMessage() == "routing query to healthcare_provider specialist"


def test_install_is_idempotent():
    name = "aethera.test.redaction"
    lg = logging.getLogger(name)
    install_phi_log_redaction(name)
    install_phi_log_redaction(name)
    count = sum(isinstance(flt, PHIRedactionFilter) for flt in lg.filters)
    assert count == 1


# ---------------------------------------------------------------------------
# Conversation PHI taint
# ---------------------------------------------------------------------------

@pytest.fixture
def tracker(tmp_path):
    t = ConversationSensitivityTracker(db_path=str(tmp_path / "taint.db"))
    yield t
    t.close()


def test_clean_conversation_stays_clean(tracker):
    phi, pii = apply_taint(tracker, "conv-1", contains_phi=False, contains_pii=False)
    assert phi is False and pii is False
    assert tracker.is_tainted("conv-1") is False


def test_phi_turn_taints_conversation(tracker):
    phi, pii = apply_taint(tracker, "conv-2", contains_phi=True, contains_pii=False)
    assert phi is True
    assert tracker.is_tainted("conv-2") is True


def test_clean_followup_stays_pinned_after_phi(tracker):
    apply_taint(tracker, "conv-3", contains_phi=True, contains_pii=False)
    # A later, clean-looking message in the same conversation must still pin local.
    phi, pii = apply_taint(tracker, "conv-3", contains_phi=False, contains_pii=False)
    assert phi is True


def test_taint_persists_across_instances(tmp_path):
    path = str(tmp_path / "taint.db")
    t1 = ConversationSensitivityTracker(db_path=path)
    t1.mark_tainted("conv-x")
    t1.close()
    t2 = ConversationSensitivityTracker(db_path=path)
    assert t2.is_tainted("conv-x") is True
    t2.close()


def test_empty_conversation_id_is_safe(tracker):
    phi, pii = apply_taint(tracker, None, contains_phi=True, contains_pii=True)
    # Marking a None id is a no-op; flags still reflect the current turn.
    assert phi is True and pii is True
    assert tracker.is_tainted(None) is False


# ---------------------------------------------------------------------------
# Encrypted backups
# ---------------------------------------------------------------------------

def _make_data_dir(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "aethera.db").write_bytes(b"SENSITIVE PHI CONTENT")
    return data


@requires_crypto
def test_backup_encrypted_when_key_set(tmp_path):
    data = _make_data_dir(tmp_path)
    mgr = BackupManager(
        backup_dir=str(tmp_path / "backups"),
        data_dir=str(data),
        encryption_key="correct horse battery staple",
    )
    assert mgr.encryption_enabled is True
    path = mgr.create_backup("b1")
    assert path.endswith(ENCRYPTED_SUFFIX)
    # The plaintext tarball must not be left behind.
    assert not (tmp_path / "backups" / "b1.tar.gz").exists()
    # Ciphertext must not contain the plaintext PHI.
    assert b"SENSITIVE PHI CONTENT" not in (tmp_path / "backups" / f"b1{ENCRYPTED_SUFFIX}").read_bytes()

    listing = mgr.list_backups()
    assert listing and listing[0]["encrypted"] is True


@requires_crypto
def test_backup_roundtrip_restore(tmp_path):
    data = _make_data_dir(tmp_path)
    mgr = BackupManager(
        backup_dir=str(tmp_path / "backups"),
        data_dir=str(data),
        encryption_key="a-strong-passphrase",
    )
    path = mgr.create_backup("b1")

    restore_dir = tmp_path / "restored"
    restorer = BackupManager(
        backup_dir=str(tmp_path / "backups"),
        data_dir=str(restore_dir),
        encryption_key="a-strong-passphrase",
    )
    assert restorer.restore_backup(path) is True
    assert (restore_dir / "aethera.db").read_bytes() == b"SENSITIVE PHI CONTENT"
    # No decrypted temp file left behind.
    assert not list((tmp_path / "backups").glob(".restore_*"))


@requires_crypto
def test_restore_fails_without_key(tmp_path):
    data = _make_data_dir(tmp_path)
    mgr = BackupManager(str(tmp_path / "backups"), str(data), encryption_key="k")
    path = mgr.create_backup("b1")
    no_key = BackupManager(str(tmp_path / "backups"), str(tmp_path / "out"))
    assert no_key.restore_backup(path) is False


def test_plaintext_backup_when_no_key(tmp_path):
    data = _make_data_dir(tmp_path)
    mgr = BackupManager(backup_dir=str(tmp_path / "backups"), data_dir=str(data))
    assert mgr.encryption_enabled is False
    path = mgr.create_backup("b1")
    assert path.endswith(".tar.gz") and not path.endswith(ENCRYPTED_SUFFIX)
