"""Typer CLI front-end over :mod:`translator.pipeline`.

    translator langs
    translator install-lang en zh
    translator transcribe input.wav [--from auto]
    translator translate input.wav --to zh [--from auto] [--no-speak] [--out out.wav]
    translator say "你好" --lang zh --out hello.wav
    translator serve            # start the MCP server (stdio) for Claude Code
"""
from __future__ import annotations

import sys
from typing import Optional

import typer

# Windows consoles default to cp1252, which can't print Chinese/etc. Force UTF-8
# so translated text renders instead of raising UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

from . import config, pipeline, voices

app = typer.Typer(add_completion=False, help="Portable offline audio translator.")


@app.callback()
def _init() -> None:
    config.setup_logging()


@app.command("setup-models")
def setup_models(
    model: str = typer.Option("1.3B", "--model", help="Translation model: 600M | 1.3B | 3.3B"),
    voices_: str = typer.Option("en,zh,ja", "--voices", help="Comma-separated voice languages to install"),
) -> None:
    """Download everything needed to run: translation model + speech recogniser + voices."""
    import os

    from . import asr, nllb, tts, voicevox_tts

    model = model.upper()
    if model not in config.NLLB_MODELS:
        raise typer.BadParameter(f"--model must be one of {', '.join(config.NLLB_MODELS)}")
    os.environ["TRANSLATOR_NLLB_MODEL"] = model
    config.NLLB_MODEL = model
    repo, size, note = config.NLLB_MODELS[model]

    typer.echo(f"[1/3] Translation model: NLLB {model} ({size}, {note}) …")
    nllb.ensure_model()

    typer.echo("[2/3] Speech recogniser: Whisper …")
    dev = config.detect_device()
    asr._load_model(config.WHISPER_SIZE, dev.device, dev.compute_type)

    typer.echo("[3/3] Voices …")
    for raw in (v.strip() for v in voices_.split(",") if v.strip()):
        code = config.normalize_lang(raw)
        lang = config.get_language(code)
        if lang.voicevox_style is not None:
            typer.echo(f"      {lang.name} (VOICEVOX) …")
            try:
                voicevox_tts.ensure_assets()
            except Exception as e:  # noqa: BLE001
                typer.echo(f"      skipped {lang.name}: {e}")
        elif lang.piper_voice is not None:
            typer.echo(f"      {lang.name} (Piper) …")
            tts.ensure_voice(code)

    typer.echo("\nDone. Launch the app with:  translator gui")


@app.command()
def doctor() -> None:
    """Diagnose the install: models, voices, devices, compute — plus a self-test."""
    from . import devices, mt, nllb, voicevox_tts

    ok = True
    typer.echo(f"Compute device       : {config.detect_device().device}")
    typer.echo(f"MT backend           : {mt.backend()}")
    typer.echo(f"NLLB model present   : {nllb.available()}")
    typer.echo(f"Whisper model cached : {any(config.ASR_DIR.rglob('model.bin'))}")
    typer.echo(f"VOICEVOX (ja) ready  : {voicevox_tts.available()}")
    ins, outs = devices.list_input_devices(), devices.list_output_devices()
    typer.echo(f"Audio devices        : {len(ins)} input, {len(outs)} output")
    inst = voices.installed()
    typer.echo(f"Installed voices     : {', '.join(v['name'] for v in inst) or 'none'}")
    for v in inst:
        if v["kind"] == "piper":
            vid = config.get_language(v["code"]).piper_voice
            both = (config.TTS_DIR / f"{vid}.onnx").exists() and (config.TTS_DIR / f"{vid}.onnx.json").exists()
            if not both:
                typer.echo(f"  ! {v['name']} voice is incomplete (missing a file)")
                ok = False
    try:
        out = pipeline.translate_text("Hello, how are you?", "en", "ja")
        typer.echo(f"Self-test en->ja     : {out}  [OK]")
    except Exception as e:  # noqa: BLE001
        typer.echo(f"Self-test en->ja     : FAILED — {e}")
        ok = False
    typer.echo("\nEverything looks good." if ok else "\nProblems detected (see ! lines).")
    raise typer.Exit(0 if ok else 1)


@app.command()
def langs() -> None:
    """List all languages (every one translates offline via NLLB)."""
    for l in pipeline.list_languages():
        spoken = " (voice installed)" if voices.is_installed(l["code"]) else ""
        typer.echo(f"  {l['code']:<4} {l['name']}{spoken}")


@app.command("voices")
def list_voices() -> None:
    """List speech voices: installed ones and what can be downloaded."""
    for v in voices.catalog():
        mark = "[installed]" if v["installed"] else "[download]  "
        typer.echo(f"  {mark} {v['code']:<4} {v['name']}")


@app.command("get-voice")
def get_voice(
    language: str = typer.Argument(..., help="Language code, e.g. fr"),
) -> None:
    """Download a language's speech voice from the static Piper URLs (needs internet)."""
    code = config.normalize_lang(language)
    typer.echo(f"Downloading {config.get_language(code).name} voice ...")
    voices.download(code)
    typer.echo("Done.")


@app.command("remove-voice")
def remove_voice(
    language: str = typer.Argument(..., help="Language code, e.g. fr"),
) -> None:
    """Remove a downloaded speech voice."""
    code = config.normalize_lang(language)
    voices.remove(code)
    typer.echo(f"Removed {config.get_language(code).name} voice.")


@app.command("voice-url")
def voice_url(
    language: str = typer.Argument(..., help="Language code, e.g. fr"),
) -> None:
    """Print the download URLs + destination for a voice (to install it by hand)."""
    code = config.normalize_lang(language)
    info = voices.voice_files(code)
    typer.echo(f"{config.get_language(code).name} voice — download BOTH files:")
    typer.echo(f"  {info['onnx_url']}")
    typer.echo(f"  {info['json_url']}")
    typer.echo(f"then place {info['onnx_name']} and {info['json_name']} into:")
    typer.echo(f"  {info['dest_dir']}")


@app.command()
def transcribe(
    audio_path: str = typer.Argument(..., help="Input audio file"),
    from_: str = typer.Option("auto", "--from", help="Source language or 'auto'"),
) -> None:
    """Speech -> text (no translation)."""
    t = pipeline.transcribe(audio_path, from_)
    typer.echo(f"[{t.language} p={t.language_probability:.2f}] {t.text}")


@app.command()
def translate(
    audio_path: str = typer.Argument(..., help="Input audio file"),
    to: str = typer.Option(..., "--to", help="Target language code, e.g. zh"),
    from_: str = typer.Option("auto", "--from", help="Source language or 'auto'"),
    speak: bool = typer.Option(True, "--speak/--no-speak", help="Synthesize translated speech"),
    out: Optional[str] = typer.Option(None, "--out", help="Output audio path"),
    keep_punct: bool = typer.Option(False, "--keep-punct", help="Keep ! ? , (default drops them for speech)"),
) -> None:
    """Full pipeline: audio -> translated text (+ optional translated speech)."""
    r = pipeline.translate_audio(
        audio_path, target_lang=to, source_lang=from_, speak=speak, out_audio_path=out, plain=not keep_punct
    )
    typer.echo(f"source [{r.source_lang}]: {r.source_text}")
    typer.echo(f"target [{r.target_lang}]: {r.translated_text}")
    if r.out_audio_path:
        typer.echo(f"audio: {r.out_audio_path}")


@app.command("text")
def text_cmd(
    content: str = typer.Argument(..., help="Text to translate"),
    to: str = typer.Option(..., "--to", help="Target language code, e.g. ja"),
    from_: str = typer.Option("auto", "--from", help="Source language or 'auto' (guessed from script)"),
    speak: bool = typer.Option(False, "--speak", help="Also synthesize translated speech"),
    out: str = typer.Option("text.wav", "--out", help="Output audio path (with --speak)"),
) -> None:
    """Translate typed text (+ optional speech)."""
    src = pipeline.detect_text_language(content) if from_ == "auto" else config.normalize_lang(from_)
    translated = pipeline.translate_text(content, src, to)
    typer.echo(f"source [{src}]: {content}")
    typer.echo(f"target [{config.normalize_lang(to)}]: {translated}")
    if speak:
        typer.echo(f"audio: {pipeline.synthesize(translated, to, out)}")


@app.command()
def say(
    text: str = typer.Argument(..., help="Text to speak"),
    lang: str = typer.Option(..., "--lang", help="Language code, e.g. zh"),
    out: str = typer.Option("say.wav", "--out", help="Output audio path"),
) -> None:
    """Text -> speech."""
    path = pipeline.synthesize(text, lang, out)
    typer.echo(f"audio: {path}")


@app.command()
def gui() -> None:
    """Launch the desktop GUI (live mic -> translated text + speech)."""
    from .gui import main

    main()


@app.command()
def serve() -> None:
    """Start the MCP server (stdio transport) for Claude Code."""
    from .mcp_server import mcp

    mcp.run()


if __name__ == "__main__":
    app()
