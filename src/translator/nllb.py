"""NLLB-200 translation backend (high quality, offline, no torch).

Runs the NLLB-200-distilled-1.3B model on CTranslate2 (the same engine used for
Whisper/Argos) with the fast `tokenizers` tokenizer — so it needs no torch and no
transformers. One model translates directly between all supported languages (no
English pivot). GPU is used when available, with automatic CPU fallback.

Model assets (model.bin, tokenizer.json, ...) live under ``models/nllb``.
"""
from __future__ import annotations

from functools import lru_cache

from . import config


def _repo() -> str:
    """HuggingFace repo for the selected model size (falls back to 1.3B)."""
    return config.NLLB_MODELS.get(config.NLLB_MODEL, config.NLLB_MODELS["1.3B"])[0]


def available() -> bool:
    """True if the NLLB model + tokenizer are present locally (any size)."""
    return (config.NLLB_DIR / "model.bin").exists() and (config.NLLB_DIR / "tokenizer.json").exists()


def ensure_model() -> None:
    """Download the selected NLLB-200 CTranslate2 model if missing (needs internet once)."""
    if available():
        return
    from huggingface_hub import snapshot_download

    config.NLLB_DIR.mkdir(parents=True, exist_ok=True)
    snapshot_download(_repo(), local_dir=str(config.NLLB_DIR))


@lru_cache(maxsize=1)
def _load(device: str):
    import ctranslate2
    from tokenizers import Tokenizer

    translator = ctranslate2.Translator(str(config.NLLB_DIR), device=device, compute_type="auto")
    tokenizer = Tokenizer.from_file(str(config.NLLB_DIR / "tokenizer.json"))
    return translator, tokenizer


def translate(text: str, from_code: str, to_code: str) -> str:
    """Translate ``text`` between two languages using NLLB-200 (offline)."""
    src = config.get_language(from_code).nllb_code
    tgt = config.get_language(to_code).nllb_code
    if not text.strip() or src == tgt:
        return text
    try:
        return _run(text, src, tgt)
    except RuntimeError as e:
        # CUDA runtime (cuBLAS/cuDNN) missing or failing -> fall back to CPU once.
        if config.detect_device().device != "cpu" and _is_cuda_error(e):
            config.force_cpu()
            _load.cache_clear()
            return _run(text, src, tgt)
        raise


def _run(text: str, src: str, tgt: str) -> str:
    translator, tokenizer = _load(config.detect_device().device)
    # NLLB is sentence-level; translate each sentence-ish line and rejoin. Keeping
    # segments short preserves quality on multi-sentence transcripts.
    outputs = []
    for segment in _segments(text):
        enc = tokenizer.encode(segment, add_special_tokens=False)
        source = [src] + enc.tokens + ["</s>"]
        result = translator.translate_batch(
            [source], target_prefix=[[tgt]], beam_size=4, max_decoding_length=512
        )
        tokens = result[0].hypotheses[0]
        if tokens and tokens[0] == tgt:
            tokens = tokens[1:]
        ids = [tokenizer.token_to_id(t) for t in tokens]
        outputs.append(tokenizer.decode([i for i in ids if i is not None]))
    return " ".join(o.strip() for o in outputs if o.strip())


def _segments(text: str) -> list[str]:
    """Split into sentence-sized inputs for NLLB.

    Latin sentences end with punctuation + whitespace; CJK (Japanese/Chinese) end
    with 。！？ and usually NO following space, so split right after those too.
    """
    import re

    text = text.strip()
    parts = re.split(r"(?<=[.!?])\s+|(?<=[。！？])", text)
    return [p.strip() for p in parts if p and p.strip()] or [text]


def _is_cuda_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in ("cublas", "cudnn", "cuda", "gpu"))
