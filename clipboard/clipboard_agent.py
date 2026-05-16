"""
Aethera AI - Clipboard Agent

System tray clipboard monitor for healthcare code detection.
Uses pystray for system tray icon, monitors clipboard for healthcare
codes (ICD-10, CPT, HCPCS, NPI, NDC, LOINC), shows notifications,
and can send detected codes to Aethera API for analysis.
"""

import logging
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Dict, List, Optional

import requests

from clipboard.patterns import detect_codes, detect_codes_flat, list_patterns

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger("aethera.clipboard")

AETHERA_API_URL = os.getenv("AETHERA_API_URL", "http://localhost:8000")
POLL_INTERVAL = float(os.getenv("CLIPBOARD_POLL_INTERVAL", "1.5"))
NOTIFICATION_ENABLED = os.getenv("CLIPBOARD_NOTIFICATION", "true").lower() == "true"
SEND_TO_API = os.getenv("CLIPBOARD_SEND_TO_API", "false").lower() == "true"
MAX_CONTENT_LENGTH = int(os.getenv("CLIPBOARD_MAX_CONTENT", "5000"))
HISTORY_LIMIT = int(os.getenv("CLIPBOARD_HISTORY_LIMIT", "100"))

# ---------------------------------------------------------------------------
# Cross-platform clipboard access
# ---------------------------------------------------------------------------

class ClipboardReader:
    """
    Cross-platform clipboard reader.

    Windows: PowerShell Get-Clipboard
    Linux: xclip or xsel
    macOS: pbpaste
    Falls back to pyperclip if available.
    """

    def __init__(self):
        self._system = platform.system()
        self._method = self._detect_method()

    def _detect_method(self) -> str:
        """Detect the best clipboard access method."""
        # Try pyperclip first (most reliable)
        try:
            import pyperclip
            pyperclip.paste()  # Test read
            return "pyperclip"
        except (ImportError, pyperclip.PyperclipException):
            pass

        # Platform-specific fallbacks
        if self._system == "Windows":
            return "powershell"
        elif self._system == "Darwin":
            return "pbpaste"
        elif self._system == "Linux":
            # Check for xclip
            try:
                subprocess.run(["xclip", "-version"], capture_output=True, timeout=2)
                return "xclip"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
            # Check for xsel
            try:
                subprocess.run(["xsel", "--version"], capture_output=True, timeout=2)
                return "xsel"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

        return "none"

    def read(self) -> Optional[str]:
        """
        Read current clipboard content.

        Returns:
            Clipboard text or None if unavailable
        """
        try:
            if self._method == "pyperclip":
                import pyperclip
                return pyperclip.paste()

            elif self._method == "powershell":
                return self._read_powershell()

            elif self._method == "pbpaste":
                return self._read_pbpaste()

            elif self._method == "xclip":
                return self._read_xclip()

            elif self._method == "xsel":
                return self._read_xsel()

        except Exception as exc:
            logger.debug("Clipboard read error (%s): %s", self._method, exc)

        return None

    def _read_powershell(self) -> Optional[str]:
        """Read clipboard via PowerShell Get-Clipboard."""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
        return None

    def _read_pbpaste(self) -> Optional[str]:
        """Read clipboard via macOS pbpaste."""
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
        return None

    def _read_xclip(self) -> Optional[str]:
        """Read clipboard via Linux xclip."""
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
        return None

    def _read_xsel(self) -> Optional[str]:
        """Read clipboard via Linux xsel."""
        result = subprocess.run(
            ["xsel", "--clipboard", "--output"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()
        return None

    @property
    def method(self) -> str:
        return self._method


# ---------------------------------------------------------------------------
# Notification handler
# ---------------------------------------------------------------------------

class NotificationHandler:
    """
    Cross-platform notification display.

    Windows: Windows toast via win10toast or plyer
    macOS: osascript notification
    Linux: notify-send
    """

    def __init__(self):
        self._system = platform.system()
        self._method = self._detect_method()

    def _detect_method(self) -> str:
        if self._system == "Windows":
            try:
                from win10toast import ToastNotifier
                return "win10toast"
            except ImportError:
                try:
                    from plyer import notification
                    return "plyer"
                except ImportError:
                    return "powershell_notify"
        elif self._system == "Darwin":
            return "osascript"
        elif self._system == "Linux":
            try:
                subprocess.run(["notify-send", "--version"], capture_output=True, timeout=2)
                return "notify_send"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass
        return "none"

    def show(self, title: str, message: str, duration: int = 5) -> bool:
        """
        Display a desktop notification.

        Args:
            title: Notification title
            message: Notification body text
            duration: Display duration in seconds

        Returns:
            True if notification was shown successfully
        """
        if not NOTIFICATION_ENABLED:
            return False

        try:
            if self._method == "win10toast":
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                threading.Thread(
                    target=toaster.show_toast,
                    args=(title, message),
                    kwargs={"duration": duration, "threaded": True},
                    daemon=True,
                ).start()
                return True

            elif self._method == "plyer":
                from plyer import notification as plyer_notif
                plyer_notif.notify(title=title, message=message, timeout=duration)
                return True

            elif self._method == "powershell_notify":
                return self._notify_powershell(title, message)

            elif self._method == "osascript":
                return self._notify_osascript(title, message)

            elif self._method == "notify_send":
                return self._notify_send(title, message, duration)

        except Exception as exc:
            logger.warning("Notification error (%s): %s", self._method, exc)

        return False

    def _notify_powershell(self, title: str, message: str) -> bool:
        """Windows notification via PowerShell."""
        try:
            ps_script = (
                f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null;'
                f'$notify = New-Object System.Windows.Forms.NotifyIcon;'
                f'$notify.Icon = [System.Drawing.SystemIcons]::Information;'
                f'$notify.Visible = $true;'
                f'$notify.ShowBalloonTip(5000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info);'
                f'Start-Sleep -Seconds 6; $notify.Dispose()'
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                timeout=10,
            )
            return True
        except Exception:
            return False

    def _notify_osascript(self, title: str, message: str) -> bool:
        """macOS notification via osascript."""
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def _notify_send(self, title: str, message: str, duration: int) -> bool:
        """Linux notification via notify-send."""
        try:
            subprocess.run(
                ["notify-send", "-t", str(duration * 1000), title, message],
                capture_output=True,
                timeout=5,
            )
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Aethera API client
# ---------------------------------------------------------------------------

class AetheraAPIClient:
    """Client for sending detected codes to the Aethera API."""

    def __init__(self, base_url: str = AETHERA_API_URL):
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def send_detected_codes(self, codes: List[Dict], clipboard_content: str) -> Optional[Dict]:
        """
        Send detected healthcare codes to Aethera API for analysis.

        Args:
            codes: List of detected code dicts from patterns.detect_codes_flat
            clipboard_content: Original clipboard text

        Returns:
            API response dict or None on failure
        """
        payload = {
            "source": "clipboard_agent",
            "detected_codes": codes,
            "content_preview": clipboard_content[:500] if clipboard_content else "",
            "timestamp": datetime.now().isoformat(),
        }

        try:
            resp = self._session.post(
                f"{self.base_url}/api/clipboard/analyze",
                json=payload,
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.warning("Aethera API returned %d: %s", resp.status_code, resp.text[:200])
                return None
        except requests.RequestException as exc:
            logger.error("Aethera API request failed: %s", exc)
            return None

    def lookup_code(self, code_type: str, code: str) -> Optional[Dict]:
        """Look up a specific code via the Aethera API."""
        try:
            resp = self._session.get(
                f"{self.base_url}/api/codes/{code_type}/{code}",
                timeout=10,
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except requests.RequestException:
            return None


# ---------------------------------------------------------------------------
# Detection history
# ---------------------------------------------------------------------------

class DetectionHistory:
    """
    In-memory history of detected healthcare codes.
    Stores recent detections with timestamps and metadata.
    """

    def __init__(self, limit: int = HISTORY_LIMIT):
        self._limit = limit
        self._entries: List[Dict] = []

    def add(self, detected_codes: Dict, content: str, source: str = "clipboard"):
        """Add a detection event to history."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "source": source,
            "content_preview": content[:200] if content else "",
            "detected_codes": detected_codes,
            "code_count": sum(len(v) for v in detected_codes.values()) if isinstance(detected_codes, dict) else len(detected_codes),
        }

        self._entries.append(entry)

        # Trim to limit
        if len(self._entries) > self._limit:
            self._entries = self._entries[-self._limit:]

    def get_recent(self, count: int = 20) -> List[Dict]:
        """Get recent detection entries."""
        return self._entries[-count:]

    def get_by_type(self, code_type: str, count: int = 20) -> List[Dict]:
        """Get recent detections filtered by code type."""
        results = []
        for entry in reversed(self._entries):
            if code_type in entry.get("detected_codes", {}):
                results.append(entry)
                if len(results) >= count:
                    break
        return results

    def clear(self):
        """Clear detection history."""
        self._entries.clear()

    @property
    def count(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# Clipboard Monitor
# ---------------------------------------------------------------------------

class ClipboardMonitor:
    """
    Monitors the clipboard for healthcare code patterns.

    Runs in a background thread, polls the clipboard at a configurable
    interval, and triggers callbacks when healthcare codes are detected.
    """

    def __init__(
        self,
        poll_interval: float = POLL_INTERVAL,
        send_to_api: bool = SEND_TO_API,
    ):
        self.poll_interval = poll_interval
        self.send_to_api = send_to_api

        self._clipboard = ClipboardReader()
        self._notifications = NotificationHandler()
        self._api_client = AetheraAPIClient() if send_to_api else None
        self._history = DetectionHistory()

        self._last_content: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable] = []
        self._detection_count = 0

    def register_callback(self, callback: Callable):
        """
        Register a callback for detected codes.

        Callback signature: callback(detected_codes: Dict, content: str)
        """
        self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable):
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def start(self):
        """Start clipboard monitoring in a background thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

        logger.info(
            "Clipboard monitor started (method=%s, interval=%.1fs, api=%s)",
            self._clipboard.method, self.poll_interval, self.send_to_api,
        )

    def stop(self):
        """Stop clipboard monitoring."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("Clipboard monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop running in background thread."""
        while self._running:
            try:
                content = self._clipboard.read()

                if content and content != self._last_content and len(content) <= MAX_CONTENT_LENGTH:
                    self._last_content = content
                    self._process_content(content)

            except Exception as exc:
                logger.debug("Monitor loop error: %s", exc)

            time.sleep(self.poll_interval)

    def _process_content(self, content: str):
        """Process clipboard content for healthcare code detection."""
        detected = detect_codes(content, validate=True)

        if not detected:
            return

        self._detection_count += 1

        # Build flat list for notifications and API
        flat_codes = detect_codes_flat(content, validate=True)

        # Record in history
        self._history.add(detected, content)

        # Show notification
        code_types = list(detected.keys())
        code_count = sum(len(v) for v in detected.values())
        title = f"Aethera: Healthcare Codes Detected"
        body = f"Found {code_count} code(s): {', '.join(code_types[:5])}"
        if len(code_types) > 5:
            body += f" +{len(code_types) - 5} more"

        self._notifications.show(title, body)

        # Send to API
        if self._api_client and self.send_to_api:
            try:
                self._api_client.send_detected_codes(flat_codes, content)
            except Exception as exc:
                logger.debug("API send error: %s", exc)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(detected, content)
            except Exception as exc:
                logger.debug("Callback error: %s", exc)

        logger.info("Detected %d codes of %d types", code_count, len(code_types))

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def detection_count(self) -> int:
        return self._detection_count

    def get_history(self, count: int = 20) -> List[Dict]:
        """Get recent detection history."""
        return self._history.get_recent(count)

    def clear_history(self):
        """Clear detection history."""
        self._history.clear()


# ---------------------------------------------------------------------------
# System Tray Application
# ---------------------------------------------------------------------------

class ClipboardTrayApp:
    """
    System tray application for the clipboard agent.

    Provides:
    - System tray icon with Aethera branding
    - Right-click context menu for actions
    - Status indicator (monitoring active/inactive)
    - Quick access to detection history
    """

    def __init__(self, monitor: Optional[ClipboardMonitor] = None):
        self.monitor = monitor or ClipboardMonitor()
        self._icon = None
        self._running = False

    def _create_icon_image(self):
        """Create the system tray icon image."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create a simple icon: colored circle with "A" for Aethera
            size = 64
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Draw circle background
            draw.ellipse([4, 4, size - 4, size - 4], fill=(6, 182, 212), outline=(255, 255, 255, 200), width=2)

            # Draw "A" letter
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except (OSError, IOError):
                font = ImageFont.load_default()

            draw.text((18, 12), "A", fill=(255, 255, 255), font=font)

            return img

        except ImportError:
            # If PIL not available, create a minimal icon
            from PIL import Image
            img = Image.new("RGB", (64, 64), (6, 182, 212))
            return img

    def _get_menu(self):
        """Build the context menu."""
        import pystray

        status_text = "Monitoring: Active" if self.monitor.is_running else "Monitoring: Paused"
        count_text = f"Detections: {self.monitor.detection_count}"

        return pystray.Menu(
            pystray.MenuItem(status_text, self._toggle_monitoring),
            pystray.MenuItem(count_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Show Recent Detections", self._show_history),
            pystray.MenuItem("Clear History", self._clear_history),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Send Test to Aethera", self._send_test),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._quit),
        )

    def _toggle_monitoring(self, icon, item):
        """Toggle clipboard monitoring on/off."""
        if self.monitor.is_running:
            self.monitor.stop()
            icon.title = "Aethera Clipboard Agent (Paused)"
        else:
            self.monitor.start()
            icon.title = "Aethera Clipboard Agent"

    def _show_history(self, icon, item):
        """Show recent detections in a notification."""
        history = self.monitor.get_history(5)
        if not history:
            self._notify("No Detections Yet", "Copy some healthcare codes to get started!")
            return

        lines = []
        for entry in history:
            ts = entry["timestamp"][:19]
            types = ", ".join(entry.get("detected_codes", {}).keys())
            lines.append(f"{ts}: {types}")

        self._notify("Recent Detections", "\n".join(lines))

    def _clear_history(self, icon, item):
        """Clear detection history."""
        self.monitor.clear_history()
        self._notify("History Cleared", "Detection history has been cleared.")

    def _send_test(self, icon, item):
        """Send a test detection to Aethera API."""
        try:
            client = AetheraAPIClient()
            resp = client.send_detected_codes(
                [{"code": "TEST", "type": "test", "valid": True, "name": "Test Code"}],
                "Test clipboard content from agent",
            )
            if resp:
                self._notify("Test Sent", "Successfully sent test to Aethera API")
            else:
                self._notify("Test Failed", "Could not reach Aethera API")
        except Exception as exc:
            self._notify("Test Error", str(exc)[:100])

    def _quit(self, icon, item):
        """Quit the application."""
        self.monitor.stop()
        self._running = False
        icon.stop()

    def _notify(self, title: str, message: str):
        """Show a notification."""
        notifications = NotificationHandler()
        notifications.show(title, message)

    def run(self):
        """Run the system tray application."""
        try:
            import pystray
        except ImportError:
            logger.error("pystray is required for system tray. Install with: pip install pystray")
            # Fall back to headless mode
            self._run_headless()
            return

        self._running = True
        self.monitor.start()

        icon_image = self._create_icon_image()
        self._icon = pystray.Icon(
            name="aethera_clipboard",
            icon=icon_image,
            title="Aethera Clipboard Agent",
            menu=self._get_menu,
        )

        logger.info("Starting Aethera Clipboard Agent system tray app")
        self._icon.run()

    def _run_headless(self):
        """Run without system tray (headless / service mode)."""
        self._running = True
        self.monitor.start()
        logger.info("Running Aethera Clipboard Agent in headless mode")

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.monitor.stop()
            self._running = False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Main entry point for the clipboard agent."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = ClipboardTrayApp()
    app.run()


if __name__ == "__main__":
    main()