"""Shared configuration: supported languages, local model cache paths, device detection.

Everything the pipeline needs to know about *where* things live and *what* hardware
to run on is centralised here so the ASR / MT / TTS modules stay small.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# Model cache lives inside the repo by default so the whole thing is portable
# (copy the folder, keep the models). Override with TRANSLATOR_HOME.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
HOME = Path(os.environ.get("TRANSLATOR_HOME", PROJECT_ROOT / "models"))

ASR_DIR = HOME / "asr"        # faster-whisper CTranslate2 models
TTS_DIR = HOME / "tts"        # Piper .onnx voices + .json configs
LOG_DIR = PROJECT_ROOT / "logs"  # rotating log file for diagnosing issues
# Argos manages its own package dir; we point it at HOME/argos below.
ARGOS_DIR = HOME / "argos"
VOICEVOX_DIR = HOME / "voicevox"  # VOICEVOX runtime + Open JTalk dict + .vvm models (Japanese TTS)
NLLB_DIR = HOME / "nllb"          # NLLB-200 CTranslate2 model (high-quality MT; one model, all langs)

# Selectable translation model — pick which one to download at setup time
# (TRANSLATOR_NLLB_MODEL). They share the same tokenizer/format, so the runtime
# loads whichever is present in NLLB_DIR — no version tracking needed.
NLLB_MODELS = {
    "600M": ("JustFrederik/nllb-200-distilled-600M-ct2-int8", "~0.6 GB", "fastest"),
    "1.3B": ("OpenNMT/nllb-200-distilled-1.3B-ct2-int8", "~1.4 GB", "recommended balance"),
    "3.3B": ("OpenNMT/nllb-200-3.3B-ct2-int8", "~3.2 GB", "best quality, ~2x slower"),
}
NLLB_MODEL = os.environ.get("TRANSLATOR_NLLB_MODEL", "1.3B")

# IMPORTANT: argostranslate.settings reads these env vars AT IMPORT TIME. This
# module (config) is imported before any argostranslate import, so we set them
# here at module load — otherwise Argos caches its default (wrong) package dir and
# get_installed_packages() comes back empty even though our packages are present.
os.environ.setdefault("ARGOS_PACKAGES_DIR", str(ARGOS_DIR / "packages"))
# CPU by default — GPU needs a full CUDA (cuBLAS/cuDNN) runtime that many Windows
# boxes lack. Opt in with TRANSLATOR_DEVICE=cuda.
os.environ.setdefault("ARGOS_DEVICE_TYPE", "cpu")
# Use the lightweight ONNX sentence splitter (MiniSBD, via onnxruntime we already
# ship for Piper) instead of stanza/spaCy. This lets us drop torch + spaCy (~700MB)
# from the install. See setup notes / stub-stanza shim.
os.environ.setdefault("ARGOS_CHUNK_TYPE", "MINISBD")
os.environ.setdefault("ARGOS_STANZA_AVAILABLE", "False")

# argostranslate.sbd does an unconditional `import stanza`, and stanza drags in
# torch (~500MB). Since we force MiniSBD, stanza is never actually used — so if the
# real stanza isn't installed (trimmed build), register a stub in sys.modules
# BEFORE argostranslate is imported so that hard import still succeeds.
import sys as _sys  # noqa: E402

if "stanza" not in _sys.modules:
    try:
        import stanza  # noqa: F401
    except ImportError:
        import types as _types

        def _stanza_unavailable(*_a, **_k):
            raise RuntimeError("stanza is not installed in this trimmed build (MiniSBD is used instead)")

        _stub = _types.ModuleType("stanza")
        _stub.Pipeline = _stanza_unavailable  # never called: MiniSBD is forced
        _stub.__version__ = "0.0.0-stub"
        _sys.modules["stanza"] = _stub


def ensure_dirs() -> None:
    for d in (HOME, ASR_DIR, TTS_DIR, ARGOS_DIR, ARGOS_DIR / "packages"):
        d.mkdir(parents=True, exist_ok=True)


_logging_ready = False


def setup_logging() -> None:
    """Attach a rotating file handler so errors are diagnosable after the fact.

    Best-effort: never let a read-only install folder crash the app — fall back to
    no file logging if the log directory can't be created/opened.
    """
    global _logging_ready
    if _logging_ready:
        return
    _logging_ready = True  # set first so a failure here isn't retried every call
    import logging

    root = logging.getLogger("translator")
    root.setLevel(logging.INFO)
    try:
        from logging.handlers import RotatingFileHandler

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            LOG_DIR / "translator.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        root.addHandler(handler)
    except Exception:
        root.addHandler(logging.NullHandler())  # logging must never break the app


# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Language:
    code: str                    # ISO 639-1, used by Whisper + Argos
    name: str
    piper_voice: str | None      # Piper voice id, or None (see rhasspy/piper-voices)
    nllb_code: str               # FLORES-200 code for NLLB-200 (e.g. eng_Latn)
    voicevox_style: int | None = None  # VOICEVOX style id for TTS (Japanese)


# Translation works for EVERY language below offline via NLLB-200 (one bundled
# model; nllb_code = FLORES-200). `piper_voice` is the downloadable voice used to
# *speak* the output — a language without an installed voice is text-only.
# en/ja/zh ship with their voices bundled (en/zh Piper, ja VOICEVOX); the rest are
# translate-now, download-a-voice-to-speak. Voice ids are from Piper's voices.json.
LANGUAGES: dict[str, Language] = {
    "en": Language("en", "English", "en_US-lessac-medium", "eng_Latn"),
    "ja": Language("ja", "Japanese", None, "jpn_Jpan", voicevox_style=2),  # Piper none; VOICEVOX
    "zh": Language("zh", "Chinese (Mandarin)", "zh_CN-huayan-medium", "zho_Hans"),
    "sq": Language("sq", "Albanian", "sq_AL-edon-medium", "als_Latn"),
    "ar": Language("ar", "Arabic", "ar_JO-kareem-medium", "arb_Arab"),
    "bn": Language("bn", "Bengali", "bn_BD-google-medium", "ben_Beng"),
    "bg": Language("bg", "Bulgarian", "bg_BG-dimitar-medium", "bul_Cyrl"),
    "ca": Language("ca", "Catalan", "ca_ES-upc_ona-medium", "cat_Latn"),
    "cs": Language("cs", "Czech", "cs_CZ-jirka-medium", "ces_Latn"),
    "da": Language("da", "Danish", "da_DK-talesyntese-medium", "dan_Latn"),
    "nl": Language("nl", "Dutch", "nl_BE-nathalie-medium", "nld_Latn"),
    "fi": Language("fi", "Finnish", "fi_FI-harri-medium", "fin_Latn"),
    "fr": Language("fr", "French", "fr_FR-mls-medium", "fra_Latn"),
    "ka": Language("ka", "Georgian", "ka_GE-natia-medium", "kat_Geor"),
    "de": Language("de", "German", "de_DE-mls-medium", "deu_Latn"),
    "el": Language("el", "Greek", "el_GR-joy-medium", "ell_Grek"),
    "hi": Language("hi", "Hindi", "hi_IN-pratham-medium", "hin_Deva"),
    "hu": Language("hu", "Hungarian", "hu_HU-anna-medium", "hun_Latn"),
    "is": Language("is", "Icelandic", "is_IS-bui-medium", "isl_Latn"),
    "id": Language("id", "Indonesian", "id_ID-news_tts-medium", "ind_Latn"),
    "it": Language("it", "Italian", "it_IT-paola-medium", "ita_Latn"),
    "kk": Language("kk", "Kazakh", "kk_KZ-issai-high", "kaz_Cyrl"),
    "ku": Language("ku", "Kurdish", "ku_TR-berfin_renas-medium", "kmr_Latn"),
    "lv": Language("lv", "Latvian", "lv_LV-aivars-medium", "lvs_Latn"),
    "lb": Language("lb", "Luxembourgish", "lb_LU-marylux-medium", "ltz_Latn"),
    "ml": Language("ml", "Malayalam", "ml_IN-arjun-medium", "mal_Mlym"),
    "ne": Language("ne", "Nepali", "ne_NP-chitwan-medium", "npi_Deva"),
    "no": Language("no", "Norwegian", "no_NO-nvcc-medium", "nob_Latn"),
    "fa": Language("fa", "Persian", "fa_IR-amir-medium", "pes_Arab"),
    "pl": Language("pl", "Polish", "pl_PL-darkman-medium", "pol_Latn"),
    "pt": Language("pt", "Portuguese", "pt_BR-cadu-medium", "por_Latn"),
    "ro": Language("ro", "Romanian", "ro_RO-mihai-medium", "ron_Latn"),
    "ru": Language("ru", "Russian", "ru_RU-denis-medium", "rus_Cyrl"),
    "sr": Language("sr", "Serbian", "sr_RS-serbski_institut-medium", "srp_Cyrl"),
    "sk": Language("sk", "Slovak", "sk_SK-lili-medium", "slk_Latn"),
    "sl": Language("sl", "Slovenian", "sl_SI-artur-medium", "slv_Latn"),
    "es": Language("es", "Spanish", "es_ES-davefx-medium", "spa_Latn"),
    "sw": Language("sw", "Swahili", "sw_CD-lanfrica-medium", "swh_Latn"),
    "sv": Language("sv", "Swedish", "sv_SE-alma-medium", "swe_Latn"),
    "te": Language("te", "Telugu", "te_IN-maya-medium", "tel_Telu"),
    "tr": Language("tr", "Turkish", "tr_TR-dfki-medium", "tur_Latn"),
    "uk": Language("uk", "Ukrainian", "uk_UA-ukrainian_tts-medium", "ukr_Cyrl"),
    "ur": Language("ur", "Urdu", "ur_PK-aegis_female-medium", "urd_Arab"),
    "vi": Language("vi", "Vietnamese", "vi_VN-vais1000-medium", "vie_Latn"),
    "cy": Language("cy", "Welsh", "cy_GB-bu_tts-medium", "cym_Latn"),
}


def has_voice(code: str) -> bool:
    """True if this language can be synthesized to speech (Piper or VOICEVOX)."""
    lang = get_language(code)
    return lang.piper_voice is not None or lang.voicevox_style is not None


def get_language(code: str) -> Language:
    code = normalize_lang(code)
    if code not in LANGUAGES:
        raise ValueError(
            f"Unsupported language '{code}'. Supported: {', '.join(LANGUAGES)}"
        )
    return LANGUAGES[code]


def normalize_lang(code: str) -> str:
    """Map common aliases (e.g. 'pt-br', 'zh-CN', 'english') to our canonical code."""
    c = code.strip().lower().replace("_", "-")
    aliases = {
        "zh-cn": "zh", "zh-tw": "zh", "cmn": "zh", "mandarin": "zh", "chinese": "zh",
        "english": "en", "japanese": "ja",
    }
    if c in aliases:
        return aliases[c]
    return c.split("-")[0]  # 'en-us' -> 'en'


# ---------------------------------------------------------------------------
# ASR / device settings
# ---------------------------------------------------------------------------
# Whisper size: base is a good speed/quality tradeoff on CPU. Override with
# TRANSLATOR_WHISPER (tiny|base|small|medium|large-v3).
WHISPER_SIZE = os.environ.get("TRANSLATOR_WHISPER", "base")


@dataclass(frozen=True)
class Device:
    device: str        # "cuda" or "cpu"
    compute_type: str  # ctranslate2 compute type


_force_cpu = False


def force_cpu() -> None:
    """Permanently fall back to CPU for the rest of the process (after a CUDA error)."""
    global _force_cpu
    _force_cpu = True
    detect_device.cache_clear()
    os.environ["ARGOS_DEVICE_TYPE"] = "cpu"


@lru_cache(maxsize=1)
def detect_device() -> Device:
    """Pick the compute device: use the GPU when one is present, else CPU.

    ``auto`` (default) uses CUDA if a GPU is detected; the ASR/MT layers fall back
    to CPU at runtime if the CUDA runtime libraries (cuBLAS/cuDNN) are missing — a
    common Windows gap. Force with ``TRANSLATOR_DEVICE=cuda`` or ``=cpu``.
    """
    if _force_cpu:
        return Device("cpu", "int8")
    choice = os.environ.get("TRANSLATOR_DEVICE", "auto").lower()
    if choice == "cpu":
        return Device("cpu", "int8")
    if choice == "cuda":
        return Device("cuda", "float16")
    # auto: prefer GPU if present (with runtime CPU fallback downstream).
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return Device("cuda", "float16")
    except Exception:
        pass
    return Device("cpu", "int8")
