"""TTS: text-to-speech via Piper (lightweight offline ONNX voices).

Voices are downloaded on demand from the official rhasspy/piper-voices repo into
the portable model cache. The public surface is a single :func:`synthesize`
function plus :func:`ensure_voice`; the Piper-specific details (download layout,
API differences across piper-tts versions) are isolated here so the backend can
be swapped (e.g. to Coqui XTTS) without touching the rest of the pipeline.
"""
from __future__ import annotations

import logging
import time
import wave
from functools import lru_cache
from pathlib import Path

import requests

from . import config

log = logging.getLogger("translator.tts")
_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def _voice_url(voice_id: str, ext: str) -> str:
    # "en_US-lessac-medium" -> en/en_US/lessac/medium/en_US-lessac-medium.onnx[.json]
    lang_region, name, quality = voice_id.split("-")
    family = lang_region.split("_")[0]
    return f"{_HF_BASE}/{family}/{lang_region}/{name}/{quality}/{voice_id}.onnx{ext}"


def _download(url: str, dest: Path, attempts: int = 3) -> None:
    """Download ``url`` to ``dest`` atomically, retrying transient failures."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    last: Exception | None = None
    offline = False
    for i in range(attempts):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 16):
                        f.write(chunk)
            tmp.replace(dest)  # atomic: dest appears only when fully written
            return
        except requests.exceptions.ConnectionError as e:
            last, offline = e, True
            log.warning("download attempt %d/%d failed (offline?): %s", i + 1, attempts, e)
        except requests.exceptions.RequestException as e:
            last = e
            log.warning("download attempt %d/%d failed: %s", i + 1, attempts, e)
        if i < attempts - 1:
            time.sleep(1.5 * (i + 1))
    tmp.unlink(missing_ok=True)
    if offline:
        raise ConnectionError("No internet connection — can't download this voice right now.")
    raise ConnectionError(f"Could not download voice after {attempts} tries: {last}")


def voice_files_present(voice_id: str) -> bool:
    """True if both files of a specific Piper voice id are present locally."""
    return (config.TTS_DIR / f"{voice_id}.onnx").exists() and (config.TTS_DIR / f"{voice_id}.onnx.json").exists()


def ensure_voice_id(voice_id: str) -> Path:
    """Ensure a specific Piper voice id is present locally; return its .onnx path.

    Downloads both required files (model + config); leaves nothing half-installed
    (a failed config download removes the orphan model so state stays consistent).
    """
    config.ensure_dirs()
    onnx = config.TTS_DIR / f"{voice_id}.onnx"
    cfg = config.TTS_DIR / f"{voice_id}.onnx.json"
    if onnx.exists() and cfg.exists():
        return onnx
    fresh_onnx = not onnx.exists()
    if not onnx.exists():
        _download(_voice_url(voice_id, ""), onnx)
    try:
        if not cfg.exists():
            _download(_voice_url(voice_id, ".json"), cfg)
    except Exception:
        if fresh_onnx:
            onnx.unlink(missing_ok=True)  # don't leave a model without its config
        raise
    return onnx


def ensure_voice(lang: str) -> Path:
    """Ensure the currently selected Piper voice for ``lang`` is present locally."""
    voice_id = config.active_voice(lang)
    if voice_id is None:
        raise RuntimeError(
            f"No offline speech voice is available for '{lang}'. "
            "It can be transcribed and translated, but not spoken."
        )
    return ensure_voice_id(voice_id)


@lru_cache(maxsize=4)
def _load_voice(onnx_path: str):
    from piper import PiperVoice

    return PiperVoice.load(onnx_path)


def synthesize(text: str, lang: str, out_path: str | Path) -> Path:
    """Synthesize ``text`` in ``lang`` to a wav file, dispatching to the right backend.

    Piper handles languages with a ``piper_voice``; Japanese (and any language with a
    ``voicevox_style``) is routed to the VOICEVOX backend.
    """
    lang_obj = config.get_language(lang)
    if lang_obj.piper_voice is None and lang_obj.voicevox_style is not None:
        from . import voicevox_tts

        return voicevox_tts.synthesize(text, lang_obj.voicevox_style, out_path)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    onnx = ensure_voice(lang)
    voice = _load_voice(str(onnx))

    # piper-tts >= 1.3 yields AudioChunk objects; <= 1.2 writes into a wave file.
    try:
        chunks = list(voice.synthesize(text))
        first = chunks[0]
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(getattr(first, "sample_channels", 1))
            wf.setsampwidth(getattr(first, "sample_width", 2))
            wf.setframerate(getattr(first, "sample_rate", voice.config.sample_rate))
            for c in chunks:
                wf.writeframes(c.audio_int16_bytes)
    except (AttributeError, TypeError):
        # Legacy API: synthesize(text, wave_write)
        with wave.open(str(out_path), "wb") as wf:
            voice.synthesize(text, wf)
    return out_path
