"""Tests for the voice catalog / install state (reflects current model cache)."""
from __future__ import annotations

from translator import config, voices


def test_every_language_has_an_nllb_code():
    # Translation works offline for all of them via NLLB.
    for lang in config.LANGUAGES.values():
        assert lang.nllb_code, lang.code


def test_default_three_voices_installed():
    installed = {v["code"] for v in voices.installed()}
    assert {"en", "ja", "zh"} <= installed


def test_japanese_voice_is_voicevox_not_downloadable():
    ja = next(v for v in voices.catalog() if v["code"] == "ja")
    assert ja["kind"] == "voicevox"
    assert ja["removable"] is False
    assert ja["code"] not in {v["code"] for v in voices.downloadable()}


def test_is_installed_matches_catalog():
    for v in voices.catalog():
        assert voices.is_installed(v["code"]) is v["installed"]
