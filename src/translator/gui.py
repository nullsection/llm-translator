"""PySide6 desktop front-end: live push-to-record voice translator.

Pick an input device (mic), source/target languages, and an output device
(speaker); press Record, speak, press Stop. The recognized source text and the
translation appear in the middle, and (if a voice is installed for the target)
the translation is spoken through the chosen output device.

Translation works offline for every listed language via NLLB — no packs. The only
optional per-language download is a **voice** for speech, managed in the Voices
panel. Heavy work runs on worker threads; the engine is shared with the CLI/MCP.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import asr, audio, config, devices, pipeline, tts, voices

_AUTO = "auto"
log = logging.getLogger("translator.gui")
# Per-process temp file for synthesized playback (avoids collisions between copies).
_TTS_TMP = Path(tempfile.gettempdir()) / f"translator_gui_{os.getpid()}.wav"


class PipelineWorker(QThread):
    """Runs ASR -> MT -> TTS off the UI thread for one recorded utterance."""

    status = Signal(str)
    heard = Signal(str, str)        # (lang, text)
    translated = Signal(str, str)   # (lang, text)
    ready_audio = Signal(object, int)  # (samples, sample_rate)
    failed = Signal(str)

    def __init__(self, samples: np.ndarray, sr: int, source_lang: str, target_lang: str, plain: bool):
        super().__init__()
        self._samples = samples
        self._sr = sr
        self._source = source_lang
        self._target = config.normalize_lang(target_lang)
        self._plain = plain

    def run(self) -> None:
        try:
            if self._samples.size == 0:
                self.status.emit("No audio captured")
                return

            self.status.emit("Transcribing…")
            t = asr.transcribe_array(self._samples, self._sr, self._source)
            src = t.language
            if not t.text.strip():
                self.status.emit("No speech detected")
                return

            if src == self._target:
                translated = t.text
            else:
                self.status.emit("Translating…")
                translated = pipeline.translate_text(t.text, src, self._target)

            # Voice input: drop punctuation speech can't reliably determine.
            heard = pipeline.clean_speech_punctuation(t.text) if self._plain else t.text
            if self._plain:
                translated = pipeline.clean_speech_punctuation(translated)
            self.heard.emit(src, heard)
            self.translated.emit(self._target, translated)

            if not translated.strip():
                self.status.emit("Ready")
                return
            if not voices.is_installed(self._target):
                name = config.get_language(self._target).name
                self.status.emit(f"Ready ({name} — text only; download its voice to hear it)")
                return

            self.status.emit("Synthesizing…")
            tts.synthesize(translated, self._target, _TTS_TMP)
            samples, sr = audio.read_wav(_TTS_TMP)
            self.ready_audio.emit(samples, sr)
            self.status.emit("Ready")
        except Exception as e:  # noqa: BLE001 - surface any engine error to the UI
            log.exception("record→translate failed")
            self.failed.emit(f"{type(e).__name__}: {e}")


class TranslateTextWorker(QThread):
    """Translate (and optionally speak) typed text — no microphone/ASR involved."""

    status = Signal(str)
    translated = Signal(str, str)      # (lang, text)
    ready_audio = Signal(object, int)  # (samples, sample_rate)
    failed = Signal(str)

    def __init__(self, text: str, source_lang: str, target_lang: str):
        super().__init__()
        self._text = text.strip()
        self._source = source_lang
        self._target = config.normalize_lang(target_lang)

    def run(self) -> None:
        try:
            if not self._text:
                self.status.emit("Type or speak something first")
                return
            src = self._source
            if src == _AUTO:
                src = pipeline.detect_text_language(self._text)

            if src == self._target:
                translated = self._text
            else:
                self.status.emit("Translating…")
                translated = pipeline.translate_text(self._text, src, self._target)
            self.translated.emit(self._target, translated)

            if not translated.strip():
                self.status.emit("Ready")
                return
            if not voices.is_installed(self._target):
                name = config.get_language(self._target).name
                self.status.emit(f"Ready ({name} — text only; download its voice to hear it)")
                return

            self.status.emit("Synthesizing…")
            tts.synthesize(translated, self._target, _TTS_TMP)
            samples, sr = audio.read_wav(_TTS_TMP)
            self.ready_audio.emit(samples, sr)
            self.status.emit("Ready")
        except Exception as e:  # noqa: BLE001
            log.exception("typed-text translate failed")
            self.failed.emit(f"{type(e).__name__}: {e}")


class VoiceWorker(QThread):
    """Downloads or removes a voice off the UI thread (download hits the network)."""

    status = Signal(str)
    done = Signal()
    failed = Signal(str)

    def __init__(self, action: str, code: str):
        super().__init__()
        self._action = action
        self._code = code

    def run(self) -> None:
        name = config.get_language(self._code).name
        try:
            if self._action == "download":
                self.status.emit(f"Downloading {name} voice…")
                voices.download(self._code)
            else:
                self.status.emit(f"Removing {name} voice…")
                voices.remove(self._code)
            self.done.emit()
        except Exception as e:  # noqa: BLE001
            log.exception("voice %s failed", self._action)
            self.failed.emit(f"{type(e).__name__}: {e}")


class TranslatorWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Offline Voice Translator")
        self.resize(640, 640)

        self._recorder = devices.Recorder()
        self._recording = False
        self._worker: PipelineWorker | None = None
        self._text_worker: TranslateTextWorker | None = None
        self._voice_worker: VoiceWorker | None = None
        self._last_audio: tuple[np.ndarray, int] | None = None

        self._build_ui()
        self._populate_devices()
        self._populate_languages()
        self._refresh_voices()

    # ---- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # Devices
        dev_box = QGroupBox("Devices")
        dev_form = QFormLayout(dev_box)
        self.in_combo = QComboBox()
        self.out_combo = QComboBox()
        dev_form.addRow("Input (mic):", self.in_combo)
        dev_form.addRow("Output (speaker):", self.out_combo)
        root.addWidget(dev_box)

        # Translate languages (every language translates offline via NLLB)
        lang_box = QGroupBox("Translate")
        lang_form = QFormLayout(lang_box)
        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
        lang_form.addRow("From:", self.from_combo)
        lang_form.addRow("To:", self.to_combo)
        self.accuracy_combo = QComboBox()
        self.accuracy_combo.addItem("Fast (base)", "base")
        self.accuracy_combo.addItem("Accurate (small — downloads once)", "small")
        self.accuracy_combo.setCurrentIndex(1 if config.WHISPER_SIZE == "small" else 0)
        self.accuracy_combo.currentIndexChanged.connect(self._change_accuracy)
        lang_form.addRow("Speech accuracy:", self.accuracy_combo)
        self.plain_check = QCheckBox("Drop ! ? , from spoken translations (speech grammar is unreliable)")
        self.plain_check.setChecked(True)
        lang_form.addRow("", self.plain_check)
        root.addWidget(lang_box)

        # Voices (optional speech output; download from the static Piper URLs)
        voice_box = QGroupBox("Voices (speech output — optional; needs internet to download)")
        voice_layout = QVBoxLayout(voice_box)
        get_row = QHBoxLayout()
        self.voice_combo = QComboBox()
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self._download_selected)
        get_row.addWidget(QLabel("Voice:"))
        get_row.addWidget(self.voice_combo, 1)
        get_row.addWidget(self.download_btn)
        voice_layout.addLayout(get_row)

        self.installed_lbl = QLabel("Installed voices: —")
        self.installed_lbl.setWordWrap(True)
        voice_layout.addWidget(self.installed_lbl)

        remove_row = QHBoxLayout()
        self.remove_combo = QComboBox()
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_selected)
        remove_row.addWidget(QLabel("Remove:"))
        remove_row.addWidget(self.remove_combo, 1)
        remove_row.addWidget(self.remove_btn)
        voice_layout.addLayout(remove_row)
        root.addWidget(voice_box)

        # Text panels — the source box is editable so you can TYPE instead of speak.
        self.heard_edit = QTextEdit()  # editable
        self.heard_edit.setPlaceholderText("Speak with Record, or type text here and press “Translate text”…")
        self.trans_edit = QTextEdit(readOnly=True)
        heard_box = QGroupBox("Source (speak or type)")
        QVBoxLayout(heard_box).addWidget(self.heard_edit)
        trans_box = QGroupBox("Translation (target)")
        QVBoxLayout(trans_box).addWidget(self.trans_edit)
        root.addWidget(heard_box, 1)
        root.addWidget(trans_box, 1)

        # Controls
        controls = QHBoxLayout()
        self.record_btn = QPushButton("● Record")
        self.record_btn.clicked.connect(self._toggle_record)
        self.text_btn = QPushButton("Translate text")
        self.text_btn.clicked.connect(self._translate_typed)
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setEnabled(False)
        self.play_btn.clicked.connect(self._replay)
        self.status_lbl = QLabel("ready")
        controls.addWidget(self.record_btn)
        controls.addWidget(self.text_btn)
        controls.addWidget(self.play_btn)
        controls.addStretch(1)
        controls.addWidget(self.status_lbl)
        root.addLayout(controls)

    def _populate_devices(self) -> None:
        ins = devices.list_input_devices()
        outs = devices.list_output_devices()
        for d in ins:
            self.in_combo.addItem(f"{d.name}{' (default)' if d.default else ''}", d.index)
        for d in outs:
            self.out_combo.addItem(f"{d.name}{' (default)' if d.default else ''}", d.index)
        for combo, items in ((self.in_combo, ins), (self.out_combo, outs)):
            for i, d in enumerate(items):
                if d.default:
                    combo.setCurrentIndex(i)
        self._has_mic = bool(ins)
        self.record_btn.setEnabled(self._has_mic)
        if not self._has_mic:
            self._set_status("no input device found")

    def _populate_languages(self) -> None:
        """Fill From/To with every language (all translate offline via NLLB)."""
        self.from_combo.addItem("Auto-detect", _AUTO)
        for code, lang in config.LANGUAGES.items():
            self.from_combo.addItem(lang.name, code)
            self.to_combo.addItem(lang.name, code)
        idx = self.to_combo.findData("ja")
        self.to_combo.setCurrentIndex(idx if idx >= 0 else 0)

    # ---- Voice management ------------------------------------------------
    def _refresh_voices(self) -> None:
        prev = self.voice_combo.currentData()
        self.voice_combo.clear()
        for v in voices.downloadable():
            mark = "  ✓ installed" if v["installed"] else ""
            self.voice_combo.addItem(f"{v['name']}{mark}", v["code"])
        idx = self.voice_combo.findData(prev)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)

        removable = [v for v in voices.installed() if v["removable"]]
        self.remove_combo.clear()
        for v in removable:
            self.remove_combo.addItem(v["name"], v["code"])
        self.remove_btn.setEnabled(bool(removable))

        names = ", ".join(v["name"] for v in voices.installed()) or "none"
        self.installed_lbl.setText(f"Installed voices: {names}")

    def _download_selected(self) -> None:
        code = self.voice_combo.currentData()
        if code:
            self._run_voice("download", code)

    def _remove_selected(self) -> None:
        code = self.remove_combo.currentData()
        if code:
            self._run_voice("remove", code)

    def _run_voice(self, action: str, code: str) -> None:
        self._set_voice_busy(True)
        self._voice_worker = VoiceWorker(action, code)
        self._voice_worker.status.connect(self._set_status)
        self._voice_worker.failed.connect(self._on_failed)
        self._voice_worker.done.connect(self._on_voice_done)
        self._voice_worker.finished.connect(lambda: self._set_voice_busy(False))
        self._voice_worker.finished.connect(self._voice_worker.deleteLater)
        self._voice_worker.start()

    def _on_voice_done(self) -> None:
        self._refresh_voices()
        self._set_status("Ready")

    def _set_voice_busy(self, busy: bool) -> None:
        self.download_btn.setEnabled(not busy)
        self.remove_btn.setEnabled(not busy and self.remove_combo.count() > 0)
        self.record_btn.setEnabled(not busy and getattr(self, "_has_mic", False))
        self.text_btn.setEnabled(not busy)

    # ---- Recording -------------------------------------------------------
    def _toggle_record(self) -> None:
        if not self._recording:
            self._start_record()
        else:
            self._stop_record()

    def _start_record(self) -> None:
        try:
            self._recorder.start(self.in_combo.currentData())
        except Exception as e:  # noqa: BLE001
            self._set_status(f"mic error: {e}")
            return
        self._recording = True
        self.record_btn.setText("■ Stop")
        self.text_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.heard_edit.clear()
        self.trans_edit.clear()
        self._set_status("Recording…")

    def _stop_record(self) -> None:
        self._recording = False
        self.record_btn.setText("● Record")
        samples, sr = self._recorder.stop()
        self.record_btn.setEnabled(False)  # re-enabled when the worker finishes
        self._set_status("Processing…")

        self._worker = PipelineWorker(
            samples, sr, self.from_combo.currentData(), self.to_combo.currentData(),
            self.plain_check.isChecked(),
        )
        self._worker.status.connect(self._set_status)
        self._worker.heard.connect(lambda lang, txt: self.heard_edit.setPlainText(txt))
        self._worker.translated.connect(self._on_translated)
        self._worker.ready_audio.connect(self._on_audio)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_record_done)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _change_accuracy(self) -> None:
        config.WHISPER_SIZE = self.accuracy_combo.currentData()
        asr._load_model.cache_clear()
        self._set_status(f"Speech model set to '{config.WHISPER_SIZE}' (loads on next recording)")

    def _on_record_done(self) -> None:
        self.record_btn.setEnabled(True)
        self.text_btn.setEnabled(True)

    # ---- Typed-text translation -----------------------------------------
    def _translate_typed(self) -> None:
        text = self.heard_edit.toPlainText()
        if not text.strip():
            self._set_status("Type some text to translate")
            return
        self.text_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        self.play_btn.setEnabled(False)
        self.trans_edit.clear()
        self._set_status("Translating…")
        self._text_worker = TranslateTextWorker(
            text, self.from_combo.currentData(), self.to_combo.currentData()
        )
        self._text_worker.status.connect(self._set_status)
        self._text_worker.translated.connect(self._on_translated)
        self._text_worker.ready_audio.connect(self._on_audio)
        self._text_worker.failed.connect(self._on_failed)
        self._text_worker.finished.connect(self._on_text_done)
        self._text_worker.finished.connect(self._text_worker.deleteLater)
        self._text_worker.start()

    def _on_text_done(self) -> None:
        self.text_btn.setEnabled(True)
        self.record_btn.setEnabled(getattr(self, "_has_mic", False))

    # ---- Worker callbacks ------------------------------------------------
    def _on_translated(self, lang: str, text: str) -> None:
        self.trans_edit.setPlainText(text)

    def _on_audio(self, samples: np.ndarray, sr: int) -> None:
        self._last_audio = (samples, sr)
        self.play_btn.setEnabled(True)
        self._play_current(samples, sr)

    def _on_failed(self, message: str) -> None:
        self._set_status(f"error: {message}")

    # ---- Playback --------------------------------------------------------
    def _replay(self) -> None:
        if self._last_audio is not None:
            self._play_current(*self._last_audio)

    def _play_current(self, samples: np.ndarray, sr: int) -> None:
        try:
            devices.play(samples, sr, self.out_combo.currentData())
            self._set_status("Speaking…")
        except Exception as e:  # noqa: BLE001
            self._set_status(f"playback error: {e}")

    def _set_status(self, text: str) -> None:
        self.status_lbl.setText(text)


def main() -> None:
    config.setup_logging()
    app = QApplication(sys.argv)
    win = TranslatorWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
