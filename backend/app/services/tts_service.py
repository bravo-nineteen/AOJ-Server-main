"""Offline TTS service using pyttsx3/SAPI on Windows, with optional Piper.

Generates speech audio as WAV bytes. pyttsx3 is the default voice engine to keep
legacy behavior and pacing. Piper can be enabled explicitly with PIPER_ENABLED.
"""
from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
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
_BASE_RATE = 166
_DEFAULT_PIPER_LENGTH_SCALE = 1.08


def _piper_enabled() -> bool:
    return os.getenv("PIPER_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _project_root() -> Path:
    # backend/app/services/tts_service.py -> backend/
    return Path(__file__).resolve().parents[2]


def _default_piper_model_path() -> Path:
    return _project_root() / "assets" / "piper_voices" / "en_US-amy-medium.onnx"


def _default_piper_bin_path() -> Path:
    return _project_root() / ".venv" / "Scripts" / "piper.exe"


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
    text = re.sub(r"\bCTF\b", "capture the flag", text, flags=re.IGNORECASE)
    text = re.sub(r"\bKOTH\b", "king of the hill", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLoRa\b", "low rah", text, flags=re.IGNORECASE)

    # Humanize score and time notations for cleaner pronunciation.
    text = re.sub(
        r"\b(Red|Blue)\s*(\d+)\s*/\s*(\d+)\b",
        lambda m: f"{m.group(1)} {m.group(2)} to {m.group(3)}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(\d{1,2}):(\d{2})\b",
        lambda m: f"{int(m.group(1))} minutes {int(m.group(2))} seconds",
        text,
    )
    text = re.sub(
        r"\b(\d+)m\b",
        lambda m: f"{m.group(1)} meters",
        text,
        flags=re.IGNORECASE,
    )

    # Punctuation tuning for pauses.
    text = text.replace(";", ", ")
    text = text.replace(":", ", ")
    text = re.sub(r"\s*-\s*", ", ", text)
    text = re.sub(r"\.{3,}", ".", text)
    text = re.sub(r"\s*/\s*", " over ", text)

    # Convert list style phrasing to spoken connectors.
    text = re.sub(r"(^|\s)1\.\s*", r"\1First, ", text)
    text = re.sub(r"(^|\s)2\.\s*", r"\1Second, ", text)
    text = re.sub(r"(^|\s)3\.\s*", r"\1Third, ", text)
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _adaptive_rate_for_text(text: str) -> int:
    """Adaptive rate from punctuation and length for smoother, less rushed delivery."""
    rate = _BASE_RATE
    length = len(text)
    comma_count = text.count(",")
    question_count = text.count("?")
    sentence_count = len(re.findall(r"[.!?]", text))

    if length < 80:
        rate += 4
    elif length < 180:
        rate += 2
    elif length > 500:
        rate -= 8
    elif length > 320:
        rate -= 5

    if comma_count >= 6:
        rate -= 3
    if question_count >= 2:
        rate -= 2
    if sentence_count >= 10:
        rate -= 2
    if re.search(r"\b(alert|warning|urgent|now)\b", text, re.I):
        rate += 2

    return max(150, min(176, rate))


def _piper_binary_path() -> str:
    default_bin = _default_piper_bin_path()
    return os.getenv("PIPER_BIN", str(default_bin if default_bin.exists() else "piper"))


def _piper_model_path() -> str:
    return os.getenv("PIPER_MODEL_PATH", str(_default_piper_model_path()))


def _piper_length_scale() -> str:
    # >1.0 = slower speaking pace
    return os.getenv("PIPER_LENGTH_SCALE", str(_DEFAULT_PIPER_LENGTH_SCALE))


def _is_piper_available() -> tuple[bool, str]:
    bin_path = _piper_binary_path()
    model_path = _piper_model_path()

    bin_exists = bool(shutil.which(bin_path) or Path(bin_path).exists())
    if not bin_exists:
        return False, f"piper binary not found: {bin_path}"

    if not Path(model_path).exists():
        return False, f"piper model not found: {model_path}"

    return True, "ok"


def _generate_with_piper(text: str) -> bytes | None:
    ok, reason = _is_piper_available()
    if not ok:
        logger.info("Piper unavailable (%s); falling back to pyttsx3", reason)
        return None

    bin_path = _piper_binary_path()
    model_path = _piper_model_path()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name

    try:
        cmd = [
            bin_path,
            "--model",
            model_path,
            "--output_file",
            out_path,
            "--length_scale",
            _piper_length_scale(),
        ]

        # Optional voice/synthesis tuning
        speaker_id = os.getenv("PIPER_SPEAKER_ID", "").strip()
        if speaker_id:
            cmd.extend(["--speaker", speaker_id])

        noise_scale = os.getenv("PIPER_NOISE_SCALE", "").strip()
        if noise_scale:
            cmd.extend(["--noise_scale", noise_scale])

        noise_w = os.getenv("PIPER_NOISE_W", "").strip()
        if noise_w:
            cmd.extend(["--noise_w", noise_w])

        proc = subprocess.run(
            cmd,
            input=text,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        if proc.returncode != 0:
            logger.warning("Piper synthesis failed (%s): %s", proc.returncode, proc.stderr.strip())
            return None

        wav_bytes = Path(out_path).read_bytes()
        if not wav_bytes:
            logger.warning("Piper produced empty WAV output")
            return None
        return wav_bytes
    except Exception as exc:
        logger.warning("Piper synthesis exception: %s", exc)
        return None
    finally:
        Path(out_path).unlink(missing_ok=True)


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
    clean = _strip_symbols(text)
    clean = _normalize_for_speech(clean)
    if not clean:
        return None

    pyttsx3 = None
    if platform.system() == "Windows":
        try:
            import pyttsx3 as _pyttsx3  # deferred import to avoid startup crash on non-Windows
            pyttsx3 = _pyttsx3
        except ImportError:
            pass

    with _tts_lock:
        if pyttsx3 is None:
            if _piper_enabled():
                piper_wav = _generate_with_piper(clean)
                if piper_wav is not None:
                    return piper_wav
            logger.warning("No TTS engine available (pyttsx3 unavailable, Piper disabled/unavailable).")
            return None

        tmp_path: str | None = None
        try:
            engine = pyttsx3.init()

            female_id = _find_female_voice(engine)
            if female_id:
                engine.setProperty("voice", female_id)

            engine.setProperty("volume", 0.96)
            engine.setProperty("rate", _adaptive_rate_for_text(clean))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            engine.save_to_file(clean, tmp_path)
            engine.runAndWait()
            engine.stop()

            return Path(tmp_path).read_bytes()
        except Exception as exc:
            logger.exception("pyttsx3 TTS generation failed: %s", exc)
            if _piper_enabled():
                logger.info("Attempting Piper fallback after pyttsx3 failure")
                return _generate_with_piper(clean)
            return None
        finally:
            if tmp_path:
                Path(tmp_path).unlink(missing_ok=True)


def tts_engine_status() -> dict[str, str | bool | None]:
    """Expose active TTS engine availability and config for API status route."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voice_id = _find_female_voice(engine)
        voices = engine.getProperty("voices")
        voice_name = next((v.name for v in voices if v.id == voice_id), None)
        engine.stop()
        if _piper_enabled():
            piper_ok, piper_reason = _is_piper_available()
            reason = "piper_enabled" if piper_ok else f"piper_enabled_but_unavailable: {piper_reason}"
        else:
            reason = "piper_disabled"
        return {
            "available": True,
            "engine": "pyttsx3",
            "voice": voice_name or "default",
            "reason": reason,
        }
    except Exception as exc:
        if _piper_enabled():
            piper_ok, piper_reason = _is_piper_available()
            if piper_ok:
                return {
                    "available": True,
                    "engine": "piper",
                    "voice": Path(_piper_model_path()).name,
                    "reason": "pyttsx3_unavailable; piper_enabled",
                }
            piper_part = f"piper_enabled_but_unavailable: {piper_reason}"
        else:
            piper_part = "piper_disabled"
        return {
            "available": False,
            "engine": None,
            "voice": None,
            "reason": f"{piper_part}; pyttsx3_error: {exc}",
        }
