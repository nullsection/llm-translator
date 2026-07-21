# Offline Voice Translator

Speak or type in one language → get text **and** speech in another, **fully offline** on your
PC. Desktop GUI, plus a CLI and an MCP server for Claude Code. No API keys, no cloud, no cost.

```
audio/text ─▶ Whisper (speech→text) ─▶ NLLB-200 (translate) ─▶ Piper / VOICEVOX (text→speech)
```

- **Offline & private** — everything runs locally after a one-time model download.
- **~45 languages** translate offline via one bundled NLLB-200 model — no per-language packs.
- **Speak or type** — record from a mic, or type into the box; both translate (+ speak).
- **Voices on demand** — English/Chinese (Piper) and Japanese (VOICEVOX) install by default;
  download any other language's voice from the app when you want to *hear* it.
- **Pick your model size** at setup — trade speed for quality (see below).

## Requirements

- **Windows 10/11** (recommended — Japanese speech via VOICEVOX is Windows-only).
  macOS/Linux work too, but Japanese stays text-only there.
- That's it — [`uv`](https://docs.astral.sh/uv/) and Python are installed automatically by setup.
- ~2–6 GB free disk depending on the model you pick.

## Two ways to get it

**A. Download a ready-to-go bundle (no setup, fully offline).** Grab one zip from
[`dist/`](dist/) — everything is included (Python, deps, models, voices), unzip, double-click
`run-gui.bat`. See [dist/README.md](dist/README.md).

| Bundle | Model | Size |
|--------|-------|-----:|
| `dist/translator-offline-1.3B.zip` | 1.3B (recommended) | ~2.0 GB |
| `dist/translator-offline-3.3B.zip` | 3.3B (best quality) | ~3.7 GB |

**B. Clone and build** (smaller download — grabs only the model you pick):

```powershell
git clone <this-repo-url> translator
cd translator
setup.bat            REM installs everything + the default 1.3B model (recommended)
run-gui.bat          REM launch the app
```

Want a different model? Pass it to setup:

```powershell
setup.bat 600M       REM fastest, smallest
setup.bat 1.3B       REM default — best balance
setup.bat 3.3B       REM best quality, ~2x slower, bigger
```

macOS/Linux: `./setup.sh 1.3B` then `uv run translator gui`.

## Choosing a translation model

All three are NLLB-200 (one model, ~45 languages, direct — no English pivot). Bigger = a bit
more fluent, slower, larger. Measured on a fast desktop CPU:

| Model | Download | Short sentence | Quality |
|-------|---------:|---------------:|---------|
| **600M** | ~0.6 GB | ~0.15 s | good |
| **1.3B** (default) | ~1.4 GB | ~0.22 s | very good — on par with Google into English |
| **3.3B** | ~3.2 GB | ~0.43 s | best; occasionally beats Google, ~2× slower |

To switch later: delete the `models/nllb` folder and run `setup.bat <size>` again. GPU is used
automatically if a CUDA runtime is installed, otherwise it runs on CPU.

## Using the app

- **From / To** menus list every language — all translate offline.
- **Record** to speak (Whisper auto-detects the language), or **type** into the Source box and
  press **Translate text**.
- **Voices** panel: download a Piper voice for any language to hear it spoken (needs internet
  once). Languages without an installed voice show translated text only.
- Spoken translations drop `! ? ,` by default (speech can't reliably infer them); toggle off in
  the app if you want them.

## Command line

```powershell
uv run translator gui                              # desktop app
uv run translator text "Where is the station?" --to ja --speak
uv run translator translate clip.wav --to zh --out zh.wav
uv run translator voices                           # list / manage speech voices
uv run translator get-voice fr                     # download a voice by hand
uv run translator doctor                           # diagnose the install
uv run translator serve                            # MCP server for Claude Code
```

## Licences

Source code is MIT (see `LICENSE`). Downloaded models carry their own terms — most permissive,
but note two: **NLLB-200 is CC-BY-NC (non-commercial)** and **VOICEVOX** asks for a credit line
when you publish its Japanese audio. Full details in **[NOTICE.md](NOTICE.md)**. For commercial
use, set `TRANSLATOR_MT=argos` to fall back to the unrestricted (lower-quality) Argos backend.

## Development

```powershell
uv sync --dev
uv run pytest
```
