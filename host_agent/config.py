"""
Aethera AI — Host Agent Configuration
Reads environment variables for orchestrator connection and agent identity.
"""
import os

# Orchestrator connection
ORCHESTRATOR_URL = os.getenv("AETHERA_ORCHESTRATOR_URL", "ws://localhost:8000/api/pc/ws")
ORCHESTRATOR_HTTP_URL = os.getenv("AETHERA_ORCHESTRATOR_HTTP_URL", "http://localhost:8000")

# Agent identity
AGENT_ID = os.getenv("AETHERA_AGENT_ID", "host-agent-1")
HOSTNAME = os.getenv("COMPUTERNAME", "unknown")
PLATFORM = "windows"

# Capabilities — which handlers are enabled
ENABLED_CAPABILITIES = os.getenv(
    "AETHERA_CAPABILITIES",
    "filesystem,app_launcher,shell_executor,screen_capture,clipboard,system_monitor,browser",
).split(",")

# Confirmation timeout (seconds)
CONFIRMATION_TIMEOUT = int(os.getenv("AETHERA_CONFIRMATION_TIMEOUT", "60"))

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = int(os.getenv("AETHERA_HEARTBEAT_INTERVAL", "15"))

# Reconnect settings
RECONNECT_DELAY_INITIAL = float(os.getenv("AETHERA_RECONNECT_DELAY", "1"))
RECONNECT_DELAY_MAX = float(os.getenv("AETHERA_RECONNECT_MAX_DELAY", "30"))
MAX_RECONNECT_ATTEMPTS = int(os.getenv("AETHERA_MAX_RECONNECT", "100"))

# Shell execution
SHELL_TIMEOUT = int(os.getenv("AETHERA_SHELL_TIMEOUT", "30"))
SHELL_SAFE_COMMANDS = set(os.getenv(
    "AETHERA_SHELL_SAFE_COMMANDS",
    "dir,ls,type,cat,echo,set,get,whoami,hostname,ipconfig,ping,tracert,netstat,systeminfo,"
    "tasklist,wmic,where,findstr,find,tree,ver",
).split(","))

# Screen capture
SCREENSHOT_DIR = os.getenv("AETHERA_SCREENSHOT_DIR", "")

# Browser automation
BROWSER_HEADLESS = os.getenv("AETHERA_BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("AETHERER_BROWSER_TIMEOUT", "30"))

# File system limits
MAX_FILE_SIZE = int(os.getenv("AETHERA_MAX_FILE_SIZE", str(5 * 1024 * 1024)))  # 5MB
MAX_DIRECTORY_DEPTH = int(os.getenv("AETHERA_MAX_DIR_DEPTH", "10"))

# Audit
AUDIT_ENABLED = os.getenv("AETHERA_AUDIT_ENABLED", "true").lower() == "true"