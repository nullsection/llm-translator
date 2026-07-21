"""Portable, fully-offline audio translator.

Pipeline: audio -> [ASR] speech-to-text -> [MT] translate -> [TTS] speech -> audio + text.

The heavy lifting lives in :mod:`translator.pipeline`; :mod:`translator.cli` and
:mod:`translator.mcp_server` are thin front-ends over that shared engine.
"""

__version__ = "0.1.0"
