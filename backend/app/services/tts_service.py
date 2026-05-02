"""Offline TTS service using Windows SAPI via pyttsx3.

Generates speech audio as WAV bytes in a background thread (pyttsx3 requires
its own thread due to COM apartment restrictions on Windows).  Falls back
gracefully on non-Windows platforms.
"""
from __future__ import annotations

import logging
import platform
import re
import tempfile
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Preferred female voice name fragments (checked in order)
_FEMALE_VOICE_PREFS = [
    "zira",   # Microsoft Zira Desktop – US English female
    "hazel",  # Microsoft Hazel Desktop – GB English female
    "susan",  # alternate
    "aria",   # Microsoft Aria (newer Windows)
    "jenny",  # Microsoft Jenny
]

_tts_lock = threading.Lock()


def _strip_symbols(text: str) -> str:
    """Remove markdown and special chars that sound bad when spoken aloud."""
    # Remove markdown bold/italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # Remove markdown headers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bullet/numbered list markers
    text = re.sub(r"^\s*[-*+•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    # Remove code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove internal tags like [CONFIRM_ACTION:...]
    text = re.sub(r"\[[A-Z_]+:[^\]]+\]", "", text)
    # Remove lone special symbols
    text = re.sub(r"[*#_~`^|<>{}\\]", "", text)
    # Collapse multiple spaces/newlines
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", ", ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _normalize_for_speech(text: str) -> str:
    """Shape text for more natural rhythm and intonation in SAPI voices."""
    # Expand common abbreviations/acronyms that sound clipped otherwise.
    text = re.sub(r"\bAOJ\b", "A O J", text, flags=re.IGNORECASE)
    text = re.sub(r"\bETA\b", "E T A", text, flags=re.IGNORECASE)

    # Punctuation tuning for pauses.
    text = text.replace(";", ", ")
    text = text.replace(":", ". ")
    text = re.sub(r"\s*-\s*", ", ", text)
    text = re.sub(r"\.{3,}", ".", text)

    # Ensure sentence endings are clean for intonation.
    text = re.sub(r"([a-zA-Z0-9])\s+([A-Z])", r"\1. \2", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _find_female_voice(engine) -> str | None:
    """Return the voice ID of the best available female voice, or None."""
    voices = engine.getProperty("voices")
    # Prefer exact matches to known female voice names
    for pref in _FEMALE_VOICE_PREFS:
        for v in voices:
            if pref in v.name.lower():
                return v.id
    # Fall back to any voice with "female" in gender attribute (some SAPI versions)
    for v in voices:
        gender = getattr(v, "gender", "") or ""
        if "female" in str(gender).lower():
            return v.id
    return None


def generate_speech_wav(text: str) -> bytes | None:
    """
    Convert text to speech and return raw WAV bytes.
    Returns None if TTS is unavailable or fails.
    Blocks until synthesis is complete (uses a temp file since pyttsx3 requires it).
    """
    if platform.system() != "Windows":
        logger.warning("pyttsx3 TTS is only supported on Windows.")
        return None

    clean = _strip_symbols(text)
    clean = _normalize_for_speech(clean)
    if not clean:
        return None

    try:
        import pyttsx3  # deferred import to avoid startup crash on non-Windows
    except ImportError:
        logger.warning("pyttsx3 not installed; TTS unavailable.")
        return None

    with _tts_lock:
        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            engine = pyttsx3.init()

            female_id = _find_female_voice(engine)
            if female_id:
                engine.setProperty("voice", female_id)

            # Natural pacing: slightly slower than default, adaptive for long text.
            rate = 162
            if len(clean) > 450:
                rate = 154
            elif len(clean) > 260:
                rate = 158
            engine.setProperty("rate", rate)
            engine.setProperty("volume", 0.96)

            engine.save_to_file(clean, tmp_path)
            engine.runAndWait()
            engine.stop()

            wav_bytes = Path(tmp_path).read_bytes()
            return wav_bytes
        except Exception as exc:
            logger.exception("TTS generation failed: %s", exc)
            return None
        finally:
            if tmp_path:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except OSError:
                    pass
