"""Headless-safe tests for the live-audio layer and array-based ASR.

No live hardware is asserted (CI may have no devices); we only check the calls are
safe and that transcribing an array matches transcribing the same file.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from translator import asr, audio, devices

SAMPLE = Path(__file__).parent / "sample" / "en.wav"


def test_device_listings_are_safe():
    ins = devices.list_input_devices()
    outs = devices.list_output_devices()
    assert isinstance(ins, list)
    assert isinstance(outs, list)


def test_resample_16k_changes_length_predictably():
    x = np.zeros(48000, dtype=np.float32)  # 1s @ 48k
    y = audio.resample_16k(x, 48000)
    assert abs(len(y) - 16000) <= 1
    assert audio.resample_16k(x[:16000], 16000).shape[0] == 16000  # no-op path


@pytest.mark.skipif(not SAMPLE.exists(), reason="no sample audio; run install-lang first")
def test_transcribe_array_matches_file():
    samples, sr = audio.read_wav(SAMPLE)
    from_file = asr.transcribe(SAMPLE, "en").text.lower()
    from_array = asr.transcribe_array(samples, sr, "en").text.lower()
    assert from_array.strip()
    # Same audio -> same recognized words (allow trivial whitespace differences).
    assert from_array.split() == from_file.split()
