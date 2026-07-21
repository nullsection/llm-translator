"""End-to-end smoke tests.

The heavyweight ASR/MT/TTS models are only exercised when their assets are already
present locally, so these tests are skipped by default in CI and run once you have
done `translator install-lang en zh` and dropped a clip at tests/sample/en.wav.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from translator import config, pipeline

SAMPLE = Path(__file__).parent / "sample" / "en.wav"


def test_registry_includes_defaults_and_is_broad():
    codes = {l["code"] for l in pipeline.list_languages()}
    assert {"en", "ja", "zh"} <= codes
    assert len(codes) >= 20  # opened up to many languages via NLLB


def test_normalize_lang_aliases():
    assert config.normalize_lang("Japanese") == "ja"
    assert config.normalize_lang("zh_CN") == "zh"
    assert config.normalize_lang("English") == "en"


@pytest.mark.skipif(not SAMPLE.exists(), reason="no sample audio; install a language first")
def test_translate_audio_en_to_ja(tmp_path):
    out = tmp_path / "out.wav"
    r = pipeline.translate_audio(SAMPLE, target_lang="ja", source_lang="en", out_audio_path=out)
    assert r.source_text.strip()
    assert r.translated_text.strip()
    assert r.target_lang == "ja"
    assert out.exists() and out.stat().st_size > 0  # VOICEVOX Japanese speech
