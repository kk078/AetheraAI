"""
Aethera AI — Host Agent
Native Windows process that connects to the orchestrator via WebSocket,
receives PC control commands, and executes them locally with safety gates.

Usage:
    python -m host_agent.agent
    python host_agent/agent.py
"""
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, InvalidHandshake
except ImportError:
    print("ERROR: websockets package required. Install with: pip install websockets")
    sys.exit(1)

from .config import (
    ORCHESTRATOR_URL,
    AGENT_ID,
    HOSTNAME,
    PLATFORM,
    ENABLED_CAPABILITIES,
    HEARTBEAT_INTERVAL,
    RECONNECT_DELAY_INITIAL,
    RECONNECT_DELAY_MAX,
    MAX_RECONNECT_ATTEMPTS,
    AUDIT_ENABLED,
)
from .safety import SafetyGate, RiskLevel
from .handlers import get_handler

logger = logging.getLogger("aethera.host_agent")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


class HostAgent:
    """
    WebSocket client that connects to the orchestrator,
    dispatches commands to handlers, and manages confirmations.
    """

    def __init__(self):
        self.agent_id = AGENT_ID
        self.ws = None
        self.connected = False
        self.safety = SafetyGate()
        self.pending_confirmations: dict = {}  # command_id -> asyncio.Future
        self.capabilities = [c.strip() for c in ENABLED_CAPABILITIES if c.strip()]
        self._heartbeat_task = None
        self._reconnect_delay = RECONNECT_DELAY_INITIAL

    async def start(self):
        """Main entry point: connect to orchestrator and run."""
        logger.info(f"Host Agent {self.agent_id} starting (capabilities: {self.capabilities})")
        attempts = 0
        while attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                async with websockets.connect(
                    ORCHESTRATOR_URL,
                    ping_interval=20,
                    ping_timeout=10,
                    max_size=10 * 1024 * 1024,  # 10MB for screenshots
                ) as ws:
                    self.ws = ws
                    self.connected = True
                    self._reconnect_delay = RECONNECT_DELAY_INITIAL
                    attempts = 0

                    # Register with orchestrator
                    await self._register()

                    # Start heartbeat
                    self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

                    # Listen for messages
                    async for message in ws:
                        try:
                            data = json.loads(message)
                            await self._handle_message(data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON received: {e}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")

            except (ConnectionClosed, InvalidHandshake, ConnectionRefusedError, OSError) as e:
                self.connected = False
                if self._heartbeat_task:
                    self._heartbeat_task.cancel()
                attempts += 1
                logger.warning(f"Connection lost (attempt {attempts}/{MAX_RECONNECT_ATTEMPTS}): {e}")
                if attempts >= MAX_RECONNECT_ATTEMPTS:
                    logger.error("Max reconnect attempts reached. Giving up.")
                    break
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, RECONNECT_DELAY_MAX)

        logger.info("Host Agent shut down.")

    async def _register(self):
        """Send registration message to orchestrator."""
        msg = {
            "type": "register",
            "agent_id": self.agent_id,
            "hostname": HOSTNAME,
            "platform": PLATFORM,
            "capabilities": self.capabilities,
            "version": "1.0.0",
        }
        await self.ws.send(json.dumps(msg))
        logger.info(f"Registered agent {self.agent_id} with orchestrator")

    async def _heartbeat_loop(self):
        """Periodically send heartbeat with system stats."""
        while True:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not self.connected:
                    break
                stats = await self._get_basic_stats()
                msg = {
                    "type": "heartbeat",
                    "agent_id": self.agent_id,
                    "status": "online",
                    "capabilities": self.capabilities,
                    "system": stats,
                }
                await self.ws.send(json.dumps(msg))
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                break

    async def _get_basic_stats(self) -> dict:
        """Get basic system stats for heartbeat."""
        try:
            import psutil
            return {
                "cpu": psutil.cpu_percent(interval=0),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage("/").percent if os.name != "nt" else psutil.disk_usage("C:\\").percent,
            }
        except Exception:
            return {"cpu": 0, "memory": 0, "disk": 0}

    async def _handle_message(self, data: dict):
        """Route incoming messages to the appropriate handler."""
        msg_type = data.get("type", "")

        if msg_type == "command":
            await self._handle_command(data)
        elif msg_type == "confirmation_response":
            await self._handle_confirmation_response(data)
        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_command(self, data: dict):
        """Execute a command after safety checks."""
        command_id = data.get("command_id", str(uuid.uuid4()))
        action = data.get("action", "")
        parameters = data.get("parameters", {})
        user_id = data.get("user_id", "default_user")
        session_id = data.get("session_id", "")

        # Classify the action
        decision = self.safety.classify(action, parameters)

        # If confirmation is required, request it
        if decision.requires_confirmation:
            confirmation_msg = {
                "type": "confirmation_request",
                "command_id": command_id,
                "action": action,
                "description": decision.description,
                "risk_level": decision.risk_level.value,
                "parameters": parameters,
                "timeout_seconds": decision.timeout_seconds,
            }
            await self.ws.send(json.dumps(confirmation_msg))

            # Wait for confirmation
            future = asyncio.get_event_loop().create_future()
            self.pending_confirmations[command_id] = future
            try:
                approved = await asyncio.wait_for(future, timeout=decision.timeout_seconds)
                if not approved:
                    await self._send_result(command_id, action, False, None, "User denied the action", user_id, session_id, decision)
                    return
            except asyncio.TimeoutError:
                await self._send_result(command_id, action, False, None, "Confirmation timed out", user_id, session_id, decision)
                return
            finally:
                self.pending_confirmations.pop(command_id, None)

        # Execute the command
        await self._execute_command(command_id, action, parameters, user_id, session_id, decision)

    async def _handle_confirmation_response(self, data: dict):
        """Handle a confirmation response from the UI."""
        command_id = data.get("command_id", "")
        approved = data.get("approved", False)
        future = self.pending_confirmations.get(command_id)
        if future and not future.done():
            future.set_result(approved)

    async def _execute_command(self, command_id: str, action: str, parameters: dict,
                               user_id: str, session_id: str, decision):
        """Execute a command using the appropriate handler."""
        handler = get_handler(action)
        if handler is None:
            await self._send_result(command_id, action, False, None, f"No handler for action: {action}", user_id, session_id, decision)
            return

        try:
            result = await handler.handle(action, parameters)
            success = result.get("success", False)
            data = result.get("data", result)
            error = result.get("error") if not success else None
            await self._send_result(command_id, action, success, data, error, user_id, session_id, decision)
        except Exception as e:
            logger.error(f"Handler error for {action}: {e}", exc_info=True)
            await self._send_result(command_id, action, False, None, str(e), user_id, session_id, decision)

    async def _send_result(self, command_id: str, action: str, success: bool,
                           data, error, user_id: str, session_id: str, decision=None):
        """Send a result message back to the orchestrator."""
        result = {
            "type": "result",
            "command_id": command_id,
            "action": action,
            "success": success,
            "data": data,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        # Include audit info
        if AUDIT_ENABLED:
            audit_data = {
                "user_id": user_id,
                "action": f"pc_control.{action}",
                "resource": str(data)[:200] if data else action,
                "details": json.dumps({
                    "command_id": command_id,
                    "success": success,
                    "error": error,
                    "risk_level": decision.risk_level.value if decision else "unknown",
                    "requires_confirmation": decision.requires_confirmation if decision else False,
                    "hostname": HOSTNAME,
                    "agent_id": self.agent_id,
                }),
                "session_id": session_id,
            }
            result["audit"] = audit_data

        await self.ws.send(json.dumps(result))


async def main():
    """Entry point for running the host agent."""
    agent = HostAgent()
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())