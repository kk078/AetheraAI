"""
Aethera AI - Translator Skill

Multi-language translation via the orchestrator's LLM endpoint (LiteLLM proxy).
Supports: translate text, detect language, list supported languages.
Uses the LLM for actual translation; language detection uses a lightweight
heuristic combined with LLM confirmation when available.
"""

import json
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional

from skills.skill_base import AetheraSkill, SkillResult, skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")
DEFAULT_MODEL = os.getenv("AETHERA_TRANSLATE_MODEL", "aethera-cloud-balanced")

# ---------------------------------------------------------------------------
# Supported languages (ISO 639-1 code -> display name)
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES: Dict[str, str] = {
    "af": "Afrikaans", "ar": "Arabic", "az": "Azerbaijani", "be": "Belarusian",
    "bg": "Bulgarian", "bn": "Bengali", "ca": "Catalan", "cs": "Czech",
    "cy": "Welsh", "da": "Danish", "de": "German", "el": "Greek",
    "en": "English", "eo": "Esperanto", "es": "Spanish", "et": "Estonian",
    "eu": "Basque", "fa": "Persian", "fi": "Finnish", "fr": "French",
    "ga": "Irish", "gl": "Galician", "gu": "Gujarati", "he": "Hebrew",
    "hi": "Hindi", "hr": "Croatian", "ht": "Haitian Creole", "hu": "Hungarian",
    "hy": "Armenian", "id": "Indonesian", "is": "Icelandic", "it": "Italian",
    "ja": "Japanese", "ka": "Georgian", "kk": "Kazakh", "km": "Khmer",
    "kn": "Kannada", "ko": "Korean", "ku": "Kurdish", "ky": "Kyrgyz",
    "la": "Latin", "lo": "Lao", "lt": "Lithuanian", "lv": "Latvian",
    "mk": "Macedonian", "ml": "Malayalam", "mn": "Mongolian", "mr": "Marathi",
    "ms": "Malay", "mt": "Maltese", "my": "Burmese", "ne": "Nepali",
    "nl": "Dutch", "no": "Norwegian", "pa": "Punjabi", "pl": "Polish",
    "ps": "Pashto", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "rw": "Kinyarwanda", "si": "Sinhala", "sk": "Slovak", "sl": "Slovenian",
    "sq": "Albanian", "sr": "Serbian", "sv": "Swedish", "sw": "Swahili",
    "ta": "Tamil", "te": "Telugu", "tg": "Tajik", "th": "Thai",
    "tk": "Turkmen", "tl": "Tagalog", "tr": "Turkish", "uk": "Ukrainian",
    "ur": "Urdu", "uz": "Uzbek", "vi": "Vietnamese", "yo": "Yoruba",
    "zh": "Chinese", "zu": "Zulu",
}

# ---------------------------------------------------------------------------
# Lightweight language detection heuristics
# ---------------------------------------------------------------------------
SCRIPT_RANGES: List[Dict[str, Any]] = [
    {"range": (0x0400, 0x04FF), "lang": "ru", "name": "Cyrillic"},
    {"range": (0x0530, 0x058F), "lang": "hy", "name": "Armenian"},
    {"range": (0x0590, 0x05FF), "lang": "he", "name": "Hebrew"},
    {"range": (0x0600, 0x06FF), "lang": "ar", "name": "Arabic"},
    {"range": (0x0900, 0x097F), "lang": "hi", "name": "Devanagari"},
    {"range": (0x0980, 0x09FF), "lang": "bn", "name": "Bengali"},
    {"range": (0x0A00, 0x0A7F), "lang": "gu", "name": "Gujarati"},
    {"range": (0x0A80, 0x0AFF), "lang": "pa", "name": "Gurmukhi"},
    {"range": (0x0B00, 0x0B7F), "lang": "ta", "name": "Tamil"},
    {"range": (0x0B80, 0x0BFF), "lang": "ta", "name": "Tamil extended"},
    {"range": (0x0C00, 0x0C7F), "lang": "te", "name": "Telugu"},
    {"range": (0x0C80, 0x0CFF), "lang": "kn", "name": "Kannada"},
    {"range": (0x0D00, 0x0D7F), "lang": "ml", "name": "Malayalam"},
    {"range": (0x0E00, 0x0E7F), "lang": "th", "name": "Thai"},
    {"range": (0x0E80, 0x0EFF), "lang": "lo", "name": "Lao"},
    {"range": (0x1000, 0x109F), "lang": "my", "name": "Myanmar"},
    {"range": (0x10A0, 0x10FF), "lang": "ka", "name": "Georgian"},
    {"range": (0x3040, 0x309F), "lang": "ja", "name": "Hiragana/Katakana"},
    {"range": (0x30A0, 0x30FF), "lang": "ja", "name": "Katakana"},
    {"range": (0x4E00, 0x9FFF), "lang": "zh", "name": "CJK Unified Ideographs"},
    {"range": (0xAC00, 0xD7AF), "lang": "ko", "name": "Hangul Syllables"},
]


@skill(name="translator", category="general")
class TranslatorSkill(AetheraSkill):
    """
    Translate text between languages using the orchestrator's LLM endpoint.
    Detect source language and list supported languages.
    """

    @property
    def name(self) -> str:
        return "translator"

    @property
    def description(self) -> str:
        return "Translate text between languages, detect language, and list supported languages via LLM"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["translate", "detect_language", "list_languages"],
                    "description": (
                        "'translate' to translate text, "
                        "'detect_language' to identify the language of text, "
                        "'list_languages' to show supported languages"
                    ),
                },
                "text": {
                    "type": "string",
                    "description": "Text to translate or detect language for"
                },
                "source_language": {
                    "type": "string",
                    "description": (
                        "Source language code (e.g. 'en', 'es', 'fr'). "
                        "If not provided for translate, the LLM will auto-detect."
                    ),
                },
                "target_language": {
                    "type": "string",
                    "description": "Target language code for translation (e.g. 'en', 'es', 'fr')"
                },
                "model": {
                    "type": "string",
                    "description": "LLM model to use for translation. Defaults to aethera-cloud-balanced.",
                },
                "preserve_formatting": {
                    "type": "boolean",
                    "description": "Attempt to preserve original formatting, markdown, and structure.",
                    "default": True,
                },
                "filter": {
                    "type": "string",
                    "description": "Optional filter for list_languages: search by language name or code"
                },
            },
            "required": ["action"],
        }

    @property
    def examples(self) -> list:
        return [
            {"input": {"action": "translate", "text": "Hello, how are you?", "target_language": "es"}},
            {"input": {"action": "detect_language", "text": "Bonjour, comment allez-vous?"}},
            {"input": {"action": "list_languages", "filter": "spa"}},
        ]

    @property
    def cache_ttl(self) -> int:
        return 600  # Cache translations for 10 minutes

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, **kwargs) -> SkillResult:
        action = kwargs.get("action", "")

        try:
            if action == "translate":
                return await self._translate(kwargs)
            elif action == "detect_language":
                return self._detect_language(kwargs)
            elif action == "list_languages":
                return self._list_languages(kwargs)
            else:
                return SkillResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            logger.exception("Translator error")
            return SkillResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # Translate
    # ------------------------------------------------------------------

    async def _translate(self, kwargs: dict) -> SkillResult:
        text = kwargs.get("text", "")
        source_lang = kwargs.get("source_language", "")
        target_lang = kwargs.get("target_language", "")
        model = kwargs.get("model", DEFAULT_MODEL)
        preserve_formatting = kwargs.get("preserve_formatting", True)

        if not text:
            return SkillResult(success=False, error="'text' is required for translate action")
        if not target_lang:
            return SkillResult(success=False, error="'target_language' is required for translate action")

        # Validate language codes
        if source_lang and source_lang not in SUPPORTED_LANGUAGES:
            return SkillResult(
                success=False,
                error=f"Unsupported source language code: {source_lang}. Use list_languages to see options."
            )
        if target_lang not in SUPPORTED_LANGUAGES:
            return SkillResult(
                success=False,
                error=f"Unsupported target language code: {target_lang}. Use list_languages to see options."
            )

        source_name = SUPPORTED_LANGUAGES.get(source_lang, "auto-detected")
        target_name = SUPPORTED_LANGUAGES[target_lang]

        # Build system prompt
        system_prompt = (
            f"You are a professional translator. Translate the following text "
            f"from {source_name} to {target_name}. "
            f"Provide ONLY the translated text, nothing else. "
        )
        if preserve_formatting:
            system_prompt += (
                "Preserve all original formatting, markdown syntax, line breaks, "
                "and structural elements exactly as they appear in the source. "
            )

        # Build user message
        if source_lang:
            user_message = text
        else:
            user_message = text

        # Call LLM
        translated = await self._call_llm(system_prompt, user_message, model)

        if translated is None:
            return SkillResult(success=False, error="Translation failed: LLM call unsuccessful")

        return SkillResult(
            success=True,
            data={
                "original_text": text,
                "translated_text": translated,
                "source_language": source_lang or "auto",
                "target_language": target_lang,
                "source_language_name": source_name,
                "target_language_name": target_name,
                "model": model,
            }
        )

    # ------------------------------------------------------------------
    # Detect language
    # ------------------------------------------------------------------

    def _detect_language(self, kwargs: dict) -> SkillResult:
        text = kwargs.get("text", "")

        if not text:
            return SkillResult(success=False, error="'text' is required for detect_language action")

        # Phase 1: Script-based heuristic detection
        heuristic_result = self._heuristic_detect(text)

        # Phase 2: Word-pattern heuristics for Latin-script languages
        if heuristic_result["code"] == "en" or heuristic_result["confidence"] == "low":
            pattern_result = self._pattern_detect(text)
            if pattern_result["confidence"] == "high":
                heuristic_result = pattern_result

        return SkillResult(
            success=True,
            data={
                "detected_language": heuristic_result["code"],
                "language_name": heuristic_result["name"],
                "confidence": heuristic_result["confidence"],
                "method": heuristic_result.get("method", "heuristic"),
                "text_sample": text[:200],
            }
        )

    # ------------------------------------------------------------------
    # List languages
    # ------------------------------------------------------------------

    def _list_languages(self, kwargs: dict) -> SkillResult:
        filter_text = kwargs.get("filter", "").lower()

        languages = [
            {"code": code, "name": name}
            for code, name in sorted(SUPPORTED_LANGUAGES.items(), key=lambda x: x[1])
        ]

        if filter_text:
            languages = [
                lang for lang in languages
                if filter_text in lang["code"] or filter_text in lang["name"].lower()
            ]

        return SkillResult(
            success=True,
            data={
                "languages": languages,
                "total": len(languages),
            }
        )

    # ------------------------------------------------------------------
    # Heuristic language detection
    # ------------------------------------------------------------------

    @staticmethod
    def _heuristic_detect(text: str) -> Dict[str, Any]:
        """Detect language by examining Unicode script ranges."""
        script_counts: Dict[str, int] = {}

        for char in text:
            cp = ord(char)
            if cp < 0x0080:  # ASCII — skip for script detection
                continue
            for entry in SCRIPT_RANGES:
                lo, hi = entry["range"]
                if lo <= cp <= hi:
                    key = entry["lang"]
                    script_counts[key] = script_counts.get(key, 0) + 1
                    break

        if not script_counts:
            # All ASCII — default to English with low confidence
            return {
                "code": "en",
                "name": SUPPORTED_LANGUAGES.get("en", "English"),
                "confidence": "low",
                "method": "default_ascii",
            }

        # Pick the script with the most characters
        best_code = max(script_counts, key=script_counts.get)  # type: ignore[arg-type]
        total_non_ascii = sum(script_counts.values())
        ratio = script_counts[best_code] / total_non_ascii if total_non_ascii else 0

        confidence = "high" if ratio > 0.8 else "medium" if ratio > 0.5 else "low"

        return {
            "code": best_code,
            "name": SUPPORTED_LANGUAGES.get(best_code, best_code),
            "confidence": confidence,
            "method": "script_detection",
        }

    @staticmethod
    def _pattern_detect(text: str) -> Dict[str, Any]:
        """
        Simple word-pattern detection for common Latin-script languages.
        Returns best-guess code and confidence.
        """
        lower = text.lower()
        patterns: Dict[str, List[str]] = {
            "es": ["el ", "la ", "los ", "las ", "de ", "en ", "que ", "por ", "para ", "con ", "una ", "uno ", "usted"],
            "fr": ["le ", "la ", "les ", "de ", "un ", "une ", "du ", "des ", "est ", "que ", "pour ", "dans ", "avec ", "pas "],
            "de": ["der ", "die ", "das ", "und ", "ist ", "ein ", "eine ", "nicht ", "mit ", "auf ", "fur ", "aus "],
            "it": ["il ", "la ", "le ", "lo ", "gli ", "di ", "che ", "un ", "una ", "per ", "con ", "non ", "del "],
            "pt": ["o ", "a ", "os ", "as ", "de ", "um ", "uma ", "que ", "para ", "com ", "não ", "do ", "da "],
            "nl": ["de ", "het ", "een ", "van ", "en ", "dat ", "met ", "voor ", "niet ", "op ", "te ", "aan "],
        }

        scores: Dict[str, int] = {}
        for lang_code, words in patterns.items():
            score = sum(1 for w in words if w in lower)
            scores[lang_code] = score

        if not scores or max(scores.values()) == 0:
            return {"code": "en", "name": "English", "confidence": "low", "method": "word_patterns"}

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        confidence = "high" if scores[best] >= 4 else "medium" if scores[best] >= 2 else "low"

        return {
            "code": best,
            "name": SUPPORTED_LANGUAGES.get(best, best),
            "confidence": confidence,
            "method": "word_patterns",
        }

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    async def _call_llm(self, system_prompt: str, user_message: str, model: str) -> Optional[str]:
        """
        Call the LLM via the LiteLLM proxy for translation.
        Returns the assistant's response text, or None on failure.
        """
        try:
            import httpx

            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.3,  # Low temperature for precise translation
                "max_tokens": 4096,
                "stream": False,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{LITELLM_URL}/v1/chat/completions",
                    json=payload,
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except ImportError:
            logger.error("httpx is required for LLM calls. Install with: pip install httpx")
            return None
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return None