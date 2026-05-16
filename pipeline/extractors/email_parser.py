"""
Aethera AI — Email Parser
Extracts text and metadata from EML and MSG email files.
"""
import email
import logging
from email.policy import default as default_policy
from typing import Dict, Any

logger = logging.getLogger("aethera.pipeline.email_parser")


def extract_eml(file_path: str) -> Dict[str, Any]:
    """
    Extract text and metadata from an EML email file.

    Returns:
        Dict with text, metadata, success
    """
    result = {"text": "", "metadata": {}, "success": False}

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            msg = email.message_from_file(f, policy=default_policy)

        # Extract headers
        result["metadata"] = {
            "from": str(msg.get("From", "")),
            "to": str(msg.get("To", "")),
            "cc": str(msg.get("Cc", "")),
            "subject": str(msg.get("Subject", "")),
            "date": str(msg.get("Date", "")),
        }

        # Extract body text
        text_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        text_parts.append(part.get_content())
                    except Exception:
                        pass
        else:
            try:
                text_parts.append(msg.get_content())
            except Exception:
                pass

        result["text"] = "\n\n".join(str(p) for p in text_parts if p)
        result["success"] = True

    except Exception as e:
        logger.error(f"EML extraction failed: {e}")
        result["error"] = str(e)

    return result


def extract_msg(file_path: str) -> Dict[str, Any]:
    """
    Extract text and metadata from an MSG (Outlook) email file.

    Requires the extract-msg package. Falls back to binary header parsing if unavailable.

    Returns:
        Dict with text, metadata, success
    """
    result = {"text": "", "metadata": {}, "success": False}

    try:
        import extract_msg
        msg = extract_msg.Message(file_path)
        result["metadata"] = {
            "from": msg.sender or "",
            "to": msg.to or "",
            "cc": msg.cc or "",
            "subject": msg.subject or "",
            "date": str(msg.date) if msg.date else "",
        }
        result["text"] = msg.body or ""
        result["success"] = True
    except ImportError:
        # Fallback: try reading as raw text
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(50000)
            result["text"] = content
            result["metadata"]["warning"] = "extract-msg not installed; raw text extraction only"
            result["success"] = True
        except Exception as e:
            result["error"] = f"MSG extraction failed: {e}"
    except Exception as e:
        logger.error(f"MSG extraction failed: {e}")
        result["error"] = str(e)

    return result