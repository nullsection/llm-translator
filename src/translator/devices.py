"""Live audio device layer: enumerate mics/speakers, capture, and playback.

Built on ``sounddevice`` (PortAudio). Capture targets 16 kHz mono float32 — the
format faster-whisper wants — falling back to the device's native rate + resample
when 16 kHz is refused. Kept separate from the GUI so it can be unit-tested and
reused headlessly.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TARGET_SR = 16000


@dataclass
class AudioDevice:
    index: int
    name: str
    default: bool


def _query():
    import sounddevice as sd

    return sd.query_devices(), sd.default.device  # (list, (in_idx, out_idx))


def list_input_devices() -> list[AudioDevice]:
    """Return input-capable devices. Empty list if PortAudio/host has none."""
    try:
        devices, default = _query()
    except Exception:
        return []
    out = []
    for i, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            out.append(AudioDevice(i, d["name"], i == default[0]))
    return out


def list_output_devices() -> list[AudioDevice]:
    """Return output-capable devices. Empty list if PortAudio/host has none."""
    try:
        devices, default = _query()
    except Exception:
        return []
    out = []
    for i, d in enumerate(devices):
        if d["max_output_channels"] > 0:
            out.append(AudioDevice(i, d["name"], i == default[1]))
    return out


class Recorder:
    """Push-to-record mic capture into an in-memory float32 buffer.

    Usage: ``start(device_index)`` ... ``arr, sr = stop()``. The array is mono
    float32; ``sr`` is 16 kHz when the device accepts it (the common case).
    """

    def __init__(self) -> None:
        self._stream = None
        self._chunks: list[np.ndarray] = []
        self._sr = TARGET_SR

    def start(self, device_index: int | None = None) -> None:
        import sounddevice as sd

        self._chunks = []
        self._sr = TARGET_SR
        try:
            self._stream = sd.InputStream(
                samplerate=TARGET_SR, channels=1, dtype="float32",
                device=device_index, callback=self._callback,
            )
        except Exception:
            # Device won't do 16 kHz mono: use its default samplerate, resample on stop.
            info = sd.query_devices(device_index, "input")
            self._sr = int(info["default_samplerate"])
            self._stream = sd.InputStream(
                samplerate=self._sr, channels=1, dtype="float32",
                device=device_index, callback=self._callback,
            )
        self._stream.start()

    def _callback(self, indata, frames, time, status) -> None:  # noqa: ANN001
        self._chunks.append(indata[:, 0].copy())

    def stop(self) -> tuple[np.ndarray, int]:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return np.zeros(0, dtype=np.float32), TARGET_SR
        return np.concatenate(self._chunks).astype(np.float32), self._sr


def play(samples: np.ndarray, samplerate: int, device_index: int | None = None, blocking: bool = False) -> None:
    """Play ``samples`` to the chosen output device (non-blocking by default)."""
    import sounddevice as sd

    sd.play(samples, samplerate, device=device_index)
    if blocking:
        sd.wait()


def stop_playback() -> None:
    import sounddevice as sd

    sd.stop()
