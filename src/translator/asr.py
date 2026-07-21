"""ASR: speech-to-text via faster-whisper (CTranslate2).

Accepts either a file path (any format PyAV can decode: wav/mp3/m4a/flac/...) or a
raw numpy audio array (for live mic capture). Auto-detects the spoken language when
asked, and runs on GPU or CPU per :func:`config.detect_device` with a runtime
CUDA->CPU fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import audio as _audio
from . import config


@dataclass
class Transcript:
    text: str
    language: str          # detected/used ISO code
    language_probability: float


@lru_cache(maxsize=2)
def _load_model(size: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    config.ensure_dirs()
    # download_root keeps the model inside our portable cache.
    return WhisperModel(
        size,
        device=device,
        compute_type=compute_type,
        download_root=str(config.ASR_DIR),
    )


def transcribe(audio_path: str | Path, source_lang: str = "auto") -> Transcript:
    """Transcribe speech in ``audio_path`` to text in its original language.

    ``source_lang="auto"`` lets Whisper detect the language; otherwise pass an ISO
    code (or alias like 'pt-br') to skip detection.
    """
    audio_path = str(audio_path)
    if not Path(audio_path).exists():
        raise FileNotFoundError(audio_path)
    return _transcribe(audio_path, source_lang)


def transcribe_array(samples: np.ndarray, sample_rate: int = 16000, source_lang: str = "auto") -> Transcript:
    """Transcribe raw mono float32 audio (e.g. from live mic capture).

    Whisper expects 16 kHz; the array is resampled if needed.
    """
    samples = _audio.resample_16k(np.asarray(samples, dtype=np.float32), sample_rate)
    return _transcribe(samples, source_lang)


def _transcribe(audio_input, source_lang: str) -> Transcript:
    """Shared entry point (path or array) with a one-shot CUDA->CPU fallback."""
    lang = None if source_lang == "auto" else config.normalize_lang(source_lang)
    try:
        return _run(audio_input, lang)
    except RuntimeError as e:
        # CUDA runtime (cuBLAS/cuDNN) missing or failing -> fall back to CPU once.
        if config.detect_device().device != "cpu" and _is_cuda_error(e):
            config.force_cpu()
            return _run(audio_input, lang)
        raise


def _run(audio_input, lang: str | None) -> Transcript:
    dev = config.detect_device()
    model = _load_model(config.WHISPER_SIZE, dev.device, dev.compute_type)
    # vad_filter drops silence; no_speech_threshold + condition_on_previous_text=False
    # curb the phantom text / repetition Whisper can emit on quiet or noisy input.
    segments, info = model.transcribe(
        audio_input,
        language=lang,
        vad_filter=True,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
    )
    # Consume the generator here so any device error surfaces inside the try.
    text = "".join(seg.text for seg in segments).strip()
    return Transcript(
        text=text,
        language=config.normalize_lang(info.language),
        language_probability=float(info.language_probability),
    )


def _is_cuda_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in ("cublas", "cudnn", "cuda", "gpu"))
