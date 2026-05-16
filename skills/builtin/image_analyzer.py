"""
Aethera AI - Image Analyzer Skill

Analyze images: extract metadata, perform OCR, and read basic image properties.
Supports common formats (PNG, JPEG, GIF, BMP, TIFF, WebP) via Pillow.
Falls back gracefully when pytesseract is not installed.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

logger = logging.getLogger(__name__)


@skill(name="image_analyzer", category="general")
class ImageAnalyzerSkill(AetheraSkill):
    """
    Analyze images: metadata, OCR text extraction, and basic properties.
    """

    @property
    def name(self) -> str:
        return "image_analyzer"

    @property
    def description(self) -> str:
        return "Analyze images: extract metadata, perform OCR, and read basic image properties"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["analyze", "ocr", "metadata"],
                    "description": (
                        "Action to perform: 'analyze' for full analysis, "
                        "'ocr' for text extraction only, "
                        "'metadata' for image metadata only"
                    )
                },
                "image_path": {
                    "type": "string",
                    "description": "Absolute path to the image file"
                },
                "ocr_language": {
                    "type": "string",
                    "description": "Language for OCR (e.g. 'eng', 'spa', 'fra'). Default is 'eng'.",
                    "default": "eng"
                },
                "include_exif": {
                    "type": "boolean",
                    "description": "Whether to include EXIF data in metadata output.",
                    "default": True
                }
            },
            "required": ["action", "image_path"]
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "analyze", "image_path": "/path/to/photo.jpg"}},
            {"input": {"action": "ocr", "image_path": "/path/to/scan.png", "ocr_language": "eng"}},
            {"input": {"action": "metadata", "image_path": "/path/to/image.tiff", "include_exif": True}},
        ]

    @property
    def cache_ttl(self) -> int:
        return 300  # Cache results for 5 minutes

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "analyze")
        image_path = kwargs.get("image_path", "")
        ocr_language = kwargs.get("ocr_language", "eng")
        include_exif = kwargs.get("include_exif", True)

        if not image_path:
            return SkillResult(success=False, error="image_path is required")

        path = Path(image_path)
        if not path.exists():
            return SkillResult(success=False, error=f"Image file not found: {image_path}")
        if not path.is_file():
            return SkillResult(success=False, error=f"Path is not a file: {image_path}")

        try:
            from PIL import Image
        except ImportError:
            return SkillResult(
                success=False,
                error="Pillow is required for image analysis. Install with: pip install Pillow"
            )

        try:
            img = Image.open(path)
            img.load()  # Force full load to catch corrupt files early

            if action == "metadata":
                result = self._extract_metadata(img, path, include_exif)
            elif action == "ocr":
                result = self._extract_text(img, ocr_language)
            elif action == "analyze":
                metadata = self._extract_metadata(img, path, include_exif)
                ocr_result = self._extract_text(img, ocr_language)
                result = {
                    "metadata": metadata,
                    "ocr": ocr_result,
                }
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")

            return SkillResult(success=True, data=result)

        except Exception as e:
            logger.exception("Image analysis failed for %s", image_path)
            return SkillResult(success=False, error=f"Image analysis failed: {e}")

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def _extract_metadata(self, img, path: Path, include_exif: bool) -> Dict[str, Any]:
        """Return basic image properties and optional EXIF data."""
        file_stat = path.stat()

        metadata: Dict[str, Any] = {
            "file": {
                "name": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": file_stat.st_size,
                "size_human": self._human_size(file_stat.st_size),
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            },
            "image": {
                "format": img.format,
                "mode": img.mode,
                "width": img.width,
                "height": img.height,
                "resolution_ppi": None,
                "is_animated": getattr(img, "is_animated", False),
                "n_frames": getattr(img, "n_frames", 1),
            },
        }

        # Resolution (DPI) — may be None for images without DPI info
        dpi = img.info.get("dpi")
        if dpi and len(dpi) == 2:
            metadata["image"]["resolution_ppi"] = {"x": dpi[0], "y": dpi[1]}

        # Color palette info for palette-mode images
        if img.mode == "P":
            palette = img.getpalette()
            if palette:
                metadata["image"]["palette_colors"] = len(palette) // 3

        # Transparency
        if "transparency" in img.info:
            metadata["image"]["transparency"] = img.info["transparency"]

        # EXIF data
        if include_exif:
            metadata["exif"] = self._read_exif(img)

        return metadata

    def _read_exif(self, img) -> Dict[str, Any]:
        """Read EXIF tags safely; returns empty dict if unavailable."""
        exif_data: Dict[str, Any] = {}
        try:
            from PIL.ExifTags import TAGS, GPSTAGS

            raw_exif = img._getexif()  # noqa: SLF001 — Pillow's standard method
            if raw_exif is None:
                return exif_data

            for tag_id, value in raw_exif.items():
                tag_name = TAGS.get(tag_id, f"Tag_{tag_id}")
                # GPS sub-IFD
                if tag_name == "GPSInfo":
                    gps = {}
                    for gps_id in value:
                        gps_name = GPSTAGS.get(gps_id, f"GPS_{gps_id}")
                        gps[gps_name] = self._serializable(value[gps_id])
                    exif_data[tag_name] = gps
                else:
                    exif_data[tag_name] = self._serializable(value)
        except Exception:
            # _getexif() may raise AttributeError or other errors on formats without EXIF
            pass

        return exif_data

    # ------------------------------------------------------------------
    # OCR
    # ------------------------------------------------------------------

    def _extract_text(self, img, language: str) -> Dict[str, Any]:
        """
        Extract text from image using pytesseract.
        Returns structured result with availability flag so callers can
        handle the case where pytesseract is not installed.
        """
        try:
            import pytesseract  # noqa: F811

            # Pre-process: convert to a format pytesseract handles well
            if img.mode not in ("RGB", "L"):
                work_img = img.convert("RGB")
            else:
                work_img = img

            text = pytesseract.image_to_string(work_img, lang=language)
            data = pytesseract.image_to_data(work_img, lang=language, output_type=pytesseract.Output.DICT)

            # Compute per-word confidence stats
            confidences = [
                int(c) for c in data.get("conf", []) if int(c) > 0
            ]
            avg_confidence = (
                round(sum(confidences) / len(confidences), 2)
                if confidences
                else 0
            )

            # Extract unique detected words (non-empty text entries)
            words = [t.strip() for t in data.get("text", []) if t.strip()]
            word_count = len(words)

            return {
                "available": True,
                "text": text.strip(),
                "language": language,
                "word_count": word_count,
                "confidence": avg_confidence,
            }

        except ImportError:
            return {
                "available": False,
                "text": "",
                "language": language,
                "word_count": 0,
                "confidence": 0,
                "error": (
                    "pytesseract is not installed. Install with: "
                    "pip install pytesseract and ensure Tesseract OCR binary is on PATH"
                ),
            }
        except pytesseract.TesseractNotFoundError:
            return {
                "available": False,
                "text": "",
                "language": language,
                "word_count": 0,
                "confidence": 0,
                "error": (
                    "Tesseract OCR binary not found on PATH. "
                    "Install Tesseract for your OS and add it to PATH."
                ),
            }
        except Exception as e:
            return {
                "available": False,
                "text": "",
                "language": language,
                "word_count": 0,
                "confidence": 0,
                "error": f"OCR failed: {e}",
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Return a human-readable file size string."""
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if abs(size_bytes) < 1024:
                return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} {unit}"
            size_bytes /= 1024  # type: ignore[assignment]
        return f"{size_bytes:.1f} PB"

    @staticmethod
    def _serializable(value: Any) -> Any:
        """Ensure value is JSON-serializable (bytes -> int, etc.)."""
        if isinstance(value, bytes):
            # Convert byte strings to a hex representation
            return value.hex()
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)