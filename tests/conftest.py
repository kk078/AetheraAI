"""
AetheraAI — Shared test fixtures and configuration.
Phase 14: Comprehensive Tests
"""
import asyncio
import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

fake = Faker()
Faker.seed(42)


# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Mock redis.asyncio.Redis for cascade and memory tests."""
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=0)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.pipeline = MagicMock(return_value=redis_mock)
    redis_mock.execute = AsyncMock(return_value=[])
    redis_mock.close = AsyncMock()
    redis_mock.aclose = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for connector tests."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={"results": []})
    response.raise_for_status = MagicMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def fake_value():
    """Seeded Faker instance for reproducible test data."""
    return fake


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_routing_config(tmp_path):
    """Minimal YAML config for AetheraRouter with specialist definitions."""
    config_content = """
specialists:
  healthcare_provider:
    enabled: true
    description: "Healthcare Provider Operations"
    color: "#06B6D4"
    default_model: aethera-cloud-brain
    keywords:
      - coding
      - billing
      - claim
      - reimbursement
      - denial
      - CPT
      - ICD
    tools:
      - code_lookup
      - cci_editor
      - fee_schedule
    priority: 1
  healthcare_payer:
    enabled: true
    description: "Healthcare Payer Operations"
    color: "#8B5CF6"
    default_model: aethera-cloud-brain
    keywords:
      - adjudication
      - risk adjustment
      - HCC
      - payment
      - coverage
    tools:
      - coverage_checker
    priority: 2
  healthcare_regulatory:
    enabled: true
    description: "Healthcare Regulatory Compliance"
    color: "#F43F5E"
    default_model: aethera-cloud-brain
    keywords:
      - HIPAA
      - compliance
      - Stark
      - Anti-Kickback
      - regulation
    tools:
      - compliance_checker
    priority: 3
  general:
    enabled: true
    description: "General Assistant"
    color: "#6B7280"
    default_model: aethera-cloud-balanced
    keywords: []
    tools: []
    priority: 10
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(config_content)
    return str(config_file)


@pytest.fixture
def sample_icd10_codes():
    """Valid ICD-10-CM codes for healthcare tool tests."""
    return {
        "E11.9": {"type": "icd10cm", "description": "Type 2 diabetes mellitus without complications"},
        "M54.5": {"type": "icd10cm", "description": "Low back pain"},
        "I10": {"type": "icd10cm", "description": "Essential hypertension"},
        "J06.9": {"type": "icd10cm", "description": "Acute upper respiratory infection, unspecified"},
        "S72.001A": {"type": "icd10cm", "description": "Fracture of unspecified part of neck of right femur, initial encounter"},
        "Z87.891": {"type": "icd10cm", "description": "Personal history of asbestos exposure"},
    }


@pytest.fixture
def sample_cpt_codes():
    """Valid CPT codes for healthcare tool tests."""
    return {
        "99213": {"description": "Office visit, established patient, low complexity"},
        "99214": {"description": "Office visit, established patient, moderate complexity"},
        "97110": {"description": "Therapeutic exercises"},
        "97140": {"description": "Manual therapy techniques"},
        "71045": {"description": "Chest X-ray, 1 view"},
        "85025": {"description": "Blood count, complete"},
        "93306": {"description": "Echocardiography, transthoracic, with Doppler"},
    }


@pytest.fixture
def sample_edi_837():
    """Valid 837P EDI X12 string for parser tests."""
    return (
        "ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     "
        "*240101*1200*^*00501*000000001*0*P*:~"
        "GS*HC*SENDERID*RECEIVERID*20240101*1200*1*X*005010X222~"
        "ST*837*0001*005010X222~"
        "BHT*0019*00*521541*20240101*1200*CH~"
        "NM1*41*2*CLINIC*****46*1234567890~"
        "NM1*40*2*INSURANCE CO*****46*9876543210~"
        "NM1*85*2*DR SMITH*****XX*1234567890~"
        "NM1*82*2*JOHN DOE*****MI*MEMBER001~"
        "CLM*CLAIM001*150.00***11:B:1*Y*A*Y*I*P~"
        "SV1*HC:99213***1***1~"
        "SE*12*0001~"
        "GE*1*1~"
        "IEA*1*000000001~"
    )


@pytest.fixture
def sample_edi_835():
    """Valid 835 EDI X12 string for parser tests."""
    return (
        "ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     "
        "*240101*1200*^*00501*000000002*0*P*:~"
        "GS*HC*SENDERID*RECEIVERID*20240101*1200*2*X*005010X221~"
        "ST*835*0002*005010X221~"
        "BPR*I*150.00*C*CHK*20240115*1*999999999*DA*12345*9876543210~"
        "TRN*1*1*1234567890~"
        "NM1*PR*2*INSURANCE CO*****46*9876543210~"
        "NM1*PE*2*DR SMITH*****XX*1234567890~"
        "CLP*CLAIM001*1*150.00*120.00*30.00*HC*20240101*1~"
        "SVC*HC:99213***1***1~"
        "CAS*PR*1*30.00~"
        "SE*11*0002~"
        "GE*2*2~"
        "IEA*1*000000002~"
    )


@pytest.fixture
def sample_edi_270():
    """Valid 270 EDI X12 string for parser tests."""
    return (
        "ISA*00*          *00*          *ZZ*SENDERID       *ZZ*RECEIVERID     "
        "*240101*1200*^*00501*000000003*0*P*:~"
        "GS*HS*SENDERID*RECEIVERID*20240101*1200*3*X*005010X279~"
        "ST*270*0003*005010X279~"
        "BHT*0022*13*1000*20240101*1200~"
        "HL*1**20*1~"
        "NM1*PR*2*INSURANCE CO*****46*9876543210~"
        "NM1*1P*2*DR SMITH*****XX*1234567890~"
        "NM1*IL*1*DOE*JOHN****MI*MEMBER001~"
        "SE*8*0003~"
        "GE*3*3~"
        "IEA*1*000000003~"
    )


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary SQLite database path for memory/store tests."""
    return str(tmp_path / "test_aethera.db")


@pytest.fixture
def mock_memory_subsystems():
    """Mock all MemoryManager subsystems for unit testing."""
    fact_store = MagicMock()
    fact_store.search_facts = AsyncMock(return_value=[])
    fact_store.store_fact = AsyncMock(return_value=True)

    learning_store = MagicMock()
    learning_store.get_preferences = AsyncMock(return_value={})
    learning_store.record_interaction = AsyncMock()
    learning_store.predict_next_action = AsyncMock(return_value=None)

    health_records = MagicMock()
    health_records.search = AsyncMock(return_value=[])
    health_records.export_deidentified = AsyncMock(return_value=[])

    vector_store = MagicMock()
    vector_store.search = AsyncMock(return_value=[])

    knowledge_gaps = MagicMock()
    knowledge_gaps.auto_detect_from_query = AsyncMock(return_value=[])
    knowledge_gaps.list_gaps = AsyncMock(return_value=[])

    user_profile = MagicMock()
    user_profile.get_preference = MagicMock(return_value=None)

    audit_db = MagicMock()
    audit_db.log = AsyncMock()

    return {
        "fact_store": fact_store,
        "learning_store": learning_store,
        "health_records": health_records,
        "vector_store": vector_store,
        "knowledge_gaps": knowledge_gaps,
        "user_profile": user_profile,
        "audit_db": audit_db,
    }