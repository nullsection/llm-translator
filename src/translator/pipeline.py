"""The shared translation engine.

Both front-ends (:mod:`translator.cli` and :mod:`translator.mcp_server`) call the
functions here and nothing else. Stages: ASR -> MT -> (optional) TTS.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import re

from . import asr, audio, config, mt, tts, voices

# Punctuation that speech-to-text can't reliably infer (exclamation, question,
# commas — half- and full-width). Stripped from voice output when `plain` is on.
_SPEECH_PUNCT = set("!?,！？，、")


def clean_speech_punctuation(text: str) -> str:
    """Drop !, ?, and commas (keep periods) — for voice-sourced text only."""
    out = "".join(ch for ch in text if ch not in _SPEECH_PUNCT)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


@dataclass
class TranslationResult:
    source_lang: str
    source_text: str
    target_lang: str
    translated_text: str
    out_audio_path: str | None

    def as_dict(self) -> dict:
        return asdict(self)


def list_languages() -> list[dict]:
    """Return the supported languages as ``[{code, name}, ...]``."""
    return [{"code": l.code, "name": l.name} for l in config.LANGUAGES.values()]


def transcribe(audio_path: str | Path, source_lang: str = "auto") -> asr.Transcript:
    """Speech -> text in the original language."""
    return asr.transcribe(audio_path, source_lang)


def detect_text_language(text: str) -> str:
    """Best-effort source-language guess for TYPED text, by script.

    Whisper detects spoken language from audio; for typed text we just need a rough
    script-based guess so the translator has a source. Latin script defaults to en.
    Result is clamped to a language in the registry (else 'en').
    """
    if any(0x3040 <= ord(c) <= 0x30FF for c in text):        # Hiragana/Katakana
        guess = "ja"
    elif any(0x4E00 <= ord(c) <= 0x9FFF for c in text):      # CJK ideographs (no kana)
        guess = "zh"
    elif any(0x0400 <= ord(c) <= 0x04FF for c in text):      # Cyrillic
        guess = "ru"
    elif any(0x0600 <= ord(c) <= 0x06FF for c in text):      # Arabic
        guess = "ar"
    elif any(0x0900 <= ord(c) <= 0x097F for c in text):      # Devanagari
        guess = "hi"
    elif any(0x0370 <= ord(c) <= 0x03FF for c in text):      # Greek
        guess = "el"
    else:
        guess = "en"
    return guess if guess in config.LANGUAGES else "en"


def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Text -> translated text (offline; assumes the backend model is installed)."""
    src = config.normalize_lang(source_lang)
    tgt = config.normalize_lang(target_lang)
    # NLLB is a single pre-loaded model; only Argos needs a per-pair package.
    if mt.backend() == "argos":
        mt.ensure_pair(src, tgt)
    return mt.translate_text(text, src, tgt)


def synthesize(text: str, lang: str, out_path: str | Path) -> Path:
    """Text -> speech wav."""
    return tts.synthesize(text, lang, out_path)


def translate_audio(
    input_path: str | Path,
    target_lang: str,
    source_lang: str = "auto",
    speak: bool = True,
    out_audio_path: str | Path | None = None,
    plain: bool = True,
) -> TranslationResult:
    """Full pipeline: audio in -> translated text (+ optional translated speech out).

    ``plain`` (default) strips !, ?, and commas from the voice-sourced result, since
    speech can't reliably determine them. Returns a :class:`TranslationResult`; when
    ``speak`` is True an audio file is written.
    """
    target_lang = config.normalize_lang(target_lang)
    config.get_language(target_lang)  # validate target early

    # 1. ASR
    t = transcribe(input_path, source_lang)
    src = t.language

    # 2. MT — translate the ORIGINAL (punctuation aids quality), skip if same language
    source_text = t.text
    translated = source_text if src == target_lang else translate_text(source_text, src, target_lang)

    # 2b. Strip speech-ambiguous punctuation from the displayed/returned text
    if plain:
        source_text = clean_speech_punctuation(source_text)
        translated = clean_speech_punctuation(translated)

    # 3. TTS (optional; skipped when no voice is installed for the target language)
    out_path: str | None = None
    if speak and translated.strip() and voices.is_installed(target_lang):
        dest = Path(out_audio_path) if out_audio_path else audio.default_out_path(input_path, target_lang)
        out_path = str(synthesize(translated, target_lang, dest))

    return TranslationResult(
        source_lang=src,
        source_text=source_text,
        target_lang=target_lang,
        translated_text=translated,
        out_audio_path=out_path,
    )
