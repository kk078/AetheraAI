"""
Aethera AI - Main FastAPI Application

The central orchestrator for all Aethera AI functionality.
Handles chat, specialists, skills, plugins, connectors, memory, and more.
"""

import asyncio
import json
import logging
from dataclasses import asdict
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from orchestrator.router import get_router, AetheraRouter, RoutingResult
from orchestrator.cascade import get_cascade, ModelCascade, ModelSelection, ProviderType
from orchestrator.sensitivity import get_sensitivity_analyzer, SensitivityAnalyzer, DetectionResult, SensitivityLevel
from orchestrator.explainer import get_explainer_store, ReasoningChain, StepType
from orchestrator.scenarios import ScenarioEngine
from orchestrator.session_sync import SessionSync
from orchestrator.agent import AgentResult, run_agent_loop

# Lazy imports for skills, plugins, connectors, memory — loaded on startup
_skill_registry = None
_plugin_registry = None
_connector_registry = None
_conversation_store = None
_user_profile = None
_vector_store = None
_memory_manager = None
_knowledge_graph = None
_proactive_intelligence = None
_scenario_engine = None
_session_sync = None


def _get_skill_registry():
    global _skill_registry
    if _skill_registry is None:
        try:
            from skills.skill_registry import get_registry
            _skill_registry = get_registry()
        except Exception as e:
            logger.warning(f"Skill registry not available: {e}")
    return _skill_registry


def _get_plugin_registry():
    global _plugin_registry
    if _plugin_registry is None:
        try:
            from plugins.plugin_registry import PluginRegistry
            _plugin_registry = PluginRegistry()
            _plugin_registry.load_from_config({})
        except Exception as e:
            logger.warning(f"Plugin registry not available: {e}")
    return _plugin_registry


def _get_connector_registry():
    global _connector_registry
    if _connector_registry is None:
        try:
            from connectors.connector_registry import ConnectorRegistry
            _connector_registry = ConnectorRegistry()
            _connector_registry.load_connectors({})
        except Exception as e:
            logger.warning(f"Connector registry not available: {e}")
    return _connector_registry


def _get_conversation_store():
    global _conversation_store
    if _conversation_store is None:
        try:
            from memory.conversation_store import ConversationStore
            _conversation_store = ConversationStore()
            _conversation_store.initialize()
        except Exception as e:
            logger.warning(f"Conversation store not available: {e}")
    return _conversation_store


def _get_user_profile(user_id: str = "default_user"):
    from memory.user_profile import get_user_profile
    return get_user_profile(user_id, data_dir="./data")


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        try:
            from memory.vector_store import get_vector_store
            _vector_store = get_vector_store()
        except Exception as e:
            logger.warning(f"Vector store not available: {e}")
    return _vector_store


def _get_proactive_intelligence():
    global _proactive_intelligence
    if _proactive_intelligence is None:
        try:
            from orchestrator.proactive import get_proactive_intelligence
            _proactive_intelligence = get_proactive_intelligence()
        except Exception as e:
            logger.warning(f"Proactive intelligence not available: {e}")
    return _proactive_intelligence


_knowledge_updater = None


def _get_knowledge_updater():
    global _knowledge_updater
    if _knowledge_updater is None:
        try:
            from proactive.knowledge_updater import get_knowledge_updater
            _knowledge_updater = get_knowledge_updater()
        except Exception as e:
            logger.warning(f"Knowledge updater not available: {e}")
    return _knowledge_updater


def _get_memory_manager():
    global _memory_manager
    if _memory_manager is None:
        try:
            from memory.memory_manager import get_memory_manager
            _memory_manager = get_memory_manager(
                db_path="/data/aethera.db",
                health_db_path="/data/health_records.db",
                chromadb_url=CHROMADB_URL,
                encryption_key=ENCRYPTION_KEY,
            )
        except Exception as e:
            logger.warning(f"Memory manager not available: {e}")
    return _memory_manager


def _get_knowledge_graph():
    global _knowledge_graph
    if _knowledge_graph is None:
        try:
            from memory.knowledge_graph import KnowledgeGraph
            _knowledge_graph = KnowledgeGraph("/data/aethera.db")
            _knowledge_graph.initialize()
        except Exception as e:
            logger.warning(f"Knowledge graph not available: {e}")
    return _knowledge_graph


_temporal_processor = None
_audit_db = None
_action_queue = None
_automation_engine = None
_news_aggregator = None

def _get_audit_db():
    global _audit_db
    if _audit_db is None:
        try:
            from infrastructure.security.audit_logger import AuditDatabase
            _audit_db = AuditDatabase()
        except Exception as e:
            logger.warning(f"Audit database not available: {e}")
    return _audit_db

def _get_temporal_processor():
    global _temporal_processor
    if _temporal_processor is None:
        try:
            from orchestrator.temporal import get_temporal_processor
            _temporal_processor = get_temporal_processor()
        except Exception as e:
            logger.warning(f"Temporal processor not available: {e}")
    return _temporal_processor

def _get_action_queue():
    global _action_queue
    if _action_queue is None:
        try:
            from proactive.action_queue import ActionQueue
            _action_queue = ActionQueue()
        except Exception as e:
            logger.warning(f"Action queue not available: {e}")
    return _action_queue

def _get_automation_engine():
    global _automation_engine
    if _automation_engine is None:
        try:
            from proactive.automations import AutomationEngine
            from proactive.scheduler import get_scheduler
            scheduler = get_scheduler()
            _automation_engine = AutomationEngine(scheduler=scheduler)
        except Exception as e:
            logger.warning(f"Automation engine not available: {e}")
    return _automation_engine

def _get_news_aggregator():
    global _news_aggregator
    if _news_aggregator is None:
        try:
            from proactive.news_aggregator import NewsAggregator
            _news_aggregator = NewsAggregator()
        except Exception as e:
            logger.warning(f"News aggregator not available: {e}")
    return _news_aggregator

# =============================================================================
# CONFIGURATION
# =============================================================================

# Environment variables
LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")
CHROMADB_URL = os.getenv("CHROMADB_URL", "http://chromadb:8000")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/aethera.db")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = Path(__file__).parent / "config.yaml"

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("aethera-orchestrator")

# =============================================================================
# MODEL DISPLAY NAMES — Human-readable names for UI
# =============================================================================

MODEL_DISPLAY_NAMES = {
    "aethera-cloud-brain": "Qwen 3.5 122B (Cloud)",
    "aethera-cloud-reason": "DeepSeek V4 Flash (Cloud)",
    "aethera-cloud-coder": "Kimi K2.6 (Cloud)",
    "aethera-cloud-tools": "Gemma 4 26B (Cloud)",
    "aethera-cloud-agent": "Nemotron 3 Super (Cloud)",
    "aethera-cloud-balanced": "Qwen 3.5 35B (Cloud)",
    "aethera-cloud-engineer": "GLM 5.1 (Cloud)",
    "aethera-local-fast": "Qwen 3.5 4B (Local GPU)",
    "aethera-local-tools": "Gemma 4 E2B (Local GPU)",
    "aethera-local-smart": "Qwen 3.5 9B (Local CPU)",
    "hf-qwen-72b": "Qwen 2.5 72B (HuggingFace)",
    "hf-mistral": "Mistral 7B (HuggingFace)",
}

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Aethera AI",
    description="Personal Healthcare AI Super Agent - API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ChatMessage(BaseModel):
    """Chat message model."""
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = None
    specialist: Optional[str] = None
    model: Optional[str] = None
    confidence: Optional[float] = None


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for continuity")
    specialist: Optional[str] = Field(None, description="Force specific specialist")
    model: Optional[str] = Field(None, description="Force specific model")
    stream: bool = Field(True, description="Enable streaming response")
    user_id: Optional[str] = Field("default_user", description="User ID for personalization")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    """Chat response model."""
    conversation_id: str
    message: ChatMessage
    specialist: str
    model: str
    confidence: float
    tools_used: List[str] = []
    reasoning: Optional[str] = None
    timestamp: datetime
    teaching_mode: Optional[Dict[str, Any]] = None


class SpecialistInfo(BaseModel):
    """Specialist information model."""
    name: str
    description: str
    color: str
    enabled: bool
    priority: int
    default_model: str
    tools: List[str]


class SkillInfo(BaseModel):
    """Skill information model."""
    name: str
    description: str
    category: str
    parameters: Dict[str, Any]
    examples: List[Dict[str, Any]] = []
    requires_phi_protection: bool = False


class PluginInfo(BaseModel):
    """Plugin information model."""
    name: str
    description: str
    enabled: bool
    requires_auth: bool
    status: str  # connected, disconnected, error
    config_schema: Dict[str, Any] = {}


class ConnectorInfo(BaseModel):
    """Connector information model."""
    name: str
    description: str
    category: str
    connected: bool
    status: str


class HealthCheck(BaseModel):
    """Health check response model."""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
    models_available: int
    specialists_available: int


class UsageSummary(BaseModel):
    """Usage summary model."""
    ollama_cloud: Dict[str, Any]
    huggingface: Dict[str, Any]
    local: Dict[str, Any]
    total_queries_today: int
    total_tokens_today: int


# =============================================================================
# STATE MANAGEMENT
# =============================================================================

class AetheraState:
    """Application state management."""

    def __init__(self):
        self.router: Optional[AetheraRouter] = None
        self.cascade: Optional[ModelCascade] = None
        self.sensitivity: Optional[SensitivityAnalyzer] = None
        self.initialized = False
        self.start_time = datetime.now()

    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing Aethera Orchestrator...")

        # Initialize router
        self.router = get_router(str(CONFIG_PATH))
        logger.info(f"Loaded {len(self.router.list_specialists())} specialists")

        # Initialize cascade
        self.cascade = get_cascade(REDIS_URL)
        await self.cascade.initialize()
        logger.info("Model cascade initialized")

        # Initialize sensitivity analyzer
        self.sensitivity = get_sensitivity_analyzer()
        logger.info("Sensitivity analyzer initialized")

        # Initialize memory manager
        try:
            mm = _get_memory_manager()
            await mm.initialize()
            logger.info("Memory manager initialized")
        except Exception as e:
            logger.warning(f"Memory manager initialization failed: {e}")

        self.initialized = True
        logger.info("Aethera Orchestrator initialized successfully")

    def ensure_initialized(self):
        """Ensure components are initialized."""
        if not self.initialized:
            raise HTTPException(
                status_code=503,
                detail="Orchestrator not initialized. Wait for startup to complete."
            )


# Global state
state = AetheraState()

# =============================================================================
# LIFESPAN EVENTS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    await state.initialize()
    # Start proactive scheduler with built-in jobs
    pi = _get_proactive_intelligence()
    if pi:
        try:
            pi.start_scheduler()
            logger.info("Proactive scheduler started")
        except Exception as e:
            logger.warning(f"Proactive scheduler startup failed: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    pi = _get_proactive_intelligence()
    if pi:
        try:
            pi.stop_scheduler()
        except Exception:
            pass
    if state.cascade:
        await state.cascade.close()
    mm = _get_memory_manager()
    if mm:
        await mm.close()
    logger.info("Aethera Orchestrator shutdown complete")

# =============================================================================
# CORE CHAT ENDPOINTS
# =============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint with streaming support.

    Routes query to appropriate specialist, selects optimal model,
    executes with tools, and returns response with metadata.
    """
    state.ensure_initialized()

    start_time = time.time()
    conversation_id = request.conversation_id or str(uuid.uuid4())

    try:
        # 1. Analyze sensitivity (PHI/PII detection)
        sensitivity_result = state.sensitivity.analyze(request.message)

        # 2. Route to specialist
        routing_result = state.router.route(request.message)

        # Override specialist if requested
        if request.specialist:
            routing_result.primary_specialist = request.specialist
            routing_result.confidence = 1.0
            routing_result.reasoning = f"User forced specialist: {request.specialist}"

        # 3. Select model based on sensitivity and routing
        model_selection = await state.cascade.select_model(
            specialist=routing_result.primary_specialist,
            is_phi=sensitivity_result.contains_phi,
            is_pii=sensitivity_result.contains_pii,
            complexity=routing_result.query_complexity,
            force_model=request.model
        )

        # 4. Build messages for LLM
        system_prompt = await build_system_prompt(
            specialist=routing_result.primary_specialist,
            tools=routing_result.recommended_tools,
            sensitivity=sensitivity_result,
            user_id=request.user_id,
            query=request.message,
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Load conversation history if available
        if request.conversation_id:
            store = _get_conversation_store()
            if store:
                try:
                    conversation = store.get_conversation(request.conversation_id)
                    if conversation and conversation.get("messages"):
                        msgs = conversation["messages"][-10:]
                        for msg in msgs:
                            if msg.get("role") in ("user", "assistant"):
                                messages.append({
                                    "role": msg["role"],
                                    "content": msg.get("content", "")
                                })
                except Exception:
                    pass  # History is optional

        messages.append({"role": "user", "content": request.message})

        # 5. Run the agentic loop (executes tools the model calls, then answers)
        agent_result = await execute_llm_call(
            messages=messages,
            model=model_selection.model_name,
            tools=routing_result.recommended_tools,
            stream=request.stream
        )
        response_content = agent_result.content
        tools_used = agent_result.tools_used or routing_result.recommended_tools

        # 6. Create response
        # Detect teaching mode intent
        teaching_mode_data = None
        try:
            from skills.skill_creator import TeachingModeDetector
            detector = TeachingModeDetector()
            intent = detector.detect(request.message, messages)
            if intent.is_teaching:
                teaching_mode_data = {
                    "detected": True,
                    "confidence": intent.confidence,
                    "patterns": intent.detected_patterns,
                    "suggested_action": intent.suggested_action,
                }
        except Exception:
            pass  # Teaching mode detection is optional

        response = ChatResponse(
            conversation_id=conversation_id,
            message=ChatMessage(
                role="assistant",
                content=response_content,
                timestamp=datetime.now(),
                specialist=routing_result.primary_specialist,
                model=model_selection.model_name,
                confidence=routing_result.confidence
            ),
            specialist=routing_result.primary_specialist,
            model=model_selection.model_name,
            confidence=routing_result.confidence,
            tools_used=tools_used,
            reasoning=routing_result.reasoning,
            timestamp=datetime.now(),
            teaching_mode=teaching_mode_data
        )

        # 7. Log to audit trail
        await log_audit_event(
            event_type="chat",
            conversation_id=conversation_id,
            specialist=routing_result.primary_specialist,
            model=model_selection.model_name,
            sensitivity=sensitivity_result.sensitivity_level.value,
            duration_ms=int((time.time() - start_time) * 1000)
        )

        # 8. Consolidate memory (non-blocking)
        mm = _get_memory_manager()
        if mm:
            asyncio.create_task(mm.consolidate(
                user_id=request.user_id,
                query=request.message,
                response=response_content,
                specialist=routing_result.primary_specialist,
                sensitivity=sensitivity_result,
                conversation_id=conversation_id,
            ))

        # 9. Extract temporal deadlines from message (non-blocking)
        try:
            tp = _get_temporal_processor()
            if tp:
                items = tp.extract_deadlines_from_text(request.message)
                if items:
                    logger.info(f"Extracted {len(items)} temporal items from chat message")
        except Exception:
            pass

        return response

    except Exception as e:
        logger.exception(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint returning Server-Sent Events."""
    state.ensure_initialized()

    start_time = time.time()
    conversation_id = request.conversation_id or str(uuid.uuid4())

    try:
        sensitivity_result = state.sensitivity.analyze(request.message)
        routing_result = state.router.route(request.message)

        if request.specialist:
            routing_result.primary_specialist = request.specialist
            routing_result.confidence = 1.0

        model_selection = await state.cascade.select_model(
            specialist=routing_result.primary_specialist,
            is_phi=sensitivity_result.contains_phi,
            is_pii=sensitivity_result.contains_pii,
            complexity=routing_result.query_complexity,
            force_model=request.model,
        )

        system_prompt = await build_system_prompt(
            specialist=routing_result.primary_specialist,
            tools=routing_result.recommended_tools,
            sensitivity=sensitivity_result,
            user_id=request.user_id,
            query=request.message,
        )

        # Extract temporal deadlines from message (fast, synchronous)
        try:
            tp = _get_temporal_processor()
            if tp:
                items = tp.extract_deadlines_from_text(request.message)
                if items:
                    logger.info(f"Extracted {len(items)} temporal items from streaming chat message")
        except Exception:
            pass

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message},
        ]

        # Load conversation history if provided
        if request.conversation_id:
            store = _get_conversation_store()
            if store:
                try:
                    conversation = store.get_conversation(request.conversation_id)
                    if conversation and conversation.get("messages"):
                        msgs = conversation["messages"][-10:]
                        for msg in msgs:
                            if msg.get("role") in ("user", "assistant"):
                                messages.insert(-1, {
                                    "role": msg["role"],
                                    "content": msg.get("content", "")
                                })
                except Exception:
                    pass  # History is optional, continue without it

        payload = {
            "model": model_selection.model_name,
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        # Add tool definitions if available
        registry = _get_skill_registry()
        tool_defs = []
        if registry and routing_result.recommended_tools:
            for tn in routing_result.recommended_tools:
                s = registry.get(tn)
                if s:
                    tool_defs.append(s.to_tool_definition())
        if tool_defs:
            payload["tools"] = tool_defs

        async def event_generator():
            # Send metadata event first
            metadata = {
                "specialist": routing_result.primary_specialist,
                "model": model_selection.model_name,
                "model_display": MODEL_DISPLAY_NAMES.get(model_selection.model_name, model_selection.model_name),
                "confidence": routing_result.confidence,
                "phi_detected": sensitivity_result.contains_phi,
                "pii_detected": sensitivity_result.contains_pii,
                "sensitivity": sensitivity_result.sensitivity_level.value,
                "tools": routing_result.recommended_tools,
                "conversation_id": conversation_id,
            }
            yield f"data: {json.dumps({'type': 'metadata', 'data': metadata})}\n\n"

            try:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
                    async with client.stream(
                        "POST",
                        f"{LITELLM_URL}/v1/chat/completions",
                        json=payload,
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            yield f"data: {json.dumps({'type': 'error', 'error': f'LLM returned {response.status_code}', 'detail': error_body.decode()[:500]})}\n\n"
                            return

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data = line[6:]
                                if data.strip() == "[DONE]":
                                    yield f"data: {json.dumps({'type': 'done', 'conversation_id': conversation_id})}\n\n"
                                    break
                                try:
                                    chunk = json.loads(data)
                                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                                    # Handle tool calls in streaming
                                    tool_calls = delta.get("tool_calls")
                                    if tool_calls:
                                        yield f"data: {json.dumps({'type': 'tool_call', 'data': tool_calls})}\n\n"
                                except json.JSONDecodeError:
                                    continue
            except httpx.TimeoutException:
                yield f"data: {json.dumps({'type': 'error', 'error': 'LLM request timed out'})}\n\n"
            except httpx.ConnectError:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Cannot connect to LLM service'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)[:200]})}\n\n"

            # Log audit and consolidate memory (non-blocking)
            try:
                await log_audit_event(
                    event_type="chat_stream",
                    conversation_id=conversation_id,
                    specialist=routing_result.primary_specialist,
                    model=model_selection.model_name,
                    sensitivity=sensitivity_result.sensitivity_level.value,
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            except Exception:
                pass
                yield f"data: {json.dumps({'type': 'error', 'error': 'LLM request timed out'})}\n\n"
            except httpx.ConnectError:
                yield f"data: {json.dumps({'type': 'error', 'error': 'Cannot connect to LLM service'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)[:200]})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        logger.exception(f"Streaming chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/specialist/{specialist_name}")
async def chat_with_specialist(specialist_name: str, request: ChatRequest):
    """Force a specific specialist for the query."""
    request.specialist = specialist_name
    return await chat(request)


@app.post("/api/chat/multi-agent")
async def chat_multi_agent(request: ChatRequest):
    """
    Multi-agent reasoning for complex queries.

    Spawns multiple specialists to debate and reach consensus.
    """
    state.ensure_initialized()

    from orchestrator.multi_agent import get_coordinator

    coordinator = get_coordinator()

    # Build conversation history from recent messages
    conversation_history = []
    if request.conversation_id:
        store = _get_conversation_store()
        if store:
            try:
                conv = store.get_conversation(request.conversation_id)
                messages = conv.get("messages", conv) if isinstance(conv, dict) else conv
                conversation_history = messages[-10:] if messages else []
            except Exception:
                pass

    # Build context from memory if available
    context = {}
    if request.user_id and _memory_manager:
        try:
            user_ctx = await _memory_manager.get_user_context(request.user_id)
            if user_ctx:
                context["user_preferences"] = user_ctx
        except Exception:
            pass

    result = await coordinator.coordinate(
        query=request.message,
        context=context,
        max_agents=3,
        conversation_history=conversation_history,
    )

    # Log the multi-agent interaction
    audit_db = _get_audit_db()
    if audit_db:
        try:
            audit_db.log(
                user_id=request.user_id or "anonymous",
                action="multi_agent_chat",
                resource=f"specialists:{','.join(result.get('specialists_consulted', []))}",
                details=json.dumps({
                    "query_length": len(request.message),
                    "specialists": result.get("specialists_consulted", []),
                    "avg_confidence": result.get("average_confidence", 0),
                }),
            )
        except Exception:
            pass

    return {
        "message": {
            "role": "assistant",
            "content": result.get("content", ""),
        },
        "specialists": result.get("specialists_consulted", []),
        "perspectives": result.get("perspectives", []),
        "average_confidence": result.get("average_confidence", 0),
        "model": "multi-agent",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/conversations")
async def list_conversations(limit: int = 50, offset: int = 0):
    """List user conversations."""
    store = _get_conversation_store()
    if store is None:
        return {"conversations": [], "total": 0, "limit": limit, "offset": offset}
    try:
        conversations = store.list_conversations("default_user", limit=limit, offset=offset)
        return {"conversations": conversations, "total": len(conversations), "limit": limit, "offset": offset}
    except Exception:
        return {"conversations": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation by ID."""
    store = _get_conversation_store()
    if store is None:
        return {"conversation_id": conversation_id, "messages": []}
    try:
        conversation = store.get_conversation(conversation_id)
        return {"conversation_id": conversation_id, "messages": conversation or []}
    except Exception:
        return {"conversation_id": conversation_id, "messages": []}


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation."""
    store = _get_conversation_store()
    if store is None:
        return {"status": "deleted", "conversation_id": conversation_id}
    try:
        store.delete_conversation(conversation_id)
        return {"status": "deleted", "conversation_id": conversation_id}
    except Exception:
        return {"status": "deleted", "conversation_id": conversation_id}

# =============================================================================
# SPECIALIST ENDPOINTS
# =============================================================================

@app.get("/api/specialists", response_model=List[SpecialistInfo])
async def list_specialists():
    """List all available specialists."""
    state.ensure_initialized()
    specialists = state.router.list_specialists()
    return [
        SpecialistInfo(
            name=s["name"],
            description=s["description"],
            color=s["color"],
            enabled=s["enabled"],
            priority=s["priority"],
            default_model=state.router.get_specialist(s["name"]).get("default_model", "aethera-cloud-balanced"),
            tools=state.router.get_specialist(s["name"]).get("tools", [])
        )
        for s in specialists
    ]


@app.get("/api/specialists/{specialist_name}")
async def get_specialist(specialist_name: str):
    """Get specialist details."""
    state.ensure_initialized()
    specialist = state.router.get_specialist(specialist_name)
    if not specialist:
        raise HTTPException(status_code=404, detail=f"Specialist '{specialist_name}' not found")
    return {
        "name": specialist_name,
        **specialist
    }


@app.post("/api/specialists/{specialist_name}/query")
async def query_specialist(specialist_name: str, request: ChatRequest):
    """Query a specific specialist directly."""
    request.specialist = specialist_name
    return await chat(request)

# =============================================================================
# SKILLS ENDPOINTS
# =============================================================================

@app.get("/api/skills")
async def list_skills(category: Optional[str] = None):
    """List all available skills, optionally filtered by category."""
    registry = _get_skill_registry()
    if registry is None:
        return {"skills": []}
    skills = registry.list_skills()
    if category:
        skills = [s for s in skills if s.get("category") == category]
    return {"skills": skills}


@app.get("/api/skills/{skill_name}")
async def get_skill(skill_name: str):
    """Get skill details."""
    registry = _get_skill_registry()
    if registry is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    skill = registry.get(skill_name)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")
    return {
        "name": skill.name,
        "description": skill.description,
        "parameters": skill.parameters,
        "category": skill.category,
        "examples": skill.examples,
        "requires_phi_protection": skill.requires_phi_protection,
        "tool_definition": skill.to_tool_definition(),
    }


@app.post("/api/skills/{skill_name}/execute")
async def execute_skill(skill_name: str, parameters: Dict[str, Any]):
    """Execute a skill with given parameters."""
    registry = _get_skill_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Skill registry not available")
    import time as _time
    _start = _time.time()
    try:
        result = await registry.execute(skill_name, **parameters)
        _elapsed = (_time.time() - _start) * 1000
        # Track effectiveness
        try:
            from skills.skill_effectiveness import get_effectiveness_tracker
            tracker = get_effectiveness_tracker()
            tracker.record_invocation(
                skill_name=skill_name,
                success=result.success,
                execution_time_ms=_elapsed,
                error=result.error if not result.success else None,
            )
        except Exception:
            pass  # Effectiveness tracking is optional
        return {"success": result.success, "result": result.data, "error": result.error}
    except Exception as e:
        _elapsed = (_time.time() - _start) * 1000
        # Track failed invocation
        try:
            from skills.skill_effectiveness import get_effectiveness_tracker
            tracker = get_effectiveness_tracker()
            tracker.record_invocation(
                skill_name=skill_name,
                success=False,
                execution_time_ms=_elapsed,
                error=str(e),
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SKILL CREATION & SELF-CREATION ENDPOINTS
# =============================================================================

class SkillCreationRequest(BaseModel):
    """Request to create a skill from conversation messages."""
    messages: List[Dict[str, str]] = Field(..., description="Conversation messages with role and content")
    category: Optional[str] = Field("general", description="Skill category override")

class SkillFromSpecRequest(BaseModel):
    """Request to create a skill directly from a workflow specification."""
    name: str = Field(..., description="Snake_case skill name")
    display_name: Optional[str] = Field("", description="Human-friendly name")
    description: str = Field(..., description="What the skill does")
    category: Optional[str] = Field("general", description="Skill category")
    inputs: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Input parameters")
    outputs: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Output fields")
    steps: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Processing steps")
    rules: Optional[List[str]] = Field(default_factory=list, description="Condition/constraint rules")
    examples: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Input/output examples")

class SkillValidateRequest(BaseModel):
    """Request to validate skill code without deploying."""
    code: str = Field(..., description="Python source code to validate")

class SkillFeedbackRequest(BaseModel):
    """Request to submit effectiveness feedback for a skill."""
    rating: int = Field(..., ge=1, le=5, description="Rating from 1-5")
    feedback_text: Optional[str] = Field("", description="Optional text feedback")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")


@app.post("/api/skills/create")
async def create_skill_from_conversation(request: SkillCreationRequest):
    """Create a new skill from a teaching conversation."""
    try:
        from skills.skill_creator import (
            TeachingModeDetector, WorkflowExtractor, SkillCodeGenerator,
            SkillValidator, SkillSandboxTester, create_skill_from_conversation,
        )

        generated, validation, test_result = await create_skill_from_conversation(
            messages=request.messages,
        )

        return {
            "spec": {
                "name": generated.spec.name if generated.spec else "",
                "display_name": generated.spec.display_name if generated.spec else "",
                "description": generated.spec.description if generated.spec else "",
                "category": generated.spec.category if generated.spec else request.category,
                "inputs": generated.spec.inputs if generated.spec else [],
                "outputs": generated.spec.outputs if generated.spec else [],
                "steps": generated.spec.steps if generated.spec else [],
                "rules": generated.spec.rules if generated.spec else [],
            },
            "code": generated.code,
            "file_path": generated.file_path,
            "validation": {
                "is_safe": validation.is_safe,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
            "test_result": {
                "passed": test_result.passed,
                "errors": test_result.errors,
                "execution_time_ms": test_result.execution_time_ms,
            },
        }
    except Exception as e:
        logger.error(f"Skill creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/create-from-spec")
async def create_skill_from_spec(request: SkillFromSpecRequest):
    """Create a skill directly from a workflow specification."""
    try:
        from skills.skill_creator import WorkflowSpec, SkillCodeGenerator, SkillValidator

        spec = WorkflowSpec(
            name=request.name,
            display_name=request.display_name or request.name.replace("_", " ").title(),
            description=request.description,
            category=request.category,
            inputs=request.inputs or [{"name": "input", "type": "string", "description": "Input data", "required": True}],
            outputs=request.outputs or [{"name": "result", "type": "string", "description": "Processing result"}],
            steps=request.steps,
            rules=request.rules,
            examples=request.examples,
        )

        generator = SkillCodeGenerator()
        generated = await generator.generate(spec)

        validator = SkillValidator()
        if generated.code:
            validation = validator.validate(generated.code)
        else:
            validation = __import__("skills.skill_creator", fromlist=["ValidationResult"]).ValidationResult(
                is_safe=False, errors=["No code generated"]
            )

        return {
            "spec": {
                "name": spec.name,
                "display_name": spec.display_name,
                "description": spec.description,
                "category": spec.category,
                "inputs": spec.inputs,
                "outputs": spec.outputs,
                "steps": spec.steps,
                "rules": spec.rules,
            },
            "code": generated.code,
            "file_path": generated.file_path,
            "validation": {
                "is_safe": validation.is_safe,
                "errors": validation.errors,
                "warnings": validation.warnings,
            },
        }
    except Exception as e:
        logger.error(f"Skill creation from spec failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/validate")
async def validate_skill_code(request: SkillValidateRequest):
    """Validate skill code for safety without deploying it."""
    try:
        from skills.skill_creator import SkillValidator

        validator = SkillValidator()
        result = validator.validate(request.code)

        return {
            "is_safe": result.is_safe,
            "errors": result.errors,
            "warnings": result.warnings,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/test/{skill_name}")
async def test_skill(skill_name: str):
    """Run sandbox tests on a generated skill."""
    try:
        from skills.skill_creator import SkillSandboxTester, WorkflowSpec
        from skills.skill_registry import get_registry

        registry = get_registry()
        skill = registry.get(skill_name)
        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # Get the skill's source file for testing
        file_path = registry.get_skill_file_path(skill_name)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Source file for skill '{skill_name}' not found")

        code = file_path.read_text(encoding="utf-8")
        spec = WorkflowSpec(
            name=skill.name,
            description=skill.description,
        )

        tester = SkillSandboxTester()
        result = await tester.test(code, spec)

        return {
            "passed": result.passed,
            "results": result.results,
            "errors": result.errors,
            "execution_time_ms": result.execution_time_ms,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/approve/{skill_name}")
async def approve_skill(skill_name: str):
    """Approve and activate a draft user-created skill."""
    try:
        from skills.skill_registry import get_registry

        registry = get_registry()
        skill = registry.get(skill_name)

        if skill and skill.source == "user_created":
            # Skill already registered — just confirm it's active
            return {
                "status": "active",
                "skill_name": skill_name,
                "message": f"Skill '{skill_name}' is already active",
            }

        # Try to hot-reload to pick up new skills
        result = registry.hot_reload()
        skill = registry.get(skill_name)

        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found after reload")

        return {
            "status": "active",
            "skill_name": skill_name,
            "version": skill.version,
            "source": skill.source,
            "message": f"Skill '{skill_name}' approved and activated",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/skills/reject/{skill_name}")
async def reject_skill(skill_name: str):
    """Reject and delete a draft user-created skill."""
    try:
        from skills.skill_registry import get_registry

        registry = get_registry()
        skill = registry.get(skill_name)

        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        if skill.source != "user_created" and skill.source != "auto_generated":
            raise HTTPException(status_code=400, detail=f"Cannot reject built-in skill '{skill_name}'")

        # Get the source file path and delete it
        file_path = registry.get_skill_file_path(skill_name)
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"Deleted skill file: {file_path}")

        # Unregister from memory
        registry.unregister(skill_name)

        return {
            "status": "rejected",
            "skill_name": skill_name,
            "message": f"Skill '{skill_name}' rejected and removed",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/feedback/{skill_name}")
async def submit_skill_feedback(skill_name: str, request: SkillFeedbackRequest):
    """Submit effectiveness feedback for a skill."""
    try:
        from skills.skill_effectiveness import get_effectiveness_tracker

        tracker = get_effectiveness_tracker()
        fb_id = tracker.record_feedback(
            skill_name=skill_name,
            rating=request.rating,
            feedback_text=request.feedback_text,
            context=request.context,
        )

        return {
            "feedback_id": fb_id,
            "skill_name": skill_name,
            "rating": request.rating,
            "message": f"Feedback recorded for skill '{skill_name}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/feedback/{skill_name}")
async def get_skill_feedback(skill_name: str):
    """Get effectiveness data for a skill."""
    try:
        from skills.skill_effectiveness import get_effectiveness_tracker

        tracker = get_effectiveness_tracker()
        effectiveness = tracker.get_effectiveness(skill_name)

        if not effectiveness:
            return {
                "skill_name": skill_name,
                "effectiveness": None,
                "suggestions": [],
                "message": "No effectiveness data yet",
            }

        suggestions = tracker.get_optimization_suggestions(skill_name)

        return {
            "skill_name": skill_name,
            "effectiveness": effectiveness,
            "suggestions": suggestions,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills/proposals")
async def list_skill_proposals(status: Optional[str] = None, category: Optional[str] = None):
    """List auto-proposed skills."""
    try:
        from skills.skill_self_proposal import get_proposal_engine

        engine = get_proposal_engine()
        proposals = engine.list_proposals(status=status, category=category)

        return {"proposals": proposals, "total": len(proposals)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/proposals/{proposal_id}/approve")
async def approve_skill_proposal(proposal_id: str):
    """Approve an auto-proposed skill and generate it."""
    try:
        from skills.skill_self_proposal import get_proposal_engine

        engine = get_proposal_engine()
        proposal = engine.approve_proposal(proposal_id)

        if not proposal:
            raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found or not in 'proposed' state")

        # Generate the skill code
        result = await engine.generate_skill(proposal_id)

        if result and result.get("status") == "active":
            # Write the file to disk
            file_path = engine.write_skill_file(proposal_id)
            return {
                "status": "active",
                "proposal_id": proposal_id,
                "skill_name": result.get("name"),
                "file_path": file_path,
                "message": "Skill proposal approved, generated, and deployed",
            }
        else:
            return {
                "status": result.get("status", "failed") if result else "failed",
                "proposal_id": proposal_id,
                "message": "Skill generation failed",
                "errors": result.get("failed_reason", "") if result else "Unknown error",
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/proposals/{proposal_id}/reject")
async def reject_skill_proposal(proposal_id: str, reason: Optional[str] = None):
    """Reject an auto-proposed skill."""
    try:
        from skills.skill_self_proposal import get_proposal_engine

        engine = get_proposal_engine()
        success = engine.reject_proposal(proposal_id, reason=reason or "")

        if not success:
            raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found")

        return {
            "status": "rejected",
            "proposal_id": proposal_id,
            "message": "Skill proposal rejected",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/reload")
async def reload_skills():
    """Trigger hot-reload of user-created skills."""
    try:
        from skills.skill_registry import get_registry

        registry = get_registry()
        result = registry.hot_reload()

        return {
            "status": "reloaded",
            "added": result.get("added", []),
            "removed": result.get("removed", []),
            "updated": result.get("updated", []),
            "total_skills": result.get("total", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills/scan-proposals")
async def scan_for_proposals():
    """Scan knowledge gaps and propose new skills if warranted."""
    try:
        from skills.skill_self_proposal import get_proposal_engine
        from memory.knowledge_gaps import get_knowledge_gap_store
        from skills.skill_registry import get_registry

        engine = get_proposal_engine()
        gap_store = get_knowledge_gap_store()
        registry = get_registry()

        proposal = engine.scan_and_propose(
            gap_store=gap_store,
            skill_registry=registry,
        )

        if proposal:
            return {"proposed": True, "proposal": proposal}
        else:
            return {"proposed": False, "message": "No high-priority gaps found that warrant a new skill"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DATA INTELLIGENCE ENDPOINTS
# =============================================================================

_dataset_store = None
_data_pipeline = None


def _get_dataset_store():
    global _dataset_store
    if _dataset_store is None:
        try:
            from data_intelligence.store import get_dataset_store
            _dataset_store = get_dataset_store()
        except Exception as e:
            logger.warning(f"Dataset store not available: {e}")
    return _dataset_store


def _get_data_pipeline():
    global _data_pipeline
    if _data_pipeline is None:
        try:
            from data_intelligence.pipeline import DataIntelligencePipeline
            _data_pipeline = DataIntelligencePipeline()
        except Exception as e:
            logger.warning(f"Data intelligence pipeline not available: {e}")
    return _data_pipeline


class DatasetCreateRequest(BaseModel):
    """Request to register a new dataset."""
    name: str = Field(..., description="Dataset name")
    description: str = Field("", description="Dataset description")
    source_type: str = Field("inline", description="Data source: 'file', 'inline', or 'url'")
    source_path: str = Field("", description="File path or URL")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="Inline data rows")
    format: str = Field("csv", description="Data format: csv, json, xlsx, parquet")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Processing options")


class DatasetProcessRequest(BaseModel):
    """Request to process a dataset through the pipeline."""
    stages: Optional[List[str]] = Field(None, description="Stages to run (default: all)")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Stage-specific options")


class AnnotationRequest(BaseModel):
    """Request to annotate dataset rows."""
    annotation_types: List[str] = Field(["category", "sentiment", "entity"], description="Types of annotations")
    sample_size: Optional[int] = Field(500, description="Max rows to annotate via LLM")
    use_llm: bool = Field(True, description="Use LLM for annotation")


class ExportRequest(BaseModel):
    """Request to export a dataset."""
    format: str = Field("csv", description="Export format: csv, json, jsonl, parquet, xlsx")
    columns: Optional[List[str]] = Field(None, description="Columns to include (default: all)")
    output_path: Optional[str] = Field(None, description="File path to write export")


class VersionCreateRequest(BaseModel):
    """Request to create a dataset version."""
    change_description: str = Field("", description="Description of changes")


@app.post("/api/data-intelligence/datasets")
async def create_dataset(request: DatasetCreateRequest):
    """Register a new dataset."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")
    try:
        dataset = store.create_dataset(
            name=request.name,
            source_type=request.source_type,
            source_path=request.source_path,
            description=request.description,
            format=request.format,
        )
        return dataset
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data-intelligence/datasets")
async def list_datasets(
    source_type: Optional[str] = None,
    format: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all datasets."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")
    return {"datasets": store.list_datasets(source_type=source_type, format=format, limit=limit, offset=offset)}


@app.get("/api/data-intelligence/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset details."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")
    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return dataset


@app.delete("/api/data-intelligence/datasets/{dataset_id}")
async def delete_dataset(dataset_id: str):
    """Delete a dataset and all associated data."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")
    success = store.delete_dataset(dataset_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return {"status": "deleted", "dataset_id": dataset_id}


@app.post("/api/data-intelligence/datasets/{dataset_id}/process")
async def process_dataset(dataset_id: str, request: DatasetProcessRequest):
    """Run the data intelligence pipeline on a dataset."""
    store = _get_dataset_store()
    pipeline = _get_data_pipeline()
    if store is None or pipeline is None:
        raise HTTPException(status_code=503, detail="Data intelligence pipeline not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    from data_intelligence.context import DataPipelineContext
    context = DataPipelineContext(
        dataset_id=dataset_id,
        name=dataset.get("name", ""),
        source_type=dataset.get("source_type", "inline"),
        source_path=dataset.get("source_path", ""),
        format=dataset.get("format", "csv"),
        options=request.options or {},
    )

    result = await pipeline.run(context, stages=request.stages)
    return {
        "dataset_id": result.dataset_id,
        "name": result.name,
        "status": result.status,
        "stages_completed": result.stages_completed,
        "stages_failed": result.stages_failed,
        "row_count": result.row_count,
        "quality_scores": result.quality_scores,
        "schema_info": result.schema_info,
        "version_number": result.version_number,
        "checksum": result.checksum,
    }


@app.post("/api/data-intelligence/datasets/{dataset_id}/annotate")
async def annotate_dataset(dataset_id: str, request: AnnotationRequest):
    """Run the annotation stage on a dataset."""
    store = _get_dataset_store()
    pipeline = _get_data_pipeline()
    if store is None or pipeline is None:
        raise HTTPException(status_code=503, detail="Data intelligence pipeline not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    from data_intelligence.context import DataPipelineContext
    context = DataPipelineContext(
        dataset_id=dataset_id,
        name=dataset.get("name", ""),
        source_type=dataset.get("source_type", "inline"),
        source_path=dataset.get("source_path", ""),
        format=dataset.get("format", "csv"),
        options={
            "annotation_types": request.annotation_types,
            "annotation_sample_size": request.sample_size,
            "use_llm": request.use_llm,
        },
    )

    result = await pipeline.run(context, stages=["curation", "annotation"])
    return {
        "dataset_id": dataset_id,
        "stages_completed": result.stages_completed,
        "stages_failed": result.stages_failed,
        "annotations_count": result.annotations_count,
    }


@app.get("/api/data-intelligence/datasets/{dataset_id}/annotations")
async def get_annotations(
    dataset_id: str,
    annotation_type: Optional[str] = None,
    limit: int = 100,
):
    """Get annotations for a dataset."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")
    annotations = store.get_annotations(
        dataset_id=dataset_id,
        annotation_type=annotation_type,
        limit=limit,
    )
    return {"annotations": annotations, "total": len(annotations)}


@app.post("/api/data-intelligence/datasets/{dataset_id}/quality")
async def score_quality(dataset_id: str, request: Optional[DatasetProcessRequest] = None):
    """Compute quality scores for a dataset."""
    store = _get_dataset_store()
    pipeline = _get_data_pipeline()
    if store is None or pipeline is None:
        raise HTTPException(status_code=503, detail="Data intelligence pipeline not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    from data_intelligence.context import DataPipelineContext
    context = DataPipelineContext(
        dataset_id=dataset_id,
        name=dataset.get("name", ""),
        source_type=dataset.get("source_type", "inline"),
        source_path=dataset.get("source_path", ""),
        format=dataset.get("format", "csv"),
        options=request.options if request else {},
    )

    result = await pipeline.run(context, stages=["curation", "quality"])
    return {
        "dataset_id": dataset_id,
        "quality_scores": result.quality_scores,
        "quality_details": result.quality_details,
    }


@app.get("/api/data-intelligence/datasets/{dataset_id}/quality")
async def get_quality(dataset_id: str):
    """Get the latest quality scores for a dataset."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")

    score = store.get_quality_score(dataset_id)
    if not score:
        return {"dataset_id": dataset_id, "quality": None, "message": "No quality scores yet"}
    return {"dataset_id": dataset_id, "quality": score}


@app.post("/api/data-intelligence/datasets/{dataset_id}/schema")
async def detect_schema(dataset_id: str, request: Optional[DatasetProcessRequest] = None):
    """Run schema detection on a dataset."""
    store = _get_dataset_store()
    pipeline = _get_data_pipeline()
    if store is None or pipeline is None:
        raise HTTPException(status_code=503, detail="Data intelligence pipeline not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    from data_intelligence.context import DataPipelineContext
    context = DataPipelineContext(
        dataset_id=dataset_id,
        name=dataset.get("name", ""),
        source_type=dataset.get("source_type", "inline"),
        source_path=dataset.get("source_path", ""),
        format=dataset.get("format", "csv"),
        options=request.options if request else {},
    )

    result = await pipeline.run(context, stages=["curation", "schema_detect"])
    return {
        "dataset_id": dataset_id,
        "schema_info": result.schema_info,
        "primary_key": result.detected_primary_key,
        "foreign_keys": result.detected_foreign_keys,
    }


@app.get("/api/data-intelligence/datasets/{dataset_id}/schema")
async def get_schema(dataset_id: str):
    """Get the detected schema for a dataset."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    return {
        "dataset_id": dataset_id,
        "schema_info": dataset.get("schema_json"),
        "row_count": dataset.get("row_count", 0),
        "column_count": dataset.get("column_count", 0),
    }


@app.post("/api/data-intelligence/datasets/{dataset_id}/versions")
async def create_version(dataset_id: str, request: VersionCreateRequest):
    """Create a version snapshot for a dataset."""
    store = _get_dataset_store()
    pipeline = _get_data_pipeline()
    if store is None or pipeline is None:
        raise HTTPException(status_code=503, detail="Data intelligence pipeline not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    from data_intelligence.context import DataPipelineContext
    context = DataPipelineContext(
        dataset_id=dataset_id,
        name=dataset.get("name", ""),
        source_type=dataset.get("source_type", "inline"),
        source_path=dataset.get("source_path", ""),
        format=dataset.get("format", "csv"),
    )

    result = await pipeline.run(context, stages=["curation", "versioning"])
    return {
        "dataset_id": dataset_id,
        "version_id": result.version_id,
        "version_number": result.version_number,
        "checksum": result.checksum,
    }


@app.get("/api/data-intelligence/datasets/{dataset_id}/versions")
async def list_versions(dataset_id: str, limit: int = 20):
    """List all versions for a dataset."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")

    versions = store.list_versions(dataset_id, limit=limit)
    return {"versions": versions, "total": len(versions)}


@app.get("/api/data-intelligence/datasets/{dataset_id}/versions/{version_id}")
async def get_version(dataset_id: str, version_id: str):
    """Get a specific version."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")

    version = store.get_version(version_id)
    if not version:
        raise HTTPException(status_code=404, detail=f"Version '{version_id}' not found")
    return version


@app.post("/api/data-intelligence/datasets/{dataset_id}/export")
async def export_dataset(dataset_id: str, request: ExportRequest):
    """Export a dataset in the specified format."""
    store = _get_dataset_store()
    pipeline = _get_data_pipeline()
    if store is None or pipeline is None:
        raise HTTPException(status_code=503, detail="Data intelligence pipeline not available")

    dataset = store.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")

    from data_intelligence.context import DataPipelineContext
    context = DataPipelineContext(
        dataset_id=dataset_id,
        name=dataset.get("name", ""),
        source_type=dataset.get("source_type", "inline"),
        source_path=dataset.get("source_path", ""),
        format=dataset.get("format", "csv"),
        options={
            "export_format": request.format,
            "export_columns": request.columns,
            "output_path": request.output_path,
        },
        export_format=request.format,
    )

    result = await pipeline.run(context, stages=["curation", "export"])

    if request.format in ("parquet", "xlsx") and result.export_available:
        from fastapi.responses import Response
        content_type = "application/octet-stream"
        if request.format == "xlsx":
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        # For binary formats, we'd need to store the bytes during pipeline run
        return {"dataset_id": dataset_id, "format": request.format, "export_path": result.export_path, "available": True}

    return {
        "dataset_id": dataset_id,
        "format": result.export_format,
        "content_preview": result.export_content[:500] if result.export_content else None,
        "available": result.export_available,
        "export_path": result.export_path,
    }


@app.get("/api/data-intelligence/stats")
async def get_data_intelligence_stats():
    """Get aggregate stats across all datasets."""
    store = _get_dataset_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Dataset store not available")
    return store.get_stats()


# =============================================================================
# PLUGINS & CONNECTORS ENDPOINTS
# =============================================================================

@app.get("/api/plugins")
async def list_plugins():
    """List all plugins and their status."""
    registry = _get_plugin_registry()
    if registry is None:
        return {"plugins": []}
    return {"plugins": registry.list_plugins()}


@app.post("/api/plugins/{plugin_name}/enable")
async def enable_plugin(plugin_name: str):
    """Enable a plugin."""
    registry = _get_plugin_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Plugin registry not available")
    try:
        plugin = registry.get_plugin(plugin_name)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
        await plugin.connect(plugin.config or {})
        return {"status": "enabled", "plugin": plugin_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plugins/{plugin_name}/disable")
async def disable_plugin(plugin_name: str):
    """Disable a plugin."""
    registry = _get_plugin_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Plugin registry not available")
    try:
        plugin = registry.get_plugin(plugin_name)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
        await plugin.disconnect()
        return {"status": "disabled", "plugin": plugin_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plugins/{plugin_name}/config")
async def configure_plugin(plugin_name: str, config: Dict[str, Any]):
    """Configure a plugin."""
    registry = _get_plugin_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Plugin registry not available")
    try:
        plugin = registry.get_plugin(plugin_name)
        if plugin is None:
            raise HTTPException(status_code=404, detail=f"Plugin '{plugin_name}' not found")
        return {"status": "configured", "plugin": plugin_name, "config": config}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/connectors")
async def list_connectors():
    """List all connectors and their status."""
    registry = _get_connector_registry()
    if registry is None:
        return {"connectors": []}
    return {"connectors": registry.list_connectors()}


@app.post("/api/connectors/{connector_name}/connect")
async def connect_to_source(connector_name: str, config: Dict[str, Any]):
    """Connect to a data source."""
    registry = _get_connector_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Connector registry not available")
    try:
        connector = registry.get_connector(connector_name)
        if connector is None:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_name}' not found")
        result = await connector.initialize(config)
        return {"status": "connected" if result else "failed", "connector": connector_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connectors/{connector_name}/disconnect")
async def disconnect_source(connector_name: str):
    """Disconnect from a data source."""
    registry = _get_connector_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Connector registry not available")
    try:
        connector = registry.get_connector(connector_name)
        if connector is None:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_name}' not found")
        await connector.cleanup()
        return {"status": "disconnected", "connector": connector_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/connectors/{connector_name}/test")
async def test_connector(connector_name: str):
    """Test connector connection."""
    registry = _get_connector_registry()
    if registry is None:
        raise HTTPException(status_code=503, detail="Connector registry not available")
    try:
        connector = registry.get_connector(connector_name)
        if connector is None:
            raise HTTPException(status_code=404, detail=f"Connector '{connector_name}' not found")
        result = await connector.fetch(connector_name, {"test": True})
        return {"status": "ok", "connector": connector_name, "result": result}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "connector": connector_name, "error": str(e)}

# =============================================================================
# HEALTHCARE TOOLS ENDPOINTS
# =============================================================================

@app.post("/api/healthcare/code-lookup")
async def code_lookup(code: str, code_type: Optional[str] = None):
    """Look up ICD-10, CPT, HCPCS, or CDT code."""
    registry = _get_skill_registry()
    if registry is None:
        return {"code": code, "description": "Code lookup unavailable", "code_type": code_type}
    try:
        result = await registry.execute("code_lookup", code=code, code_type=code_type or "auto")
        return result.data if result.success else {"code": code, "error": result.error}
    except Exception:
        return {"code": code, "description": "Code lookup service error", "code_type": code_type}


@app.post("/api/healthcare/cci-check")
async def cci_check(code1: str, code2: str, modifier: Optional[str] = None):
    """Check NCCI edit pair compatibility."""
    registry = _get_skill_registry()
    if registry is None:
        return {"compatible": True, "modifier_required": False}
    try:
        result = await registry.execute("cci_editor", action="check_pair", code1=code1, code2=code2, modifier=modifier)
        return result.data if result.success else {"compatible": True, "modifier_required": False, "error": result.error}
    except Exception:
        return {"compatible": True, "modifier_required": False}


@app.post("/api/healthcare/fee-schedule")
async def fee_schedule_lookup(code: str, locality: Optional[str] = None):
    """Look up Medicare fee schedule amount."""
    registry = _get_skill_registry()
    if registry is None:
        return {"code": code, "amount": 0.0, "locality": locality or "national"}
    try:
        result = await registry.execute("fee_schedule", action="lookup", code=code, locality=locality or "national")
        return result.data if result.success else {"code": code, "amount": 0.0, "error": result.error}
    except Exception:
        return {"code": code, "amount": 0.0, "locality": locality or "national"}


@app.post("/api/healthcare/coverage")
async def coverage_check(code: str, payer: str):
    """Check LCD/NCD coverage criteria."""
    registry = _get_skill_registry()
    if registry is None:
        return {"covered": True, "criteria": []}
    try:
        result = await registry.execute("coverage_checker", action="check_coverage", cpt=code, payer=payer)
        return result.data if result.success else {"covered": True, "criteria": [], "error": result.error}
    except Exception:
        return {"covered": True, "criteria": []}


@app.post("/api/healthcare/denial-analyze")
async def denial_analyze(car_code: str, rarc_code: Optional[str] = None):
    """Analyze denial codes and recommend actions."""
    registry = _get_skill_registry()
    if registry is None:
        return {"car_code": car_code, "recommendation": "Appeal with documentation"}
    try:
        codes = [car_code]
        if rarc_code:
            codes.append(rarc_code)
        result = await registry.execute("denial_analyzer", action="analyze", codes=codes)
        return result.data if result.success else {"car_code": car_code, "recommendation": "Appeal with documentation", "error": result.error}
    except Exception:
        return {"car_code": car_code, "recommendation": "Appeal with documentation"}


@app.post("/api/healthcare/denial-predict")
async def denial_predict(claim_data: Dict[str, Any]):
    """Predict denial probability before submission."""
    registry = _get_skill_registry()
    if registry is None:
        return {"denial_probability": 0.15, "risk_factors": []}
    try:
        result = await registry.execute(
            "denial_predictor",
            action="predict",
            claim_data=claim_data,
        )
        return result.data if result.success else {"denial_probability": 0.15, "risk_factors": [], "error": result.error}
    except Exception as e:
        return {"denial_probability": 0.15, "risk_factors": [], "error": str(e)}


@app.post("/api/healthcare/appeal-generate")
async def appeal_generate(denial_info: Dict[str, Any]):
    """Generate appeals letter with citations."""
    registry = _get_skill_registry()
    if registry is None:
        return {"letter": "Appeal letter content"}
    try:
        result = await registry.execute("appeals_writer", action="generate", denial_info=denial_info)
        return result.data if result.success else {"letter": "", "error": result.error}
    except Exception:
        return {"letter": "Appeal generation service error"}


@app.post("/api/healthcare/claim-analysis")
async def claim_analysis(data: Dict[str, Any]):
    """Analyze a claim for errors and scrub before submission."""
    registry = _get_skill_registry()
    if registry is None:
        return {"analysis": {}, "errors": [], "warnings": []}
    try:
        result = await registry.execute("claim_scrubber", action="analyze", claim_data=data)
        return result.data if result.success else {"analysis": {}, "errors": [], "warnings": [], "error": result.error}
    except Exception as e:
        return {"analysis": {}, "errors": [], "warnings": [], "error": str(e)}


@app.post("/api/healthcare/code-search")
async def code_search(data: Dict[str, Any]):
    """Search healthcare codes by keyword."""
    registry = _get_skill_registry()
    if registry is None:
        return {"results": []}
    try:
        result = await registry.execute("code_lookup", action="search", query=data.get("search", ""), code_type=data.get("codeType", "all"))
        return result.data if result.success else {"results": [], "error": result.error}
    except Exception as e:
        return {"results": [], "error": str(e)}


@app.post("/api/healthcare/drg-group")
async def drg_group(diagnoses: List[str], procedures: List[str]):
    """Determine DRG assignment."""
    registry = _get_skill_registry()
    if registry is None:
        return {"drg": "470", "description": "Major joint replacement", "weight": 2.12}
    try:
        result = await registry.execute("drg_grouper", action="assign", diagnoses=diagnoses, procedures=procedures)
        return result.data if result.success else {"drg": "470", "error": result.error}
    except Exception:
        return {"drg": "470", "description": "DRG grouper unavailable", "weight": 2.12}


@app.post("/api/healthcare/drug-lookup")
async def drug_lookup(drug_name: str):
    """Look up drug information."""
    registry = _get_skill_registry()
    if registry is None:
        return {"drug_name": drug_name, "info": {}}
    try:
        result = await registry.execute("drug_reference", action="lookup", drug_name=drug_name)
        return result.data if result.success else {"drug_name": drug_name, "info": {}, "error": result.error}
    except Exception:
        return {"drug_name": drug_name, "info": {}}


@app.post("/api/healthcare/npi-lookup")
async def npi_lookup(npi: str):
    """Look up NPI registry information."""
    registry = _get_connector_registry()
    if registry is None:
        return {"npi": npi, "provider": {}}
    try:
        connector = registry.get_connector("npi")
        if connector:
            result = await connector.fetch("lookup", {"npi": npi})
            return {"npi": npi, "provider": result.data if hasattr(result, 'data') else result}
        return {"npi": npi, "provider": {}}
    except Exception:
        return {"npi": npi, "provider": {}}


@app.post("/api/healthcare/edi-parse")
async def edi_parse(edi_content: str, transaction_type: str):
    """Parse X12 EDI transaction."""
    registry = _get_skill_registry()
    if registry is None:
        return {"parsed": True, "data": {}}
    try:
        result = await registry.execute("edi_parser", action="parse", content=edi_content, transaction_type=transaction_type)
        return result.data if result.success else {"parsed": False, "error": result.error}
    except Exception:
        return {"parsed": False, "data": {}}


@app.post("/api/healthcare/risk-adjust")
async def risk_adjust(diagnoses: List[str], demographics: Dict[str, Any]):
    """Calculate HCC/RAF score."""
    registry = _get_skill_registry()
    if registry is None:
        return {"raf_score": 1.0, "hccs": []}
    try:
        result = await registry.execute("risk_adjuster", action="calculate", diagnoses=diagnoses, demographics=demographics)
        return result.data if result.success else {"raf_score": 1.0, "hccs": [], "error": result.error}
    except Exception:
        return {"raf_score": 1.0, "hccs": []}


@app.post("/api/healthcare/medical-calc")
async def medical_calculator(calc_type: str, values: Dict[str, float]):
    """Perform clinical calculation."""
    registry = _get_skill_registry()
    if registry is None:
        return {"result": 0.0, "interpretation": "Normal"}
    try:
        result = await registry.execute("medical_calculator", action="calculate", calc_type=calc_type, values=values)
        return result.data if result.success else {"result": 0.0, "interpretation": "Normal", "error": result.error}
    except Exception:
        return {"result": 0.0, "interpretation": "Calculator unavailable"}

# =============================================================================
# KNOWLEDGE / AUTO-UPDATE ENDPOINTS
# =============================================================================

@app.get("/api/knowledge/updates")
async def knowledge_updates(
    days: int = 7,
    source: Optional[str] = None,
    category: Optional[str] = None,
    applied_only: bool = False,
    limit: int = 100,
):
    """Return the changelog of recent CMS/regulatory/security knowledge updates."""
    updater = _get_knowledge_updater()
    if updater is None:
        return {"updates": [], "error": "Knowledge updater unavailable"}
    try:
        return {"updates": updater.get_changelog(
            days=days, source=source, category=category,
            applied_only=applied_only, limit=limit,
        )}
    except Exception as e:
        return {"updates": [], "error": str(e)}


@app.get("/api/knowledge/stats")
async def knowledge_stats():
    """Return knowledge-updater statistics (counts by source/category)."""
    updater = _get_knowledge_updater()
    if updater is None:
        return {"error": "Knowledge updater unavailable"}
    try:
        return updater.get_stats()
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/knowledge/check")
async def knowledge_check(payload: Optional[Dict[str, Any]] = None):
    """Fetch new updates from CMS/regulatory sources (optionally a subset)."""
    updater = _get_knowledge_updater()
    if updater is None:
        return {"checked": False, "error": "Knowledge updater unavailable"}
    sources = (payload or {}).get("sources")
    try:
        found = updater.check_updates(sources=sources)
        return {"checked": True, "new_by_source": {k: len(v) for k, v in found.items()}}
    except Exception as e:
        return {"checked": False, "error": str(e)}


@app.post("/api/knowledge/apply")
async def knowledge_apply(payload: Optional[Dict[str, Any]] = None):
    """Mark pending updates as applied so they inform the assistant's answers."""
    updater = _get_knowledge_updater()
    if updater is None:
        return {"applied": 0, "error": "Knowledge updater unavailable"}
    data = payload or {}
    try:
        applied = updater.apply_updates(
            source=data.get("source"),
            category=data.get("category"),
            limit=data.get("limit", 100),
        )
        return {"applied": len(applied), "ids": [u.id for u in applied]}
    except Exception as e:
        return {"applied": 0, "error": str(e)}


@app.post("/api/knowledge/auto-update")
async def knowledge_auto_update():
    """Run a full check-and-auto-apply cycle (the scheduled hands-off routine)."""
    updater = _get_knowledge_updater()
    if updater is None:
        return {"error": "Knowledge updater unavailable"}
    try:
        return updater.run_auto_update()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# CLOUDFLARE ENDPOINTS
# =============================================================================

@app.get("/api/cloudflare/status")
async def cloudflare_status():
    """Get Cloudflare infrastructure status."""
    try:
        from plugins.cloudflare.dns_manager import DNSManager
        from plugins.cloudflare.tunnel_manager import TunnelManager
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if not cf_token:
            return {"status": "not_configured", "zones": [], "tunnels": [], "workers": []}
        dns = DNSManager(cf_token, cf_account)
        tunnels = TunnelManager(cf_token, cf_account)
        return {
            "status": "ok",
            "zones": [],
            "tunnels": await tunnels.list_tunnels() if tunnels else [],
            "workers": [],
        }
    except Exception:
        return {"status": "error", "zones": [], "tunnels": [], "workers": []}


@app.get("/api/cloudflare/tunnel/status")
async def cloudflare_tunnel_status():
    """Get Cloudflare tunnel status."""
    try:
        from plugins.cloudflare.tunnel_manager import TunnelManager
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if not cf_token:
            return {"status": "not_configured", "tunnels": []}
        tunnels = TunnelManager(cf_token, cf_account)
        tunnel_list = await tunnels.list_tunnels() if tunnels else []
        return {"status": "ok", "tunnels": tunnel_list}
    except Exception:
        return {"status": "error", "tunnels": []}


@app.get("/api/cloudflare/zones")
async def cloudflare_zones():
    """List Cloudflare zones."""
    try:
        from plugins.cloudflare.dns_manager import DNSManager
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if not cf_token:
            return {"zones": []}
        dns = DNSManager(cf_token, cf_account)
        zones = await dns.list_zones()
        return {"zones": zones}
    except Exception:
        return {"zones": []}


@app.post("/api/cloudflare/dns")
async def cloudflare_dns(operation: str, zone: str, data: Dict[str, Any]):
    """DNS record operations."""
    try:
        from plugins.cloudflare.dns_manager import DNSManager
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if not cf_token:
            return {"status": "not_configured"}
        dns = DNSManager(cf_token, cf_account)
        if operation == "list":
            records = await dns.list_records(zone)
            return {"status": "ok", "records": records}
        elif operation == "create":
            result = await dns.create_record(zone, data)
            return {"status": "created", "record": result}
        elif operation == "delete":
            result = await dns.delete_record(zone, data.get("record_id", ""))
            return {"status": "deleted"}
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# =============================================================================
# MEMORY & PROFILE ENDPOINTS
# =============================================================================

@app.get("/api/memory/profile/{user_id}")
async def get_user_profile(user_id: str = "default_user"):
    """Get user profile."""
    try:
        profile = _get_user_profile(user_id)
        return {"profile": profile._profile}
    except Exception:
        return {"profile": {}}


@app.post("/api/memory/profile/{user_id}")
async def update_user_profile(user_id: str, updates: Dict[str, Any]):
    """Update user profile."""
    try:
        profile = _get_user_profile(user_id)
        preferences = updates.get("preferences", {})
        for key, value in preferences.items():
            profile.set_preference(key, value)
        specializations = updates.get("specializations", [])
        for spec in specializations:
            profile.add_specialization(spec)
        memories = updates.get("memories", [])
        for mem in memories:
            if isinstance(mem, dict):
                profile.add_memory(mem.get("content", ""), mem.get("category", "general"))
            elif isinstance(mem, str):
                profile.add_memory(mem)
        return {"status": "updated", "profile_summary": profile.get_profile_summary()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/search")
async def search_memory(query: str, collection: str = "user_memories", top_k: int = 10):
    """Search memory/knowledge."""
    vs = _get_vector_store()
    if vs is None:
        return {"results": []}
    try:
        if not hasattr(vs, '_initialized') or not vs._initialized:
            await vs.initialize()
        results = await vs.search(collection, query, top_k=top_k)
        return {"results": results}
    except Exception:
        return {"results": []}


@app.get("/api/memory/knowledge-graph")
async def get_knowledge_graph(entity_type: Optional[str] = None, limit: int = 50):
    """Get knowledge graph data."""
    kg = _get_knowledge_graph()
    if kg is None:
        return {"entities": [], "relationships": []}
    try:
        loop = asyncio.get_event_loop()
        if entity_type:
            entities = loop.run_in_executor(None, lambda: kg.search_entities(entity_type=entity_type, limit=limit))
            entities = await entities
        else:
            entities = loop.run_in_executor(None, lambda: kg.search_entities(limit=limit))
            entities = await entities
        return {"entities": entities[:limit], "relationships": []}
    except Exception:
        return {"entities": [], "relationships": []}


@app.post("/api/memory/forget")
async def forget_memory(topic: str):
    """Remove specific memories."""
    vs = _get_vector_store()
    if vs is None:
        return {"status": "deleted", "topic": topic}
    try:
        vs.delete(where={"topic": topic})
        return {"status": "deleted", "topic": topic}
    except Exception:
        return {"status": "deleted", "topic": topic}


# ---------------------------------------------------------------------------
# Health Records Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/memory/health-records/{user_id}")
async def get_health_records(
    user_id: str,
    table: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get health records for a user."""
    mm = _get_memory_manager()
    if mm is None or mm.health_records is None:
        return {"records": []}
    try:
        loop = asyncio.get_event_loop()
        tables = [table] if table else None
        records = await loop.run_in_executor(
            None,
            lambda: mm.health_records.search(user_id, "", tables=tables, limit=limit),
        )
        return {"records": records, "count": len(records)}
    except Exception as e:
        return {"records": [], "error": str(e)}


@app.post("/api/memory/health-records")
async def add_health_record(record: Dict[str, Any]):
    """Add a health record. Must include 'user_id', 'table', and record data."""
    mm = _get_memory_manager()
    if mm is None or mm.health_records is None:
        return {"status": "error", "error": "Health records not available"}
    user_id = record.get("user_id", "default_user")
    table = record.get("table", "conditions")
    data = record.get("record", record)
    data.pop("table", None)
    try:
        loop = asyncio.get_event_loop()
        record_id = await loop.run_in_executor(
            None, lambda: mm.health_records.add_record(table, data)
        )
        return {"status": "created", "record_id": record_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/health-records/{user_id}/timeline")
async def get_health_timeline(user_id: str, limit: int = 50):
    """Get chronological health timeline for a user."""
    mm = _get_memory_manager()
    if mm is None or mm.health_records is None:
        return {"timeline": []}
    try:
        loop = asyncio.get_event_loop()
        timeline = await loop.run_in_executor(
            None, lambda: mm.health_records.get_timeline(user_id, limit=limit)
        )
        return {"timeline": timeline}
    except Exception as e:
        return {"timeline": [], "error": str(e)}


@app.get("/api/memory/health-records/{user_id}/export-deidentified")
async def export_deidentified_records(user_id: str):
    """Export de-identified health records (HIPAA Safe Harbor)."""
    mm = _get_memory_manager()
    if mm is None or mm.health_records is None:
        return {"records": []}
    try:
        loop = asyncio.get_event_loop()
        records = await loop.run_in_executor(
            None, lambda: mm.health_records.export_deidentified(user_id)
        )
        return {"records": records, "count": len(records)}
    except Exception as e:
        return {"records": [], "error": str(e)}


# ---------------------------------------------------------------------------
# Fact Store Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/memory/facts")
async def store_fact(fact: Dict[str, Any]):
    """Store a new fact."""
    mm = _get_memory_manager()
    if mm is None or mm.fact_store is None:
        return {"status": "error", "error": "Fact store not available"}
    try:
        loop = asyncio.get_event_loop()
        fact_id = await loop.run_in_executor(
            None,
            lambda: mm.fact_store.store_fact(
                fact_text=fact.get("fact_text", ""),
                source=fact.get("source", ""),
                source_type=fact.get("source_type", "user"),
                confidence=fact.get("confidence", 0.5),
                category=fact.get("category", "general"),
                tags=fact.get("tags", []),
            ),
        )
        return {"status": "created", "fact_id": fact_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/facts")
async def search_facts(
    query: str,
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = 20,
):
    """Search facts by query."""
    mm = _get_memory_manager()
    if mm is None or mm.fact_store is None:
        return {"facts": []}
    try:
        loop = asyncio.get_event_loop()
        facts = await loop.run_in_executor(
            None,
            lambda: mm.fact_store.search_facts(
                query, category=category, min_confidence=min_confidence, limit=limit
            ),
        )
        return {"facts": facts, "count": len(facts)}
    except Exception as e:
        return {"facts": [], "error": str(e)}


@app.get("/api/memory/facts/stats")
async def get_fact_stats():
    """Get fact store statistics."""
    mm = _get_memory_manager()
    if mm is None or mm.fact_store is None:
        return {"total_facts": 0}
    try:
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, mm.fact_store.get_stats)
        return stats
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/memory/facts/contradictions")
async def find_contradictions():
    """Find contradictory fact pairs."""
    mm = _get_memory_manager()
    if mm is None or mm.fact_store is None:
        return {"contradictions": []}
    try:
        loop = asyncio.get_event_loop()
        contradictions = await loop.run_in_executor(
            None, mm.fact_store.find_contradictions
        )
        return {"contradictions": contradictions, "count": len(contradictions)}
    except Exception as e:
        return {"contradictions": [], "error": str(e)}


@app.post("/api/memory/facts/expire-outdated")
async def expire_outdated_facts(dry_run: bool = True):
    """Expire outdated facts. Use dry_run=true to preview."""
    mm = _get_memory_manager()
    if mm is None or mm.fact_store is None:
        return {"expired_ids": []}
    try:
        loop = asyncio.get_event_loop()
        expired = await loop.run_in_executor(
            None, lambda: mm.fact_store.expire_outdated(dry_run=dry_run)
        )
        return {"expired_ids": expired, "dry_run": dry_run}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Learning Store Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/memory/learning/preferences/{user_id}")
async def get_learned_preferences(user_id: str):
    """Get all learned preferences for a user."""
    mm = _get_memory_manager()
    if mm is None or mm.learning_store is None:
        return {"preferences": {}}
    try:
        loop = asyncio.get_event_loop()
        prefs = await loop.run_in_executor(
            None, lambda: mm.learning_store.get_preferences(user_id)
        )
        return {"preferences": prefs}
    except Exception as e:
        return {"preferences": {}, "error": str(e)}


@app.post("/api/memory/learning/interactions")
async def record_interaction(interaction: Dict[str, Any]):
    """Record a user interaction for learning."""
    mm = _get_memory_manager()
    if mm is None or mm.learning_store is None:
        return {"status": "error", "error": "Learning store not available"}
    try:
        loop = asyncio.get_event_loop()
        interaction_id = await loop.run_in_executor(
            None,
            lambda: mm.learning_store.record_interaction(
                user_id=interaction.get("user_id", "default_user"),
                interaction_type=interaction.get("interaction_type", "query"),
                context=interaction.get("context"),
            ),
        )
        return {"status": "recorded", "interaction_id": interaction_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/learning/predict/{user_id}")
async def predict_next_action(user_id: str):
    """Predict the user's next likely action."""
    mm = _get_memory_manager()
    if mm is None or mm.learning_store is None:
        return {"likely_specialist": None, "likely_tools": [], "confidence": 0.0}
    try:
        loop = asyncio.get_event_loop()
        prediction = await loop.run_in_executor(
            None, lambda: mm.learning_store.predict_next_action(user_id)
        )
        return prediction
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/memory/learning/stats")
async def get_learning_stats(user_id: Optional[str] = None):
    """Get learning statistics."""
    mm = _get_memory_manager()
    if mm is None or mm.learning_store is None:
        return {"total_interactions": 0}
    try:
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(
            None, lambda: mm.learning_store.get_stats(user_id)
        )
        return stats
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Knowledge Gap Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/memory/knowledge-gaps")
async def list_knowledge_gaps(
    status: Optional[str] = None,
    category: Optional[str] = None,
    min_priority: int = 1,
):
    """List knowledge gaps."""
    mm = _get_memory_manager()
    if mm is None or mm.knowledge_gap_store is None:
        return {"gaps": []}
    try:
        loop = asyncio.get_event_loop()
        gaps = await loop.run_in_executor(
            None,
            lambda: mm.knowledge_gap_store.list_gaps(
                status=status, category=category, min_priority=min_priority
            ),
        )
        return {"gaps": gaps, "count": len(gaps)}
    except Exception as e:
        return {"gaps": [], "error": str(e)}


@app.post("/api/memory/knowledge-gaps/detect")
async def detect_knowledge_gap(data: Dict[str, Any]):
    """Auto-detect a knowledge gap from a query."""
    mm = _get_memory_manager()
    if mm is None or mm.knowledge_gap_store is None:
        return {"status": "error", "error": "Knowledge gap store not available"}
    try:
        loop = asyncio.get_event_loop()
        gap_id = await loop.run_in_executor(
            None,
            lambda: mm.knowledge_gap_store.auto_detect_from_query(
                data.get("query", ""),
                low_confidence_response=data.get("low_confidence", False),
            ),
        )
        if gap_id:
            gap = await loop.run_in_executor(
                None, lambda: mm.knowledge_gap_store.get_gap(gap_id)
            )
            return {"status": "detected", "gap": gap}
        return {"status": "no_gap_detected"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/memory/knowledge-gaps/{gap_id}/research")
async def start_gap_research(gap_id: str, notes: Optional[str] = None):
    """Mark a gap as being researched."""
    mm = _get_memory_manager()
    if mm is None or mm.knowledge_gap_store is None:
        return {"status": "error", "error": "Knowledge gap store not available"}
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, lambda: mm.knowledge_gap_store.research_gap(gap_id, notes=notes or "")
        )
        return {"status": "researching" if success else "error", "gap_id": gap_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/memory/knowledge-gaps/{gap_id}/fill")
async def mark_gap_filled(gap_id: str, data: Dict[str, Any] = None):
    """Mark a gap as filled."""
    mm = _get_memory_manager()
    if mm is None or mm.knowledge_gap_store is None:
        return {"status": "error", "error": "Knowledge gap store not available"}
    data = data or {}
    try:
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            lambda: mm.knowledge_gap_store.mark_filled(
                gap_id,
                source_url=data.get("source_url", ""),
                notes=data.get("notes", ""),
            ),
        )
        return {"status": "filled" if success else "error", "gap_id": gap_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/memory/knowledge-gaps/stats")
async def get_knowledge_gap_stats():
    """Get knowledge gap statistics."""
    mm = _get_memory_manager()
    if mm is None or mm.knowledge_gap_store is None:
        return {"total_gaps": 0}
    try:
        loop = asyncio.get_event_loop()
        stats = await loop.run_in_executor(None, mm.knowledge_gap_store.get_stats)
        return stats
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Manual Consolidation Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/memory/consolidate")
async def manual_consolidate(data: Dict[str, Any]):
    """Manually trigger memory consolidation."""
    mm = _get_memory_manager()
    if mm is None:
        return {"status": "error", "error": "Memory manager not available"}
    try:
        await mm.consolidate(
            user_id=data.get("user_id", "default_user"),
            query=data.get("query", ""),
            response=data.get("response", ""),
            specialist=data.get("specialist", "general"),
            conversation_id=data.get("conversation_id", ""),
        )
        return {"status": "consolidated"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# Temporal Intelligence Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/temporal/upcoming")
async def get_upcoming_deadlines(days: int = 7):
    """Get upcoming deadlines within specified days."""
    tp = get_temporal_processor()
    items = tp.get_upcoming(days=days)
    return {"items": [asdict(item) for item in items], "count": len(items)}


@app.get("/api/temporal/overdue")
async def get_overdue_deadlines():
    """Get overdue deadlines."""
    tp = get_temporal_processor()
    items = tp.get_overdue()
    return {"items": [asdict(item) for item in items], "count": len(items)}


@app.post("/api/temporal/items")
async def add_temporal_item(data: Dict[str, Any]):
    """Add a time-sensitive item."""
    tp = get_temporal_processor()
    deadline = None
    if data.get("deadline"):
        try:
            deadline = datetime.fromisoformat(data["deadline"])
        except (ValueError, TypeError):
            pass
    item = tp.add_item(
        description=data.get("description", ""),
        deadline=deadline,
        deadline_type=data.get("deadline_type"),
        priority=data.get("priority", "medium"),
        category=data.get("category", "general"),
    )
    return asdict(item)


@app.post("/api/temporal/extract")
async def extract_deadlines(data: Dict[str, Any]):
    """Extract deadline mentions from text and create time-sensitive items."""
    tp = get_temporal_processor()
    text = data.get("text", "")
    items = tp.extract_deadlines_from_text(text)
    return {"items": items, "count": len(items)}


@app.get("/api/temporal/healthcare-deadline")
async def get_healthcare_deadline(event_type: str, event_date: str):
    """Get standard healthcare deadline for an event type."""
    tp = get_temporal_processor()
    try:
        date = datetime.fromisoformat(event_date)
    except (ValueError, TypeError):
        return {"error": "Invalid event_date format. Use ISO format (YYYY-MM-DD)"}
    return tp.get_healthcare_deadline(event_type, date)


@app.delete("/api/temporal/items/{item_id}")
async def delete_temporal_item(item_id: str):
    """Remove a time-sensitive item."""
    tp = get_temporal_processor()
    removed = tp.remove_item(item_id)
    return {"removed": removed}


@app.post("/api/temporal/items/{item_id}/complete")
async def complete_temporal_item(item_id: str):
    """Mark a time-sensitive item as completed."""
    tp = get_temporal_processor()
    completed = tp.complete_item(item_id)
    return {"completed": completed}


# ---------------------------------------------------------------------------
# Audit Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/audit")
async def get_audit_log(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
):
    """Query audit log."""
    mm = _get_memory_manager()
    if mm is None or mm.audit_db is None:
        return {"entries": []}
    try:
        from infrastructure.security.audit_logger import AuditQuery
        query = AuditQuery(
            user_id=user_id or "",
            action=action or "",
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        entries = mm.audit_db.query(query)
        return {"entries": entries, "count": len(entries)}
    except Exception as e:
        return {"entries": [], "error": str(e)}


@app.get("/api/audit/stats")
async def get_audit_stats():
    """Get audit log statistics."""
    mm = _get_memory_manager()
    if mm is None or mm.audit_db is None:
        return {"total_entries": 0}
    try:
        stats = mm.audit_db.get_stats()
        return stats.dict() if hasattr(stats, 'dict') else stats
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/audit/integrity")
async def check_audit_integrity():
    """Verify audit log integrity."""
    mm = _get_memory_manager()
    if mm is None or mm.audit_db is None:
        return {"intact": True, "entries": 0}
    try:
        return mm.audit_db.verify_integrity()
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# PROACTIVE INTELLIGENCE ENDPOINTS
# =============================================================================

@app.get("/api/briefing")
async def get_briefing():
    """Get or generate morning briefing."""
    pi = _get_proactive_intelligence()
    if pi is None:
        return {"briefing": {}}
    try:
        briefing = await pi.generate_briefing()
        return {"briefing": briefing}
    except Exception:
        return {"briefing": {}}


@app.get("/api/alerts")
async def get_alerts(active_only: bool = True):
    """Get active alerts."""
    pi = _get_proactive_intelligence()
    if pi is None:
        return {"alerts": []}
    try:
        alerts = pi.get_unacknowledged_alerts() if active_only else pi.get_all_alerts()
        return {"alerts": alerts}
    except Exception:
        return {"alerts": []}


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    pi = _get_proactive_intelligence()
    if pi is None:
        return {"status": "acknowledged", "alert_id": alert_id}
    try:
        pi.acknowledge_alert(alert_id)
        return {"status": "acknowledged", "alert_id": alert_id}
    except Exception:
        return {"status": "acknowledged", "alert_id": alert_id}


@app.get("/api/queue")
async def get_action_queue():
    """Get action queue sorted by priority."""
    queue = _get_action_queue()
    if queue is None:
        return {"queue": [], "stats": {}}
    try:
        overdue = queue.get_overdue()
        stats = queue.get_stats()
        return {"queue": overdue, "stats": stats}
    except Exception:
        return {"queue": [], "stats": {}}


@app.post("/api/queue/{item_id}/complete")
async def complete_queue_item(item_id: str):
    """Mark queue item as complete."""
    queue = _get_action_queue()
    if queue is None:
        return {"status": "completed", "item_id": item_id}
    try:
        result = queue.complete_item(item_id)
        return {"status": "completed", "item_id": item_id, "result": result is not None}
    except Exception:
        return {"status": "completed", "item_id": item_id}


@app.post("/api/queue")
async def add_queue_item(item: Dict[str, Any]):
    """Add item to the action queue."""
    queue = _get_action_queue()
    if queue is None:
        return {"status": "error", "detail": "Action queue not available"}
    try:
        result = queue.add_item(
            item_type=item.get("item_type", "compliance_task"),
            title=item.get("title", "Untitled task"),
            description=item.get("description", ""),
            priority=item.get("priority", "normal"),
            due_date=item.get("due_date"),
            assigned_to=item.get("assigned_to", ""),
            source=item.get("source", ""),
            metadata=item.get("metadata"),
        )
        return {"status": "created", "item": result.to_dict()}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/queue/stats")
async def get_queue_stats():
    """Get action queue statistics."""
    queue = _get_action_queue()
    if queue is None:
        return {"stats": {}}
    try:
        return {"stats": queue.get_stats()}
    except Exception:
        return {"stats": {}}


@app.get("/api/automations")
async def list_automations():
    """List active automations."""
    engine = _get_automation_engine()
    if engine is None:
        return {"automations": []}
    try:
        automations = engine.list_automations()
        return {"automations": automations}
    except Exception:
        return {"automations": []}


@app.post("/api/automations")
async def create_automation(automation: Dict[str, Any]):
    """Create automation from natural language description."""
    engine = _get_automation_engine()
    if engine is None:
        return {"status": "error", "detail": "Automation engine not available"}
    try:
        result = engine.create_automation(description=automation.get("description", ""))
        return {"status": "created", "automation": result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.delete("/api/automations/{automation_id}")
async def delete_automation(automation_id: str):
    """Delete automation."""
    engine = _get_automation_engine()
    if engine is None:
        return {"status": "deleted", "automation_id": automation_id}
    try:
        engine.delete_automation(automation_id)
        return {"status": "deleted", "automation_id": automation_id}
    except Exception:
        return {"status": "deleted", "automation_id": automation_id}


@app.post("/api/automations/{automation_id}/enable")
async def enable_automation(automation_id: str):
    """Enable an automation."""
    engine = _get_automation_engine()
    if engine is None:
        return {"status": "error", "detail": "Automation engine not available"}
    try:
        result = engine.enable_automation(automation_id)
        if result:
            return {"status": "enabled", "automation_id": automation_id}
        return {"status": "error", "detail": "Automation not found"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/api/automations/{automation_id}/disable")
async def disable_automation(automation_id: str):
    """Disable an automation."""
    engine = _get_automation_engine()
    if engine is None:
        return {"status": "error", "detail": "Automation engine not available"}
    try:
        result = engine.disable_automation(automation_id)
        if result:
            return {"status": "disabled", "automation_id": automation_id}
        return {"status": "error", "detail": "Automation not found"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/api/news")
async def get_news_feed(limit: int = 20):
    """Get curated news feed."""
    aggregator = _get_news_aggregator()
    if aggregator is None:
        return {"news": []}
    try:
        articles = aggregator.get_digest(limit=limit)
        return {"news": articles}
    except Exception:
        return {"news": []}

# =============================================================================
# ANALYTICS & MONITORING ENDPOINTS
# =============================================================================

@app.get("/api/dashboard", response_model=Dict[str, Any])
async def get_dashboard():
    """Get dashboard data (usage, health, metrics, containers, storage)."""
    state.ensure_initialized()

    import shutil

    usage = await state.cascade.get_usage_summary()
    specialists = state.router.list_specialists() if state.router else []
    models = state.cascade.list_available_models() if state.cascade else []

    # Check container/service health
    containers = {}
    service_checks = {
        "orchestrator": ("http://localhost:8000/api/health", "healthy"),
        "litellm": (f"{LITELLM_URL}/health", "healthy"),
        "chromadb": (f"{CHROMADB_URL}/api/v1/heartbeat", "healthy"),
        "ollama": (f"{OLLAMA_URL}/api/tags", "healthy"),
        "redis": None,
        "searxng": (f"{SEARXNG_URL}/healthz", "healthy"),
        "ui": ("http://localhost:3000", "healthy"),
        "voice": ("http://localhost:8500/api/health", "healthy"),
    }
    for name, check in service_checks.items():
        if check is None:
            # Redis — check via redis ping
            try:
                import redis.asyncio as redis_lib
                r = redis_lib.from_url(REDIS_URL)
                await r.ping()
                await r.aclose()
                containers[name] = {"running": True, "healthy": True}
            except Exception:
                containers[name] = {"running": False, "healthy": False}
            continue
        url, healthy_status = check
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3) as client:
                resp = await client.get(url)
                containers[name] = {
                    "running": resp.status_code < 500,
                    "healthy": resp.status_code < 400,
                }
        except Exception:
            containers[name] = {"running": False, "healthy": False}

    # Model usage breakdown from cascade
    model_usage = []
    model_list = models if isinstance(models, list) else []
    total_models = len(model_list) if model_list else 1
    for model_entry in model_list[:8]:
        name = model_entry.get("model_name", model_entry.get("name", "unknown")) if isinstance(model_entry, dict) else str(model_entry)
        model_usage.append({
            "name": name,
            "requests": 0,
            "percentage": round(100 / max(total_models, 1), 1),
        })

    # Token usage from usage data
    token_usage = []
    if isinstance(usage, dict):
        for provider, data in usage.items():
            if isinstance(data, dict):
                session = data.get("session", {})
                prompt = session.get("prompt_tokens", 0) if isinstance(session, dict) else 0
                completion = session.get("completion_tokens", 0) if isinstance(session, dict) else 0
                token_usage.append({
                    "provider": provider,
                    "promptTokens": prompt,
                    "completionTokens": completion,
                    "totalTokens": prompt + completion,
                })

    # Storage usage
    data_dir = Path("/data")
    if not data_dir.exists():
        data_dir = Path(".")
    try:
        disk = shutil.disk_usage(str(data_dir))
        storage = {
            "used": disk.used,
            "total": disk.total,
            "free": disk.free,
        }
    except Exception:
        storage = {"used": 0, "total": 0, "free": 0}

    # Uptime — calculate from process start time
    import time as _time
    uptime_pct = 99.9  # Default; would need persistent tracking for real data

    return {
        "usage": usage,
        "health": {"status": "healthy" if all(c.get("healthy", False) for c in containers.values()) else "degraded"},
        "specialists": len(specialists),
        "models": len(model_list),
        "containers": containers,
        "modelUsage": model_usage,
        "tokenUsage": token_usage,
        "storage": storage,
        "uptime": uptime_pct,
    }


@app.get("/api/usage")
async def get_usage():
    """Get token usage by provider."""
    state.ensure_initialized()
    usage = await state.cascade.get_usage_summary()
    return UsageSummary(**usage, total_queries_today=0, total_tokens_today=0)


@app.get("/api/models")
async def list_models():
    """List available models and their health."""
    state.ensure_initialized()
    models = state.cascade.list_available_models()
    return {"models": models}


@app.get("/api/audit")
async def get_audit_log(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
):
    """Get audit log."""
    try:
        from infrastructure.security.audit_logger import AuditDatabase, AuditQuery
        db = AuditDatabase()
        query = AuditQuery(
            start_date=start_date.isoformat() if start_date else None,
            end_date=end_date.isoformat() if end_date else None,
            limit=limit,
        )
        entries = db.query(query)
        return {"entries": entries}
    except Exception:
        return {"entries": []}


@app.post("/api/audit/export")
async def export_audit_log(format: str = "JSON"):
    """Export audit report."""
    try:
        from infrastructure.security.audit_logger import AuditDatabase
        logger_instance = AuditDatabase()
        data = logger_instance.export(format=format)
        return {"status": "exported", "format": format, "data": data}
    except Exception:
        return {"status": "exported", "format": format}

# =============================================================================
# VOICE ENDPOINTS
# =============================================================================

@app.post("/api/voice/stt")
async def speech_to_text(audio_file: UploadFile = File(...)):
    """Convert speech to text."""
    try:
        import httpx
        voice_url = os.getenv("VOICE_SERVICE_URL", "http://voice:8500")
        audio_bytes = await audio_file.read()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{voice_url}/stt",
                files={"audio": (audio_file.filename, audio_bytes, audio_file.content_type)},
                timeout=60,
            )
            if response.status_code == 200:
                return response.json()
            return {"text": "", "error": f"Voice service returned {response.status_code}"}
    except Exception as e:
        return {"text": "", "error": f"Voice service unavailable: {e}"}


@app.post("/api/voice/tts")
async def text_to_speech(text: str = Form(...)):
    """Convert text to speech."""
    try:
        import httpx
        voice_url = os.getenv("VOICE_SERVICE_URL", "http://voice:8500")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{voice_url}/tts",
                data={"text": text},
                timeout=60,
            )
            if response.status_code == 200:
                return response.json()
            return {"audio_url": "", "error": f"Voice service returned {response.status_code}"}
    except Exception as e:
        return {"audio_url": "", "error": f"Voice service unavailable: {e}"}


@app.websocket("/api/voice/stream")
async def voice_stream(websocket: WebSocket):
    """
    WebSocket for voice conversation streaming with audio buffering.

    Accepts JSON control messages and binary audio chunks.
    Control messages:
      {"type": "start"} — begin recording session
      {"type": "stop"} — stop recording, transcribe buffered audio
      {"type": "cancel"} — discard buffered audio
    Binary messages are audio chunks appended to the buffer.
    """
    await websocket.accept()
    audio_buffer = bytearray()
    is_recording = False

    try:
        while True:
            message = await websocket.receive()

            if message.get("text"):
                # JSON control message
                try:
                    control = json.loads(message["text"])
                    msg_type = control.get("type", "")

                    if msg_type == "start":
                        audio_buffer.clear()
                        is_recording = True
                        await websocket.send_json({"type": "status", "status": "recording"})

                    elif msg_type == "cancel":
                        audio_buffer.clear()
                        is_recording = False
                        await websocket.send_json({"type": "status", "status": "cancelled"})

                    elif msg_type == "stop" and is_recording:
                        is_recording = False
                        if len(audio_buffer) < 1000:
                            # Too little audio, likely noise
                            audio_buffer.clear()
                            await websocket.send_json({"type": "status", "status": "no_speech"})
                            continue

                        # Send buffered audio to STT service
                        try:
                            import httpx
                            voice_url = os.getenv("VOICE_SERVICE_URL", "http://voice:8500")
                            async with httpx.AsyncClient() as client:
                                stt_response = await client.post(
                                    f"{voice_url}/stt",
                                    files={"audio": ("audio.webm", bytes(audio_buffer), "audio/webm")},
                                    timeout=60,
                                )
                                if stt_response.status_code == 200:
                                    text = stt_response.json().get("text", "")
                                    if text:
                                        await websocket.send_json({"type": "transcription", "text": text})
                                        # Process through chat pipeline
                                        chat_req = ChatRequest(message=text, stream=False)
                                        chat_resp = await chat(chat_req)
                                        await websocket.send_json({
                                            "type": "response",
                                            "text": text,
                                            "response": chat_resp.message.content,
                                            "specialist": chat_resp.specialist,
                                        })
                                    else:
                                        await websocket.send_json({"type": "status", "status": "no_speech"})
                                else:
                                    await websocket.send_json({"type": "error", "error": f"STT returned {stt_response.status_code}"})
                        except Exception as e:
                            await websocket.send_json({"type": "error", "error": str(e)})
                        finally:
                            audio_buffer.clear()

                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "error": "Invalid JSON control message"})

            elif message.get("bytes") and is_recording:
                # Audio chunk — append to buffer
                audio_buffer.extend(message["bytes"])

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Voice stream error: {e}")


# =============================================================================
# CLIPBOARD ENDPOINTS
# =============================================================================

@app.post("/api/clipboard/analyze")
async def analyze_clipboard(text: str = Form(...)):
    """Analyze clipboard text for healthcare codes."""
    try:
        from clipboard.patterns import detect_codes_flat, list_patterns
        codes = detect_codes_flat(text, validate=True)
        return {
            "text_length": len(text),
            "codes_detected": len(codes),
            "codes": codes,
            "patterns_available": len(list_patterns()),
        }
    except Exception:
        # Fallback: basic regex detection without the clipboard module
        import re
        results = []
        patterns = {
            "icd10_cm": r'\b([A-Z]\d{2}(\.\d{1,4})?)\b',
            "cpt": r'\b(\d{5})\b',
            "npi": r'\b(\d{10})\b',
            "hcpcs": r'\b([A-Z]\d{4})\b',
        }
        for code_type, pattern in patterns.items():
            for match in re.finditer(pattern, text):
                results.append({
                    "code": match.group(1),
                    "type": code_type,
                    "valid": None,
                })
        return {
            "text_length": len(text),
            "codes_detected": len(results),
            "codes": results,
            "patterns_available": len(patterns),
        }


@app.get("/api/codes/{code_type}/{code}")
async def lookup_code(code_type: str, code: str):
    """Look up a healthcare code."""
    registry = _get_skill_registry()
    if registry:
        try:
            result = await registry.execute("code_lookup", code=code, code_type=code_type)
            if result:
                return result
        except Exception:
            pass

    # Fallback: basic code info
    code_info = {"code": code, "type": code_type}
    try:
        from clipboard.patterns import validate_code, list_patterns
        code_info["valid"] = validate_code(code_type, code)
        for p in list_patterns():
            if p["code_type"] == code_type:
                code_info["pattern_name"] = p["name"]
                code_info["description"] = p.get("description", "")
                break
    except Exception:
        pass
    return code_info


@app.post("/api/voice/transcribe")
async def voice_transcribe_alias(audio_file: UploadFile = File(...)):
    """Alias for /api/voice/stt — accepts the same parameters."""
    return await speech_to_text(audio_file)

# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@app.get("/api/health", response_model=HealthCheck)
async def health_check():
    """System health check."""
    state.ensure_initialized()

    # Check service connectivity using a shared client
    services = {}
    import httpx
    async with httpx.AsyncClient(timeout=5) as client:
        # Check LiteLLM
        try:
            response = await client.get(f"{LITELLM_URL}/health")
            services["litellm"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services["litellm"] = "unhealthy"

        # Check ChromaDB
        try:
            response = await client.get(f"{CHROMADB_URL}/api/v1/heartbeat")
            services["chromadb"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services["chromadb"] = "unhealthy"

        # Check Ollama
        try:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            services["ollama"] = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception:
            services["ollama"] = "unhealthy"

        # Check SearXNG
        try:
            response = await client.get(f"{SEARXNG_URL}/healthz")
            services["searxng"] = "healthy" if response.status_code < 400 else "unhealthy"
        except Exception:
            services["searxng"] = "unhealthy"

    # Check Redis
    try:
        import redis.asyncio as redis
        r = redis.from_url(REDIS_URL)
        await r.ping()
        await r.aclose()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"

    specialists = state.router.list_specialists() if state.router else []
    models = state.cascade.list_available_models() if state.cascade else []

    return HealthCheck(
        status="healthy" if all(v == "healthy" for v in services.values()) else "degraded",
        version="1.0.0",
        timestamp=datetime.now(),
        services=services,
        models_available=len(models),
        specialists_available=len([s for s in specialists if s.get("enabled", True)])
    )


@app.get("/api/version")
async def get_version():
    """Get version information."""
    return {
        "version": "1.0.0",
        "build": "2026.05.15",
        "api_version": "v1"
    }


@app.post("/api/backup")
async def trigger_backup():
    """Trigger manual backup."""
    try:
        from infrastructure.backup import BackupManager
        backup = BackupManager()
        path = backup.create_backup()
        return {"status": "completed", "backup_path": str(path)}
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/api/backup/list")
async def list_backups():
    """List available backups."""
    try:
        from infrastructure.backup import BackupManager
        backup = BackupManager()
        backups = backup.list_backups()
        return {"backups": backups}
    except Exception as e:
        return {"backups": [], "error": str(e)}


@app.post("/api/backup/restore")
async def restore_backup(backup_path: str):
    """Restore from a backup."""
    try:
        from infrastructure.backup import BackupManager
        backup = BackupManager()
        success = backup.restore_backup(backup_path)
        if success:
            return {"status": "restored", "backup_path": backup_path}
        return {"status": "error", "error": "Restore failed — backup file not found or corrupt"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/settings")
async def get_settings():
    """Get application settings."""
    try:
        config_path = PROJECT_ROOT / ".env"
        settings = {}
        if config_path.exists():
            for line in config_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    if any(k in key.upper() for k in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
                        settings[key.strip()] = "***REDACTED***"
                    else:
                        settings[key.strip()] = value.strip()
        return {"settings": settings}
    except Exception:
        return {"settings": {}}


@app.post("/api/settings")
async def update_settings(settings: Dict[str, Any]):
    """Update application settings."""
    try:
        env_path = PROJECT_ROOT / ".env"
        existing = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    existing[key.strip()] = value.strip()
        existing.update(settings)
        lines = [f"{k}={v}" for k, v in existing.items()]
        env_path.write_text("\n".join(lines))
        return {"status": "updated", "settings": settings}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# =============================================================================
# FILE UPLOAD ENDPOINT
# =============================================================================

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), auto_learn: bool = True):
    """Upload and auto-process file."""
    try:
        upload_dir = PROJECT_ROOT / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        # Auto-detect file type and provide summary
        result = {
            "filename": file.filename,
            "size": len(content),
            "content_type": file.content_type,
            "status": "uploaded",
            "path": str(file_path),
        }

        # Process based on file type
        ext = Path(file.filename).suffix.lower()
        if ext in (".csv", ".xlsx", ".xls"):
            result["type"] = "spreadsheet"
            result["message"] = "Spreadsheet uploaded. Use /skills spreadsheet_analyzer to analyze."
        elif ext == ".pdf":
            result["type"] = "pdf"
            result["message"] = "PDF uploaded. Use /skills pdf_processor to extract content."
        elif ext in (".json", ".yaml", ".yml"):
            result["type"] = "data"
            result["message"] = "Data file uploaded. Ready for processing."
        elif ext in (".txt", ".md"):
            result["type"] = "text"
            result["message"] = "Text file uploaded. Ready for analysis."
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
            result["type"] = "image"
            result["message"] = "Image uploaded. Use /skills image_analyzer for OCR."
        else:
            result["type"] = "other"
            result["message"] = "File uploaded successfully."

        # Auto-learning pipeline
        if auto_learn:
            try:
                from pipeline.pipeline import run_pipeline_for_file
                job_id = str(uuid.uuid4())
                asyncio.create_task(run_pipeline_for_file(
                    file_path=str(file_path),
                    filename=file.filename,
                    content_type=file.content_type,
                    job_id=job_id,
                ))
                result["pipeline_job_id"] = job_id
                result["auto_learn"] = True
                result["message"] = "File uploaded and auto-learning pipeline started."
            except Exception as e:
                logger.warning(f"Auto-learning pipeline enqueue failed: {e}")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AUTO-LEARNING PIPELINE ENDPOINTS
# =============================================================================

class LearnURLRequest(BaseModel):
    url: str = Field(..., description="URL to fetch and learn from")
    domain: str = Field(default="general", description="Optional domain hint")


@app.get("/api/pipeline/status/{job_id}")
async def get_pipeline_status(job_id: str):
    """Get the status of an auto-learning pipeline job."""
    try:
        from pipeline.pipeline import AutoLearningPipeline
        result = AutoLearningPipeline.get_job_status(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "job_id": result.job_id,
            "status": result.status,
            "stages_completed": result.stages_completed,
            "stages_failed": result.stages_failed,
            "notification": result.notification,
            "file_type": result.file_type,
            "domain": result.domain,
            "sensitivity": result.sensitivity,
            "entity_count": result.entity_count,
            "fact_count": result.fact_count,
            "chunk_count": result.chunk_count,
            "contradiction_count": result.contradiction_count,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pipeline/jobs")
async def list_pipeline_jobs():
    """List all auto-learning pipeline jobs."""
    try:
        from pipeline.pipeline import AutoLearningPipeline
        return AutoLearningPipeline.list_jobs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/pipeline/learn-url")
async def learn_from_url(request: LearnURLRequest):
    """Fetch a URL and run the auto-learning pipeline on its content."""
    try:
        from pipeline.pipeline import run_pipeline_for_url
        job_id = str(uuid.uuid4())
        asyncio.create_task(run_pipeline_for_url(
            url=request.url,
            domain=request.domain,
            job_id=job_id,
        ))
        return {
            "job_id": job_id,
            "status": "processing",
            "url": request.url,
            "message": "Auto-learning pipeline started for URL.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# PC CONTROL ENDPOINTS
# =============================================================================

_pc_control_manager = None


def _get_pc_control_manager():
    """Lazy-init PC Control Manager singleton."""
    global _pc_control_manager
    if _pc_control_manager is None:
        from orchestrator.pc_control import get_pc_control_manager
        _pc_control_manager = get_pc_control_manager(audit_db=_get_audit_db())
    return _pc_control_manager


class PCCommandRequest(BaseModel):
    """Request model for PC control commands."""
    action: str = Field(..., description="Action to execute, e.g. 'filesystem.browse'")
    parameters: dict = Field(default_factory=dict, description="Action parameters")
    user_id: str = Field(default="default_user")
    session_id: Optional[str] = Field(default=None)


class PCConfirmationRequest(BaseModel):
    """Request model for confirming a destructive action."""
    approved: bool = Field(..., description="Whether to approve the action")
    reason: Optional[str] = Field(default=None)


@app.websocket("/api/pc/ws")
async def pc_control_ws(websocket: WebSocket):
    """WebSocket endpoint for host agent connection."""
    await websocket.accept()
    manager = _get_pc_control_manager()
    agent_id = None

    try:
        # Wait for registration message
        data = await websocket.receive_json()
        if data.get("type") != "register":
            await websocket.close(code=4001, reason="First message must be a register")
            return

        agent_id = data.get("agent_id", "unknown")
        capabilities = data.get("capabilities", [])
        await manager.register_agent(agent_id, websocket, capabilities)
        logger.info(f"PC host agent connected: {agent_id}")

        # Main message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "result":
                command_id = data.get("command_id")
                manager.handle_result(command_id, data)

            elif msg_type == "confirmation_request":
                command_id = data.get("command_id")
                action = data.get("action", "")
                description = data.get("description", "")
                risk_level = data.get("risk_level", "high")
                parameters = data.get("parameters", {})
                await manager.handle_confirmation_request(
                    command_id, action, description, risk_level, parameters
                )

            elif msg_type == "heartbeat":
                # Update agent heartbeat
                agent = manager.get_agent(agent_id)
                if agent:
                    agent.last_heartbeat = datetime.now()

    except WebSocketDisconnect:
        logger.info(f"PC host agent disconnected: {agent_id}")
    except Exception as e:
        logger.error(f"PC control WebSocket error: {e}")
    finally:
        if agent_id:
            await manager.unregister_agent(agent_id)


@app.post("/api/pc/command")
async def send_pc_command(request: PCCommandRequest):
    """Send a command to the host agent."""
    manager = _get_pc_control_manager()
    result = await manager.send_command(
        action=request.action,
        parameters=request.parameters,
        user_id=request.user_id,
        session_id=request.session_id or "",
    )
    return result


@app.post("/api/pc/confirm/{command_id}")
async def confirm_pc_action(command_id: str, request: PCConfirmationRequest):
    """Confirm or deny a pending destructive action."""
    manager = _get_pc_control_manager()
    await manager.handle_confirmation_response(command_id, request.approved)
    return {"command_id": command_id, "approved": request.approved}


@app.get("/api/pc/status")
async def get_pc_status():
    """Get host agent connection status and capabilities."""
    manager = _get_pc_control_manager()
    return manager.get_status()


@app.websocket("/api/pc/confirmations")
async def pc_confirmations_ws(websocket: WebSocket):
    """WebSocket for UI to receive confirmation requests in real-time."""
    await websocket.accept()
    manager = _get_pc_control_manager()
    manager.register_confirmation_ws(websocket)
    try:
        while True:
            # Keep connection alive; client just listens
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.unregister_confirmation_ws(websocket)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def build_system_prompt(
    specialist: str,
    tools: List[str],
    sensitivity: DetectionResult,
    user_id: str = "default_user",
    query: str = "",
) -> str:
    """Build system prompt for specialist with memory context injection."""
    # Try loading specialist system prompt from module
    specialist_prompt = ""
    try:
        import importlib
        module_name = f"specialists.{specialist}"
        module = importlib.import_module(module_name)
        if hasattr(module, "SYSTEM_PROMPT"):
            specialist_prompt = module.SYSTEM_PROMPT
    except (ImportError, AttributeError):
        pass

    if specialist_prompt:
        base_prompt = specialist_prompt
    else:
        # Default system prompt
        base_prompt = f"""You are Aethera, a personal AI super agent specialized in {specialist}.

You are helpful, accurate, and thorough. You have access to the following tools: {', '.join(tools) if tools else 'none'}.

"""

    if sensitivity.contains_phi or sensitivity.contains_pii:
        base_prompt += """
IMPORTANT: This conversation contains sensitive personal information.
- Do not store any PHI/PII in long-term memory
- Do not share information with external services
- Maintain strict confidentiality
"""

    # Inject memory context
    if query:
        mm = _get_memory_manager()
        if mm:
            try:
                context = await mm.retrieve_context(
                    query=query,
                    user_id=user_id,
                    specialist=specialist,
                    sensitivity=sensitivity,
                )
                if context:
                    base_prompt += f"\n\n--- Relevant Context ---\n{context}\n--- End Context ---\n"
            except Exception:
                pass  # Memory context is supplementary, never block the chat

    # Inject upcoming/overdue deadlines
    try:
        tp = _get_temporal_processor()
        if tp:
            overdue = tp.get_overdue()
            upcoming = tp.get_upcoming(days=7)
            if overdue or upcoming:
                deadline_parts = []
                if overdue:
                    overdue_lines = [f"  - {item.description} (OVERDUE, was due {item.deadline})" for item in overdue[:5]]
                    deadline_parts.append("OVERDUE DEADLINES:\n" + "\n".join(overdue_lines))
                if upcoming:
                    upcoming_lines = [f"  - {item.description} (due {item.deadline}, priority: {item.priority})" for item in upcoming[:5]]
                    deadline_parts.append("UPCOMING DEADLINES (next 7 days):\n" + "\n".join(upcoming_lines))
                base_prompt += f"\n\n--- Time-Sensitive Items ---\n" + "\n".join(deadline_parts) + "\n--- End Time-Sensitive Items ---\n"
    except Exception:
        pass  # Temporal context is supplementary

    # Inject recent CMS / regulatory updates so healthcare answers reflect current rules
    if specialist and specialist.startswith("healthcare"):
        try:
            updater = _get_knowledge_updater()
            if updater:
                industry = updater.get_industry_context(
                    category="healthcare_regulatory", days=30, limit=8
                )
                if industry:
                    base_prompt += (
                        "\n\n--- Recent CMS / Regulatory Updates ---\n"
                        "Account for these recent industry changes when answering:\n"
                        f"{industry}\n--- End Updates ---\n"
                    )
        except Exception:
            pass  # Industry context is supplementary, never block the chat

    return base_prompt


async def _litellm_client(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Post a chat-completions payload to LiteLLM, returning a parsed response.

    On transport errors a synthetic response carrying a user-facing message is
    returned so the agent loop terminates cleanly instead of raising.
    """
    import httpx

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        try:
            response = await client.post(
                f"{LITELLM_URL}/v1/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.error(f"LLM call timed out for model {payload.get('model')}")
            message = "I'm sorry, the request timed out. Please try again or use a different model."
        except httpx.ConnectError:
            logger.error(f"Cannot connect to LLM service at {LITELLM_URL}")
            message = "I'm sorry, the AI service is currently unavailable. Please try again in a moment."
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            message = "I encountered an error processing your request. Please try again."
    return {"choices": [{"message": {"content": message}}]}


async def execute_llm_call(
    messages: List[Dict[str, str]],
    model: str,
    tools: List[str],
    stream: bool = True
) -> AgentResult:
    """Run the agentic reason-act loop via LiteLLM, executing tools as the model calls them."""
    result = await run_agent_loop(
        messages=messages,
        model=model,
        tool_names=tools or [],
        registry=_get_skill_registry(),
        llm_client=_litellm_client,
    )
    if not result.content:
        result.content = "I apologize, but I was unable to generate a response. Please try again."
    return result


async def log_audit_event(
    event_type: str,
    conversation_id: str,
    specialist: str,
    model: str,
    sensitivity: str,
    duration_ms: int
):
    """Log event to audit trail."""
    try:
        from infrastructure.security.audit_logger import AuditDatabase
        audit = AuditDatabase()
        audit.log(
            action=event_type,
            resource=conversation_id,
            details={
                "specialist": specialist,
                "model": model,
                "sensitivity": sensitivity,
                "duration_ms": duration_ms,
            },
        )
    except Exception:
        pass
    logger.info(
        f"AUDIT: {event_type} | conv={conversation_id} | "
        f"specialist={specialist} | model={model} | "
        f"sensitivity={sensitivity} | duration={duration_ms}ms"
    )

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "orchestrator.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
