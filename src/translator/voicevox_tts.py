"""VOICEVOX Japanese TTS backend (offline, ONNX-based, no torch).

Assets (runtime DLL, Open JTalk dictionary, .vvm voice models) live under
``models/voicevox`` and are bundled with the app. The Synthesizer is expensive to
build, so it's cached for the process. Piper handles every other language; this
module is only used for languages whose registry entry sets ``voicevox_style``.

License: VOICEVOX output requires visible credit that VOICEVOX was used (and the
character, e.g. 四国めたん). See models/voicevox for the bundled terms.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from . import config


def _dict_dir() -> Path:
    # Name is version-specific (open_jtalk_dic_utf_8-1.11); glob to stay robust.
    matches = sorted((config.VOICEVOX_DIR / "dict").glob("open_jtalk_dic*"))
    if not matches:
        raise FileNotFoundError(f"Open JTalk dictionary not found under {config.VOICEVOX_DIR / 'dict'}")
    return matches[0]


def _runtime_dll() -> Path:
    return config.VOICEVOX_DIR / "onnxruntime" / "lib" / "voicevox_onnxruntime.dll"


def _vvm_files() -> list[Path]:
    return sorted((config.VOICEVOX_DIR / "models" / "vvms").glob("*.vvm"))


def available() -> bool:
    """True if VOICEVOX can actually synthesize here.

    Requires the ``voicevox_core`` engine to be importable (it only installs on
    Windows) AND the runtime, dictionary, and a model to be present. Checking the
    module — not just the files — keeps this correct on Linux/macOS, where the files
    might exist (e.g. a reused cache) but the engine is not installed.
    """
    import importlib.util

    if importlib.util.find_spec("voicevox_core") is None:
        return False
    try:
        return _runtime_dll().exists() and _dict_dir().exists() and bool(_vvm_files())
    except FileNotFoundError:
        return False


_DOWNLOADER = "https://github.com/VOICEVOX/voicevox_core/releases/download/0.16.4/download-windows-x64.exe"


def ensure_assets() -> None:
    """Download the VOICEVOX runtime + dictionary + one voice (Windows only).

    Uses VOICEVOX's official downloader, auto-accepting its licence prompts. No-op
    if already present. On non-Windows this raises (Japanese stays text-only there).
    """
    if available():
        return
    import subprocess
    import sys

    if not sys.platform.startswith("win"):
        raise RuntimeError("VOICEVOX (Japanese speech) is Windows-only; Japanese stays text-only here.")

    import requests

    config.VOICEVOX_DIR.mkdir(parents=True, exist_ok=True)
    exe = config.VOICEVOX_DIR / "download.exe"
    if not exe.exists():
        with requests.get(_DOWNLOADER, stream=True, timeout=180) as r:
            r.raise_for_status()
            with open(exe, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 16):
                    f.write(chunk)
    # 0.vvm = 四国めたん (female default); 4.vvm = 玄野武宏 (male). The glob
    # "[04].vvm" matches exactly those two files (not 14.vvm etc.).
    subprocess.run(
        [str(exe), "--only", "onnxruntime", "dict", "models",
         "--models-pattern", "[04].vvm", "--output", str(config.VOICEVOX_DIR)],
        input=b"y\n" * 5, check=True,
    )
    exe.unlink(missing_ok=True)


@lru_cache(maxsize=1)
def _synthesizer():
    from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile

    ort = Onnxruntime.load_once(filename=str(_runtime_dll()))
    synth = Synthesizer(ort, OpenJtalk(str(_dict_dir())))
    for vvm in _vvm_files():
        with VoiceModelFile.open(str(vvm)) as model:
            synth.load_voice_model(model)
    return synth


def synthesize(text: str, style_id: int, out_path: str | Path) -> Path:
    """Synthesize Japanese ``text`` with VOICEVOX ``style_id`` to a wav file."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wav = _synthesizer().tts(text, style_id)
    out_path.write_bytes(wav)
    return out_path
