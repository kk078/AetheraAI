"""
Aethera AI — PC Control Manager
Orchestrator-side module that manages WebSocket relay between
the UI and host agents, handles confirmation workflows,
and logs all PC control actions to the audit trail.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("aethera.pc_control")


class HostAgentConnection:
    """Represents a connected host agent."""
    def __init__(self, agent_id: str, websocket: WebSocket, capabilities: List[str]):
        self.agent_id = agent_id
        self.websocket = websocket
        self.capabilities = capabilities
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()


class PCControlManager:
    """
    Manages host agent connections and command relay.

    - Maintains a registry of connected host agents
    - Routes commands from UI to the appropriate host agent
    - Manages confirmation workflows for destructive actions
    - Logs all actions to the audit trail
    """

    def __init__(self, audit_db=None):
        self.agents: Dict[str, HostAgentConnection] = {}
        self.pending_commands: Dict[str, asyncio.Future] = {}
        self.pending_confirmations: Dict[str, dict] = {}
        self.confirmation_ws_clients: List[WebSocket] = []
        self.audit_db = audit_db

    # --- Agent Management ---

    async def register_agent(self, agent_id: str, websocket: WebSocket, capabilities: List[str]):
        """Register a new host agent connection."""
        conn = HostAgentConnection(agent_id, websocket, capabilities)
        self.agents[agent_id] = conn
        logger.info(f"Host agent registered: {agent_id} (capabilities: {capabilities})")

    async def unregister_agent(self, agent_id: str):
        """Unregister a disconnected host agent."""
        self.agents.pop(agent_id, None)
        logger.info(f"Host agent unregistered: {agent_id}")

    def get_agent(self, agent_id: str) -> Optional[HostAgentConnection]:
        """Get a specific host agent by ID."""
        return self.agents.get(agent_id)

    def get_first_available_agent(self) -> Optional[HostAgentConnection]:
        """Get the first available host agent."""
        for agent in self.agents.values():
            return agent
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get status of all connected agents."""
        return {
            "agents": {
                aid: {
                    "capabilities": conn.capabilities,
                    "connected_at": conn.connected_at.isoformat(),
                    "last_heartbeat": conn.last_heartbeat.isoformat(),
                }
                for aid, conn in self.agents.items()
            },
            "pending_commands": len(self.pending_commands),
            "pending_confirmations": len(self.pending_confirmations),
            "total_agents": len(self.agents),
        }

    # --- Command Routing ---

    async def send_command(self, action: str, parameters: dict,
                           user_id: str = "default_user", session_id: str = "") -> dict:
        """
        Send a command to the host agent and wait for the result.

        Returns the result dict from the host agent, or an error dict if no agent is available.
        """
        agent = self.get_first_available_agent()
        if agent is None:
            return {"success": False, "error": "No host agent connected"}

        command_id = str(uuid.uuid4())
        msg = {
            "type": "command",
            "command_id": command_id,
            "action": action,
            "parameters": parameters,
            "requires_confirmation": False,  # Host agent determines this
            "user_id": user_id,
            "session_id": session_id,
        }

        # Create a Future to wait for the result
        future = asyncio.get_event_loop().create_future()
        self.pending_commands[command_id] = future

        try:
            await agent.websocket.send_json(msg)
            # Wait for result with timeout (120s for long-running commands)
            result = await asyncio.wait_for(future, timeout=120.0)

            # Log to audit trail
            if self.audit_db:
                await self._log_audit(action, result, user_id, session_id)

            return result
        except asyncio.TimeoutError:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.pending_commands.pop(command_id, None)

    async def handle_result(self, command_id: str, result: dict):
        """Handle a result message from a host agent."""
        future = self.pending_commands.get(command_id)
        if future and not future.done():
            future.set_result(result)

    # --- Confirmation Workflow ---

    async def handle_confirmation_request(self, command_id: str, action: str,
                                            description: str, risk_level: str,
                                            parameters: dict):
        """
        Relay a confirmation request from the host agent to the UI.

        Stores the request and pushes it to all connected confirmation WebSocket clients.
        """
        confirmation = {
            "command_id": command_id,
            "action": action,
            "description": description,
            "risk_level": risk_level,
            "parameters": parameters,
            "timestamp": datetime.now().isoformat(),
        }
        self.pending_confirmations[command_id] = confirmation

        # Push to all connected confirmation WebSocket clients
        msg = json.dumps({"type": "confirmation_request", **confirmation})
        disconnected = []
        for ws in self.confirmation_ws_clients:
            try:
                await ws.send_text(msg)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.confirmation_ws_clients.remove(ws)

    async def handle_confirmation_response(self, command_id: str, approved: bool):
        """Handle a confirmation response from the UI."""
        confirmation = self.pending_confirmations.pop(command_id, None)
        if confirmation is None:
            logger.warning(f"Confirmation response for unknown command: {command_id}")
            return

        # Relay to the host agent
        agent = self.get_first_available_agent()
        if agent:
            msg = {
                "type": "confirmation_response",
                "command_id": command_id,
                "approved": approved,
            }
            try:
                await agent.websocket.send_json(msg)
            except Exception as e:
                logger.error(f"Failed to send confirmation response: {e}")

        # Log the confirmation decision
        if self.audit_db:
            action = f"pc_control.confirmation.{'approved' if approved else 'denied'}"
            await self._log_audit(action, {"command_id": command_id, "approved": approved}, "default_user", "")

    async def register_confirmation_ws(self, websocket: WebSocket):
        """Register a WebSocket client for confirmation notifications."""
        self.confirmation_ws_clients.append(websocket)

    def unregister_confirmation_ws(self, websocket: WebSocket):
        """Unregister a confirmation WebSocket client."""
        if websocket in self.confirmation_ws_clients:
            self.confirmation_ws_clients.remove(websocket)

    # --- Audit ---

    async def _log_audit(self, action: str, data: dict, user_id: str, session_id: str):
        """Log an action to the audit trail."""
        if self.audit_db:
            try:
                self.audit_db.log(
                    action=action,
                    resource=data.get("action", action),
                    details=json.dumps(data, default=str),
                    user_id=user_id,
                    session_id=session_id,
                )
            except Exception as e:
                logger.error(f"Audit log error: {e}")


# Module-level singleton
_pc_control_manager: Optional[PCControlManager] = None


def get_pc_control_manager(audit_db=None) -> PCControlManager:
    """Get or create the PCControlManager singleton."""
    global _pc_control_manager
    if _pc_control_manager is None:
        _pc_control_manager = PCControlManager(audit_db=audit_db)
    return _pc_control_manager