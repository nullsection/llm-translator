"""Audio I/O helpers.

Decoding of arbitrary input formats (mp3, m4a, wav, ...) is handled by
faster-whisper's bundled PyAV inside :mod:`translator.asr`, so here we only need
to *write* the synthesized speech that Piper produces (raw int16 PCM -> wav).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def write_wav(path: str | Path, samples: np.ndarray, sample_rate: int) -> Path:
    """Write mono int16/float PCM samples to a wav file, creating parent dirs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), samples, sample_rate)
    return path


def default_out_path(input_path: str | Path, target_lang: str) -> Path:
    """Derive a sensible output path next to the input, e.g. talk.wav -> talk.zh.wav."""
    p = Path(input_path)
    return p.with_suffix(f".{target_lang}.wav")


def read_wav(path: str | Path) -> tuple[np.ndarray, int]:
    """Read a wav into a mono float32 array and its sample rate."""
    samples, sr = sf.read(str(path), dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    return samples.astype(np.float32), int(sr)


def resample_16k(samples: np.ndarray, sr: int, target_sr: int = 16000) -> np.ndarray:
    """Linear-resample mono float32 audio to ``target_sr`` (fine for speech ASR)."""
    if sr == target_sr or samples.size == 0:
        return samples.astype(np.float32)
    n_out = int(round(samples.shape[0] * target_sr / sr))
    x_old = np.arange(samples.shape[0], dtype=np.float64)
    x_new = np.linspace(0, samples.shape[0], n_out, endpoint=False)
    return np.interp(x_new, x_old, samples).astype(np.float32)
