"""Offline TTS service using Piper first, with pyttsx3/SAPI fallback on Windows.

Generates speech audio as WAV bytes.

Natural-speech improvements included:
- Piper is preferred when enabled and available.
- Sentence/phrase chunking reduces monotone drift on long responses.
- Piper pacing can vary slightly per chunk for a less robotic cadence.
- Cleaner spoken normalization for acronyms, units, scores, timers, and game language.
- WAV chunks are stitched safely using the standard wave module.
- pyttsx3 remains available as a Windows fallback.

Recommended environment variables:
    PIPER_ENABLED=1
    PIPER_MODEL_PATH=backend/assets/piper_voices/en_US-amy-high.onnx
    PIPER_LENGTH_SCALE=1.05
    PIPER_NOISE_SCALE=0.667
    PIPER_NOISE_W=0.8
    PIPER_VARIATION=1
"""
from __future__ import annotations

import io
import logging
import os
import platform
import random
import re
import shutil
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

# Preferred voice name fragments for pyttsx3/SAPI fallback.
_FEMALE_VOICE_PREFS = [
    "zira",    # Microsoft Zira Desktop - US English female
    "hazel",   # Microsoft Hazel Desktop - GB English female
    "susan",   # alternate
    "aria",    # Microsoft Aria, newer Windows voices
    "jenny",   # Microsoft Jenny
]

_tts_lock = threading.Lock()

_BASE_RATE = int(os.getenv("PYTTSX3_BASE_RATE", "166"))
_DEFAULT_PIPER_LENGTH_SCALE = 1.05
_DEFAULT_PIPER_NOISE_SCALE = "0.667"
_DEFAULT_PIPER_NOISE_W = "0.8"
_MAX_CHUNK_CHARS = 260
_MIN_CHUNK_CHARS = 24


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _piper_enabled() -> bool:
    return _env_bool("PIPER_ENABLED", default=False)


def _piper_variation_enabled() -> bool:
    return _env_bool("PIPER_VARIATION", default=True)


def _project_root() -> Path:
    # backend/app/services/tts_service.py -> backend/
    return Path(__file__).resolve().parents[2]


def _default_piper_model_path() -> Path:
    # Prefer a high-quality model if the user has it, then fall back to medium.
    voices_dir = _project_root() / "assets" / "piper_voices"
    high = voices_dir / "en_US-amy-high.onnx"
    medium = voices_dir / "en_US-amy-medium.onnx"
    return high if high.exists() else medium


def _default_piper_bin_path() -> Path:
    if platform.system() == "Windows":
        return _project_root() / ".venv" / "Scripts" / "piper.exe"
    return _project_root() / ".venv" / "bin" / "piper"


def _strip_symbols(text: str) -> str:
    """Remove markup and symbols that sound bad when read aloud."""
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove fenced code first so inline handling does not mangle it.
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)

    # Markdown and lightweight formatting.
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)
    text = re.sub(r"^\s*[-*+•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+[.)]\s+", "", text, flags=re.MULTILINE)

    # Remove URLs and internal action tags.
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\[[A-Z_]+:[^\]]+\]", "", text)

    # Keep sentence boundaries but reduce visual clutter.
    text = re.sub(r"[<>]", "", text)
    text = re.sub(r"[*#_~`^|{}\\]", "", text)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\n", ", ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _normalize_for_speech(text: str) -> str:
    """Shape text into wording that TTS engines pronounce more naturally."""
    if not text:
        return ""

    replacements = {
        r"\bAOJ\b": "A O J",
        r"\bETA\b": "E T A",
        r"\bCTF\b": "C T F",
        r"\bKOTH\b": "K O T H",
        r"\bCQB\b": "C Q B",
        r"\bJMSDF\b": "J M S D F",
        r"\bLoRa\b": "low rah",
        r"\bGPIO\b": "G P I O",
        r"\bUSB\b": "U S B",
        r"\bAI\b": "A I",
        r"\bTTS\b": "T T S",
    }
    for pattern, spoken in replacements.items():
        text = re.sub(pattern, spoken, text, flags=re.IGNORECASE)

    # Game score, e.g. Red 3/2 -> Red 3 to 2.
    text = re.sub(
        r"\b(Red|Blue|Green|Yellow)\s*(\d+)\s*/\s*(\d+)\b",
        lambda m: f"{m.group(1)} {m.group(2)} to {m.group(3)}",
        text,
        flags=re.IGNORECASE,
    )

    # Timer notation, e.g. 03:45 -> 3 minutes 45 seconds.
    def _timer_repl(match: re.Match[str]) -> str:
        minutes = int(match.group(1))
        seconds = int(match.group(2))
        if minutes and seconds:
            return f"{minutes} minutes {seconds} seconds"
        if minutes:
            return f"{minutes} minutes"
        return f"{seconds} seconds"

    text = re.sub(r"\b(\d{1,2}):(\d{2})\b", _timer_repl, text)

    # Units and common compact forms.
    text = re.sub(r"\b(\d+)\s*[- ]\s*min(?:ute)?s?\b", r"\1 minutes", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\s*[- ]\s*sec(?:ond)?s?\b", r"\1 seconds", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*joules?\b", r"\1 joules", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*J\b", r"\1 joules", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+)\s*mAh\b", r"\1 milliamp hours", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*V\b", r"\1 volts", text, flags=re.IGNORECASE)

    # Spoken punctuation tuning.
    text = text.replace(";", ", ")
    text = text.replace(":", ", ")
    text = re.sub(r"(?<=\w)-(?=\w)", " ", text)
    text = re.sub(r"\.{3,}", ".", text)
    text = re.sub(r"\s*/\s*", " over ", text)

    # Spoken list connectors.
    text = re.sub(r"(^|\s)1\.\s*", r"\1First, ", text)
    text = re.sub(r"(^|\s)2\.\s*", r"\1Second, ", text)
    text = re.sub(r"(^|\s)3\.\s*", r"\1Third, ", text)
    text = re.sub(r"(^|\s)4\.\s*", r"\1Fourth, ", text)
    text = re.sub(r"(^|\s)5\.\s*", r"\1Fifth, ", text)

    # Avoid repeated punctuation that can make Piper overperform awkwardly.
    text = re.sub(r"!{2,}", "!", text)
    text = re.sub(r"\?{2,}", "?", text)
    text = re.sub(r"\s+([,.!?])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)

    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _split_for_natural_speech(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split text into natural chunks so each synthesis pass gets fresh prosody."""
    if len(text) <= max_chars:
        return [text]

    # First split by sentence endings.
    pieces = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    def flush() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = ""

    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue

        if len(piece) > max_chars:
            flush()
            # Then split long sentences by softer punctuation.
            subpieces = re.split(r"(?<=[,])\s+", piece)
            sub_current = ""
            for sub in subpieces:
                sub = sub.strip()
                if not sub:
                    continue
                if len(sub_current) + len(sub) + 1 <= max_chars:
                    sub_current = f"{sub_current} {sub}".strip()
                else:
                    if sub_current:
                        chunks.append(sub_current.strip())
                    sub_current = sub
            if sub_current:
                chunks.append(sub_current.strip())
            continue

        if len(current) + len(piece) + 1 <= max_chars:
            current = f"{current} {piece}".strip()
        else:
            flush()
            current = piece

    flush()

    # Merge tiny chunks into the previous chunk to avoid choppy speech.
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < _MIN_CHUNK_CHARS and len(merged[-1]) + len(chunk) + 1 <= max_chars:
            merged[-1] = f"{merged[-1]} {chunk}".strip()
        else:
            merged.append(chunk)

    return merged or [text]


def _adaptive_rate_for_text(text: str) -> int:
    """Adaptive pyttsx3 rate from punctuation and length."""
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
    if re.search(r"\b(alert|warning|urgent|immediate|now|contact|stand by)\b", text, re.I):
        rate += 2

    return max(145, min(178, rate))


def _piper_binary_path() -> str:
    default_bin = _default_piper_bin_path()
    return os.getenv("PIPER_BIN", str(default_bin if default_bin.exists() else "piper"))


def _piper_model_path() -> str:
    return os.getenv("PIPER_MODEL_PATH", str(_default_piper_model_path()))


def _base_piper_length_scale() -> float:
    raw = os.getenv("PIPER_LENGTH_SCALE", str(_DEFAULT_PIPER_LENGTH_SCALE)).strip()
    try:
        return float(raw)
    except ValueError:
        logger.warning("Invalid PIPER_LENGTH_SCALE=%r; using %.2f", raw, _DEFAULT_PIPER_LENGTH_SCALE)
        return _DEFAULT_PIPER_LENGTH_SCALE


def _piper_length_scale_for_chunk(chunk: str) -> str:
    """>1.0 is slower. Slight per-chunk variation makes speech less mechanical."""
    scale = _base_piper_length_scale()

    if _piper_variation_enabled():
        scale += random.uniform(-0.025, 0.04)

    if chunk.endswith("?"):
        scale -= 0.01
    elif re.search(r"\b(alert|warning|urgent|immediate|now)\b", chunk, re.I):
        scale -= 0.015
    elif len(chunk) > 180:
        scale += 0.015

    return f"{max(0.90, min(1.20, scale)):.3f}"


def _is_piper_available() -> tuple[bool, str]:
    bin_path = _piper_binary_path()
    model_path = _piper_model_path()

    bin_exists = bool(shutil.which(bin_path) or Path(bin_path).exists())
    if not bin_exists:
        return False, f"piper binary not found: {bin_path}"

    if not Path(model_path).exists():
        return False, f"piper model not found: {model_path}"

    return True, "ok"


def _generate_piper_chunk(text: str) -> bytes | None:
    """Generate a single WAV chunk with Piper."""
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
            _piper_length_scale_for_chunk(text),
        ]

        speaker_id = os.getenv("PIPER_SPEAKER_ID", "").strip()
        if speaker_id:
            cmd.extend(["--speaker", speaker_id])

        noise_scale = os.getenv("PIPER_NOISE_SCALE", _DEFAULT_PIPER_NOISE_SCALE).strip()
        if noise_scale:
            cmd.extend(["--noise_scale", noise_scale])

        noise_w = os.getenv("PIPER_NOISE_W", _DEFAULT_PIPER_NOISE_W).strip()
        if noise_w:
            cmd.extend(["--noise_w", noise_w])

        proc = subprocess.run(
            cmd,
            input=text,
            text=True,
            capture_output=True,
            check=False,
            timeout=int(os.getenv("PIPER_TIMEOUT_SECONDS", "30")),
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


def _read_wav_params_and_frames(wav_bytes: bytes) -> tuple[wave._wave_params, bytes]:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        params = wav_file.getparams()
        frames = wav_file.readframes(wav_file.getnframes())
    return params, frames


def _silence_frames(params: wave._wave_params, milliseconds: int) -> bytes:
    frame_count = int(params.framerate * milliseconds / 1000)
    return b"\x00" * frame_count * params.nchannels * params.sampwidth


def _stitch_wav_chunks(chunks: Iterable[bytes], pause_ms: int = 90) -> bytes | None:
    """Combine WAV chunks that share the same audio format."""
    chunk_list = list(chunks)
    if not chunk_list:
        return None
    if len(chunk_list) == 1:
        return chunk_list[0]

    first_params, first_frames = _read_wav_params_and_frames(chunk_list[0])
    output = io.BytesIO()

    with wave.open(output, "wb") as out_wav:
        out_wav.setparams(first_params)
        out_wav.writeframes(first_frames)
        silence = _silence_frames(first_params, pause_ms)

        for wav_bytes in chunk_list[1:]:
            params, frames = _read_wav_params_and_frames(wav_bytes)
            comparable_first = first_params[:4]
            comparable_current = params[:4]
            if comparable_current != comparable_first:
                logger.warning("Cannot stitch Piper WAV chunks with mismatched params")
                return None
            out_wav.writeframes(silence)
            out_wav.writeframes(frames)

    return output.getvalue()


def _generate_with_piper(text: str) -> bytes | None:
    ok, reason = _is_piper_available()
    if not ok:
        logger.info("Piper unavailable (%s); falling back if possible", reason)
        return None

    chunks = _split_for_natural_speech(text)
    wav_chunks: list[bytes] = []

    for chunk in chunks:
        wav = _generate_piper_chunk(chunk)
        if wav is None:
            return None
        wav_chunks.append(wav)

    pause_ms = int(os.getenv("PIPER_CHUNK_PAUSE_MS", "90"))
    stitched = _stitch_wav_chunks(wav_chunks, pause_ms=pause_ms)
    if stitched is None:
        logger.warning("Piper chunk stitching failed")
    return stitched


def _find_female_voice(engine) -> str | None:
    """Return the voice ID of the best available female voice, or None."""
    voices = engine.getProperty("voices")

    for pref in _FEMALE_VOICE_PREFS:
        for voice in voices:
            name = getattr(voice, "name", "") or ""
            if pref in name.lower():
                return voice.id

    for voice in voices:
        gender = getattr(voice, "gender", "") or ""
        if "female" in str(gender).lower():
            return voice.id

    return None


def _generate_with_pyttsx3(text: str) -> bytes | None:
    """Generate WAV using pyttsx3/SAPI. Windows fallback only."""
    if platform.system() != "Windows":
        return None

    try:
        import pyttsx3  # deferred import to avoid startup crash on non-Windows
    except ImportError:
        return None

    tmp_path: str | None = None
    try:
        engine = pyttsx3.init()

        female_id = _find_female_voice(engine)
        if female_id:
            engine.setProperty("voice", female_id)

        engine.setProperty("volume", float(os.getenv("PYTTSX3_VOLUME", "0.96")))
        engine.setProperty("rate", _adaptive_rate_for_text(text))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name

        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        engine.stop()

        wav_bytes = Path(tmp_path).read_bytes()
        return wav_bytes if wav_bytes else None
    except Exception as exc:
        logger.exception("pyttsx3 TTS generation failed: %s", exc)
        return None
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


def prepare_text_for_tts(text: str) -> str:
    """Public helper for testing and debugging speech normalization."""
    clean = _strip_symbols(text)
    return _normalize_for_speech(clean)


def generate_speech_wav(text: str) -> bytes | None:
    """
    Convert text to speech and return raw WAV bytes.

    Engine order:
    1. Piper, when PIPER_ENABLED=1 and available.
    2. pyttsx3/SAPI on Windows.
    3. Piper retry, if pyttsx3 failed and Piper is enabled.

    Returns None if all available engines fail.
    """
    clean = prepare_text_for_tts(text)
    if not clean:
        return None

    with _tts_lock:
        if _piper_enabled():
            piper_wav = _generate_with_piper(clean)
            if piper_wav is not None:
                return piper_wav

        pyttsx3_wav = _generate_with_pyttsx3(clean)
        if pyttsx3_wav is not None:
            return pyttsx3_wav

        logger.warning("No TTS engine available or all engines failed.")
        return None


def tts_engine_status() -> dict[str, str | bool | int | None]:
    """Expose TTS engine availability and config for an API status route."""
    piper_ok = False
    piper_reason = "piper_disabled"
    if _piper_enabled():
        piper_ok, piper_reason = _is_piper_available()
        piper_reason = "ok" if piper_ok else piper_reason

    pyttsx3_ok = False
    pyttsx3_voice: str | None = None
    pyttsx3_reason = "not_windows"

    if platform.system() == "Windows":
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voice_id = _find_female_voice(engine)
            voices = engine.getProperty("voices")
            pyttsx3_voice = next((v.name for v in voices if v.id == voice_id), None)
            engine.stop()
            pyttsx3_ok = True
            pyttsx3_reason = "ok"
        except Exception as exc:
            pyttsx3_reason = str(exc)

    preferred_engine = None
    available = False
    voice = None

    if _piper_enabled() and piper_ok:
        preferred_engine = "piper"
        available = True
        voice = Path(_piper_model_path()).name
    elif pyttsx3_ok:
        preferred_engine = "pyttsx3"
        available = True
        voice = pyttsx3_voice or "default"

    return {
        "available": available,
        "engine": preferred_engine,
        "voice": voice,
        "piper_enabled": _piper_enabled(),
        "piper_available": piper_ok,
        "piper_reason": piper_reason,
        "piper_model": Path(_piper_model_path()).name if _piper_enabled() else None,
        "piper_length_scale": f"{_base_piper_length_scale():.3f}" if _piper_enabled() else None,
        "piper_variation": _piper_variation_enabled() if _piper_enabled() else None,
        "pyttsx3_available": pyttsx3_ok,
        "pyttsx3_voice": pyttsx3_voice,
        "pyttsx3_reason": pyttsx3_reason,
        "chunk_max_chars": _MAX_CHUNK_CHARS,
    }
