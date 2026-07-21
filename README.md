# 🗣️ llm-translator

**Speak or type in one language — get it back as text *and* speech in another. 100% offline.**
No API keys, no cloud, no subscription. Everything runs on your own PC.

Built from Whisper (speech → text), NLLB-200 (translation), and Piper / VOICEVOX (text → speech).
~45 languages.

---

## 🚀 Get started (Windows)

### ⭐ Easiest — download and run (nothing to install)

1. Open the **[Releases page](https://github.com/nullsection/llm-translator/releases/latest)** and grab a bundle:
   - **`translator-offline-1.3B.zip`** — recommended (~1.9 GB).
   - **3.3B** (best quality) is split into parts — see the quick rejoin step in
     **[dist/README.md](dist/README.md)** (download the parts + `reassemble-3.3B.bat`, double-click it).
2. **Unzip** it anywhere.
3. Double-click **`run-gui.bat`**. The first launch sets itself up (~1 minute), then the app opens.

Fully offline from there on. 🎉

### 🛠️ Or build it yourself (smaller download)

```powershell
git clone https://github.com/nullsection/llm-translator
cd llm-translator
setup.bat          REM installs everything + the 1.3B model
run-gui.bat        REM launch
```

Want a different model? `setup.bat 600M` (fastest) or `setup.bat 3.3B` (best quality).
macOS/Linux: `./setup.sh` then `uv run translator gui`.

---

## 🎧 How to use it

1. Pick your **microphone** and **speaker**, and choose **From → To** languages.
2. Translate in either way:
   - **🎙️ Speak** — click **● Record**, talk, click **■ Stop**.
   - **⌨️ Type** — type into the top box and click **Translate text**.
3. You'll see the translation on screen, and hear it **spoken aloud** (when a voice for that
   language is installed).

**Voices:** English, Chinese, and Japanese speak out of the box. For any other language, open the
**Voices** panel and click **Download** — then it speaks too. Languages without a voice just show
the translated text.

---

## 🧠 Which model should I pick?

All three translate ~45 languages offline. Bigger = a little more fluent, but slower and larger.

| Model | Size | Speed | Quality |
|-------|-----:|-------|---------|
| **600M** | ~0.6 GB | fastest | good |
| **1.3B** ⭐ | ~1.4 GB | fast (~0.2 s) | very good — matches Google *into English* |
| **3.3B** | ~3.2 GB | ~2× slower | best |

You can switch anytime: delete `models/nllb` and run `setup.bat <size>` again (or download the
matching bundle). A GPU is used automatically if you have the CUDA runtime installed; otherwise it
runs on CPU.

---

## 💻 Command line (optional)

```powershell
translator gui                                   # the desktop app
translator text "Where is the station?" --to ja  # translate typed text
translator translate clip.wav --to zh --out zh.wav
translator voices                                # list / manage voices
translator get-voice fr                          # download a voice
translator doctor                                # health check
```
(Prefix with `uv run` if you cloned rather than downloaded a bundle.)

---

## 📝 Licenses

The code is **MIT**. The models it uses have their own terms — most are permissive, but two to know:

- **NLLB-200** (translation) is **non-commercial** (CC-BY-NC). For commercial use, set
  `TRANSLATOR_MT=argos` to switch to the unrestricted (lower-quality) Argos engine.
- **VOICEVOX** (Japanese voice) asks for a small credit line if you **publish** its audio.

Full details in **[NOTICE.md](NOTICE.md)**.

---

## ❓ Trouble?

- Run **`translator doctor`** — it checks the model, voices, audio devices, and does a quick
  self-test.
- Look in **`logs/translator.log`** for details of any error.
