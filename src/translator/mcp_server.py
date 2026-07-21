"""MCP server front-end (FastMCP) exposing the translation engine to Claude Code.

Because Claude is a text agent, every tool takes/returns file paths and text:
audio comes in as a path, synthesized speech goes out to a path, and the spoken
content is returned as text so Claude can read it.

Run with ``translator serve`` (stdio transport).
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import pipeline

mcp = FastMCP("translator")


@mcp.tool()
def list_languages() -> list[dict]:
    """List the language codes and names this translator supports."""
    return pipeline.list_languages()


@mcp.tool()
def transcribe(audio_path: str, source_lang: str = "auto") -> dict:
    """Transcribe speech in an audio file to text in its original language.

    Args:
        audio_path: Path to an audio file (wav/mp3/m4a/flac/...).
        source_lang: ISO code of the spoken language, or "auto" to detect.
    """
    t = pipeline.transcribe(audio_path, source_lang)
    return {"text": t.text, "language": t.language, "confidence": t.language_probability}


@mcp.tool()
def translate_text(text: str, source_lang: str, target_lang: str) -> dict:
    """Translate text from one language to another (offline).

    Args:
        text: The text to translate.
        source_lang: ISO code of the input text language.
        target_lang: ISO code to translate into.
    """
    out = pipeline.translate_text(text, source_lang, target_lang)
    return {"translated_text": out, "source_lang": source_lang, "target_lang": target_lang}


@mcp.tool()
def translate_audio(
    audio_path: str,
    target_lang: str,
    source_lang: str = "auto",
    speak: bool = True,
    out_path: str | None = None,
) -> dict:
    """Full pipeline: transcribe an audio file, translate it, and optionally
    synthesize the translation as a new audio file.

    Args:
        audio_path: Path to the input audio file.
        target_lang: ISO code to translate into (e.g. "zh", "pt", "en").
        source_lang: ISO code of the spoken language, or "auto" to detect.
        speak: If true, write translated speech to an audio file.
        out_path: Where to write the synthesized audio (auto-derived if omitted).

    Returns source_text, translated_text, and the written out_audio_path (if any).
    """
    return pipeline.translate_audio(
        audio_path,
        target_lang=target_lang,
        source_lang=source_lang,
        speak=speak,
        out_audio_path=out_path,
    ).as_dict()


@mcp.tool()
def synthesize(text: str, lang: str, out_path: str) -> dict:
    """Synthesize text into speech and write it to an audio file.

    Args:
        text: The text to speak.
        lang: ISO code of the text's language.
        out_path: Where to write the wav file.
    """
    path = pipeline.synthesize(text, lang, out_path)
    return {"out_audio_path": str(path)}


if __name__ == "__main__":
    mcp.run()
