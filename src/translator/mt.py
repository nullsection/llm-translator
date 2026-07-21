"""MT: text-to-text translation.

Two backends: **NLLB-200** (high quality, one model for all languages, used when
its model is present under models/nllb) and **Argos Translate** (lightweight
per-pair packages, the fallback). Select explicitly with ``TRANSLATOR_MT`` =
``nllb`` | ``argos`` | ``auto`` (default: NLLB if available, else Argos).

Argos pivots non-English pairs through English; NLLB translates directly.
"""
from __future__ import annotations

import os

from . import config


def backend() -> str:
    """Return the active MT backend: 'nllb' or 'argos'."""
    choice = os.environ.get("TRANSLATOR_MT", "auto").lower()
    if choice == "argos":
        return "argos"
    from . import nllb

    if choice == "nllb" or nllb.available():
        return "nllb"
    return "argos"


def installed_packages() -> set[tuple[str, str]]:
    """Return the set of (from_code, to_code) Argos packages currently installed."""
    import argostranslate.package as pkg

    config.ensure_dirs()  # point Argos at our portable cache before querying
    return {(p.from_code, p.to_code) for p in pkg.get_installed_packages()}


def uninstall_pair(from_code: str, to_code: str) -> None:
    """Remove the direct Argos package for a pair, if installed."""
    import argostranslate.package as pkg

    config.ensure_dirs()
    from_code = config.normalize_lang(from_code)
    to_code = config.normalize_lang(to_code)
    for p in pkg.get_installed_packages():
        if p.from_code == from_code and p.to_code == to_code:
            pkg.uninstall(p)


def _installed_codes() -> set[tuple[str, str]]:
    import argostranslate.translate as t

    langs = t.get_installed_languages()
    pairs = set()
    for a in langs:
        for b in langs:
            if a.code != b.code and a.get_translation(b) is not None:
                pairs.add((a.code, b.code))
    return pairs


def _install_direct(from_code: str, to_code: str) -> bool:
    """Install a single direct package if Argos publishes one. Returns success."""
    import argostranslate.package as pkg

    pkg.update_package_index()  # requires internet
    available = pkg.get_available_packages()
    match = next(
        (p for p in available if p.from_code == from_code and p.to_code == to_code),
        None,
    )
    if match is None:
        return False
    pkg.install_from_path(match.download())
    return True


def ensure_pair(from_code: str, to_code: str) -> None:
    """Make ``from_code -> to_code`` translatable, downloading packages as needed.

    Prefers a direct package; falls back to pivoting through English.
    """
    config.ensure_dirs()
    from_code = config.normalize_lang(from_code)
    to_code = config.normalize_lang(to_code)
    if from_code == to_code:
        return

    installed = _installed_codes()
    if (from_code, to_code) in installed:
        return

    # Try a direct package first.
    if _install_direct(from_code, to_code):
        return

    # Pivot through English: from -> en, en -> to.
    for a, b in ((from_code, "en"), ("en", to_code)):
        if a != b and (a, b) not in _installed_codes():
            if not _install_direct(a, b):
                raise RuntimeError(
                    f"No Argos package available for {a} -> {b}; cannot build "
                    f"{from_code} -> {to_code}."
                )


def translate_text(text: str, from_code: str, to_code: str) -> str:
    """Translate ``text`` from ``from_code`` to ``to_code`` (offline)."""
    from_code = config.normalize_lang(from_code)
    to_code = config.normalize_lang(to_code)
    if from_code == to_code or not text.strip():
        return text

    if backend() == "nllb":
        from . import nllb

        return nllb.translate(text, from_code, to_code)

    import argostranslate.translate as t

    return t.translate(text, from_code, to_code)
