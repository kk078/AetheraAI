"""
Aethera AI — Screen Capture Handler
Take screenshots and extract text via OCR.
"""
import base64
import io
import os
import tempfile
from typing import Dict, Any

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


class ScreenCaptureHandler:
    """Handles screenshot and OCR operations."""

    async def handle(self, action: str, parameters: dict) -> Dict[str, Any]:
        dispatch = {
            "screen.capture": self.capture,
            "screen.ocr": self.ocr,
        }
        handler = dispatch.get(action)
        if handler is None:
            return {"success": False, "error": f"Unknown action: {action}"}
        try:
            return await handler(parameters)
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def capture(self, params: dict) -> Dict[str, Any]:
        """Take a screenshot and return it as base64."""
        if not HAS_PYAUTOGUI:
            return {"success": False, "error": "pyautogui not installed"}

        region = params.get("region")  # [x, y, width, height]
        include_base64 = params.get("include_base64", True)
        include_ocr = params.get("include_ocr", False)

        try:
            if region and len(region) == 4:
                screenshot = pyautogui.screenshot(region=tuple(region))
            else:
                screenshot = pyautogui.screenshot()

            # Convert to base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format="PNG", optimize=True)
            img_bytes = buffer.getvalue()
            img_b64 = base64.b64encode(img_bytes).decode("utf-8")

            result = {
                "success": True,
                "data": {
                    "width": screenshot.width,
                    "height": screenshot.height,
                    "size_bytes": len(img_bytes),
                    "region": region,
                },
            }

            if include_base64:
                result["data"]["base64"] = img_b64

            if include_ocr and HAS_TESSERACT:
                text = pytesseract.image_to_string(screenshot)
                result["data"]["ocr_text"] = text.strip()

            return result

        except Exception as e:
            return {"success": False, "error": f"Screenshot failed: {e}"}

    async def ocr(self, params: dict) -> Dict[str, Any]:
        """Take a screenshot and extract text via OCR."""
        if not HAS_TESSERACT:
            return {"success": False, "error": "pytesseract not installed. Install Tesseract OCR and pytesseract."}

        # First capture the screen
        capture_result = await self.capture({"include_base64": False, "include_ocr": False, **params})
        if not capture_result.get("success"):
            return capture_result

        # Then run OCR on the screenshot
        try:
            if HAS_PYAUTOGUI:
                screenshot = pyautogui.screenshot()
                text = pytesseract.image_to_string(screenshot)
            else:
                return {"success": False, "error": "pyautogui not available for screenshot"}

            return {
                "success": True,
                "data": {
                    "text": text.strip(),
                    "region": params.get("region"),
                    "width": capture_result["data"].get("width"),
                    "height": capture_result["data"].get("height"),
                },
            }
        except Exception as e:
            return {"success": False, "error": f"OCR failed: {e}"}