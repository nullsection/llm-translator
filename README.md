# llm-translator

Speak or type in one language and get it back as text and speech in another, fully offline on your
own PC. No API keys, no cloud, no subscription.

Built from Whisper (speech to text), NLLB-200 (translation), and Piper / VOICEVOX (text to speech).
Supports around 45 languages.

## Getting started (Windows)

### Option 1 — download and run (nothing to install)

1. Open the [Releases page](https://github.com/nullsection/llm-translator/releases/latest) and
   download a bundle:
   - `translator-offline-1.3B.zip` — recommended (about 1.9 GB).
   - The 3.3B bundle (best quality) is split into parts. Download the parts and
     `reassemble-3.3B.bat`, then double-click the script to rejoin them. See
     [dist/README.md](dist/README.md).
2. Unzip it anywhere.
3. Double-click `run-gui.bat`. The first launch sets itself up (about a minute), then the app opens.

It runs fully offline from that point on.

### Option 2 — build from source (smaller download)

```powershell
git clone https://github.com/nullsection/llm-translator
cd llm-translator
setup.bat          # installs dependencies and the 1.3B model
run-gui.bat        # launch
```

Choose a different model with `setup.bat 600M` (fastest) or `setup.bat 3.3B` (best quality).
On macOS or Linux, run `./setup.sh` then `uv run translator gui`.

## Using the app

1. Select your microphone and speaker, and choose the From and To languages.
2. Translate in one of two ways:
   - Speak: click Record, talk, then click Stop.
   - Type: enter text in the top box and click Translate text.
3. The translation appears on screen and is spoken aloud when a voice for that language is
   installed.

English, Chinese, and Japanese voices are included. For any other language, open the Voices panel
and click Download to enable speech. Languages without an installed voice show translated text only.

## Choosing a model

All three models translate roughly 45 languages offline. A larger model is somewhat more fluent but
slower and larger on disk.

| Model | Size    | Speed          | Quality                                    |
|-------|---------|----------------|--------------------------------------------|
| 600M  | ~0.6 GB | fastest        | good                                       |
| 1.3B  | ~1.4 GB | fast (~0.2 s)  | very good; matches Google when translating into English |
| 3.3B  | ~3.2 GB | ~2x slower     | best                                        |

To switch models later, delete the `models/nllb` folder and run `setup.bat <size>` again, or
download the matching bundle. A GPU is used automatically when the CUDA runtime is installed;
otherwise the app runs on CPU.

## Command line

```powershell
translator gui                                    # desktop app
translator text "Where is the station?" --to ja   # translate typed text
translator translate clip.wav --to zh --out zh.wav # translate an audio file
translator voices                                  # list and manage voices
translator get-voice fr                            # download a voice
translator doctor                                  # environment health check
```

Prefix commands with `uv run` if you built from source rather than downloading a bundle.

## Licenses

The source code is MIT licensed. The models it downloads carry their own terms. Most are
permissive; two are worth noting:

- NLLB-200 (translation) is CC-BY-NC, meaning non-commercial use only. For commercial use, set
  `TRANSLATOR_MT=argos` to switch to the unrestricted Argos engine (lower quality).
- VOICEVOX (Japanese voice) requests a credit line if you publish its audio.

See [NOTICE.md](NOTICE.md) for full details.

## Troubleshooting

- Run `translator doctor` to check the model, voices, audio devices, and run a self-test.
- See `logs/translator.log` for details of any error.
