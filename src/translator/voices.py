"""Voice management: which languages can be *spoken*, and downloading/removing voices.

Translation is handled by NLLB for every language in the registry with no download.
The only per-language asset is the **voice** used for speech output:

* en / zh use bundled **Piper** voices; ja uses the bundled **VOICEVOX** voice.
* Every other language can be translated now (text), and its Piper voice can be
  downloaded on demand from the static Piper URLs to enable speech.

A language whose voice is not installed is simply text-only.
"""
from __future__ import annotations

from . import config


def is_installed(code: str) -> bool:
    """True if a usable voice for ``code`` is present locally (Piper file or VOICEVOX)."""
    code = config.normalize_lang(code)
    lang = config.get_language(code)
    if lang.voicevox_style is not None:
        from . import voicevox_tts

        return voicevox_tts.available()
    if lang.piper_voice is not None:
        # Both files are required — a half-download must not report as installed.
        onnx = config.TTS_DIR / f"{lang.piper_voice}.onnx"
        cfg = config.TTS_DIR / f"{lang.piper_voice}.onnx.json"
        return onnx.exists() and cfg.exists()
    return False


def catalog() -> list[dict]:
    """Every language that can have a voice, with install/removable status."""
    out = []
    for code, lang in config.LANGUAGES.items():
        if lang.piper_voice is None and lang.voicevox_style is None:
            continue
        out.append(
            {
                "code": code,
                "name": lang.name,
                "installed": is_installed(code),
                "kind": "voicevox" if lang.voicevox_style is not None else "piper",
                "removable": lang.piper_voice is not None,  # bundled VOICEVOX isn't removable here
            }
        )
    return out


def downloadable() -> list[dict]:
    """Voices that can be downloaded from the static Piper URLs (excludes bundled VOICEVOX)."""
    return [v for v in catalog() if v["kind"] == "piper"]


def installed() -> list[dict]:
    return [v for v in catalog() if v["installed"]]


def download(code: str) -> None:
    """Download the Piper voice for ``code`` (needs internet once)."""
    code = config.normalize_lang(code)
    lang = config.get_language(code)
    if lang.piper_voice is None:
        raise RuntimeError(f"{lang.name} has no downloadable Piper voice.")
    from . import tts

    tts.ensure_voice(code)


def voice_files(code: str) -> dict:
    """Return the exact download URLs + destination for a language's Piper voice.

    Lets you fetch the two files by hand (e.g. on an offline machine you'll move the
    folder to) and drop them into ``models/tts`` — the app then treats the voice as
    installed. Both files are required.
    """
    code = config.normalize_lang(code)
    lang = config.get_language(code)
    if lang.piper_voice is None:
        raise RuntimeError(f"{lang.name} has no downloadable Piper voice.")
    from . import tts

    vid = lang.piper_voice
    return {
        "voice_id": vid,
        "onnx_url": tts._voice_url(vid, ""),
        "json_url": tts._voice_url(vid, ".json"),
        "onnx_name": f"{vid}.onnx",
        "json_name": f"{vid}.onnx.json",
        "dest_dir": str(config.TTS_DIR),
    }


def remove(code: str) -> None:
    """Delete a downloaded Piper voice (VOICEVOX/ja is bundled and not removed here)."""
    code = config.normalize_lang(code)
    lang = config.get_language(code)
    if lang.piper_voice is None:
        raise RuntimeError(f"{lang.name}'s voice is bundled and cannot be removed here.")
    for ext in (".onnx", ".onnx.json"):
        f = config.TTS_DIR / f"{lang.piper_voice}{ext}"
        if f.exists():
            f.unlink()
