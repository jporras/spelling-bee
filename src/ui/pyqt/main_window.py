from __future__ import annotations

from pathlib import Path
import traceback
from datetime import datetime

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from src.application.sub_agents import SubAgent
from src.application.supervisor import SupervisorAgent
from src.infrastructure.audio.microphone_recorder import MicrophoneRecorder
from src.infrastructure.config import Settings
from src.ui.pyqt.reports import export_user_report_pdf
from src.ui.pyqt.themes import Theme, load_themes
from src.ui.pyqt.widgets import (
    CharacterAssetCatalog,
    AudioLevelMeter,
    CharacterPortrait,
    ConversationPanel,
    DialogueBubble,
    DragHandle,
    GlyphToolButton,
    UserDashboard,
)


class MainWindow(QMainWindow):
    DENSITY_LABELS = {
        "compact": "Compact",
        "classic": "Classic",
    }
    MODE_LABELS = {
        "grammar": "Grammar",
        "free": "Talk",
        "listen": "Listen",
        "spelling": "Spell",
    }

    def __init__(
        self,
        supervisor: SupervisorAgent,
        recorder: MicrophoneRecorder,
        settings: Settings,
    ) -> None:
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._supervisor = supervisor
        self._recorder = recorder
        self._settings = settings
        self._current_user_id = settings.app_user_name
        self._assets = CharacterAssetCatalog(Path(settings.base_dir) / "assets" / "characters")
        self._portraits: dict[str, CharacterPortrait] = {}
        self._manager_agent = SubAgent(
            agent_id="manager",
            display_name="Orion",
            mode="meta",
            role="Coordinates routing and presents the active shell.",
            routable=False,
        )
        self._drag_origin: QPoint | None = None
        self._selected_mode: str | None = None
        self._density_mode = "compact"
        self._busy = False
        self._recording_active = False
        self._busy_status: str | None = None
        self._recording_elapsed_seconds = 0
        self._last_target_phrase = ""
        self._last_spelling_word = ""
        self._themes = load_themes(Path(settings.base_dir) / "themes")
        self._theme_keys = list(self._themes.keys()) or ["fallback"]
        self._theme_key = settings.ui_theme if settings.ui_theme in self._themes else self._theme_keys[0]
        self._closing = False
        self._recording_timer = QTimer(self)
        self._recording_timer.setInterval(150)
        self._recording_timer.timeout.connect(self._update_recording_feedback)
        self._build_ui()
        self._install_shortcuts()
        self._refresh_dashboard()
        self._show_mode_preview()

    def _build_ui(self) -> None:
        self.setWindowTitle("Whisper Ukagaka")
        self.resize(940, 680)
        self._apply_window_flags()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        root = QWidget(self)
        root.setObjectName("root")
        self.setCentralWidget(root)

        root_layout = QVBoxLayout(root)
        self._root_layout = root_layout

        top_bar = QHBoxLayout()
        top_bar.setSpacing(6)
        self._top_bar = top_bar

        self.mode_buttons: dict[str, QPushButton] = {}
        for mode, label in self.MODE_LABELS.items():
            button = QPushButton(label, self)
            button.clicked.connect(lambda checked=False, selected_mode=mode: self._select_mode(selected_mode))
            self.mode_buttons[mode] = button
            top_bar.addWidget(button)

        top_bar.addStretch()

        self.drag_handle = DragHandle(self)
        top_bar.addWidget(self.drag_handle)

        self.menu_button = GlyphToolButton("menu", self)
        self.menu_button.setToolTip("Menu")
        self.menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._build_options_menu()
        top_bar.addWidget(self.menu_button)

        root_layout.addLayout(top_bar)

        shell_row = QHBoxLayout()
        self._shell_row = shell_row

        self.dialogue = DialogueBubble(self)
        self.dialogue.setObjectName("speechBubble")
        self.bubble_holder = QWidget(self)
        self._bubble_layout = QVBoxLayout(self.bubble_holder)
        self._bubble_layout.addStretch(2)
        self._bubble_layout.addWidget(self.dialogue, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self._bubble_layout.addStretch(5)
        shell_row.addStretch(1)
        shell_row.addWidget(self.bubble_holder, stretch=6)

        self.send_button = GlyphToolButton("send", self)
        self.send_button.setToolTip("Send")
        self.send_button.clicked.connect(self._handle_send)

        self.record_button = GlyphToolButton("listen", self)
        self.record_button.setToolTip("Listen")
        self.record_button.clicked.connect(self._handle_record)

        self.character_holder = QWidget(self)
        holder_layout = QVBoxLayout(self.character_holder)
        holder_layout.setContentsMargins(0, 0, 0, 24)
        holder_layout.setSpacing(0)
        holder_layout.addStretch()

        manager_portrait = CharacterPortrait(self._manager_agent, self._assets, self)
        manager_portrait.hide()
        self._portraits["manager"] = manager_portrait
        holder_layout.addWidget(
            manager_portrait,
            alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
        )

        for sub_agent in self._supervisor.available_agents():
            portrait = CharacterPortrait(sub_agent, self._assets, self)
            portrait.hide()
            self._portraits[sub_agent.agent_id] = portrait
            holder_layout.addWidget(
                portrait,
                alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
            )

        shell_row.addWidget(self.character_holder, stretch=5)
        root_layout.addLayout(shell_row, stretch=1)

        self.input_line = QLineEdit(self)
        self.input_line.setPlaceholderText("Say something to your ukagaka...")
        self.input_line.returnPressed.connect(self._handle_send)

        action_row = QHBoxLayout()
        self._action_row = action_row
        self.recording_panel = QFrame(self)
        self.recording_panel.setObjectName("recordingPanel")
        self.recording_panel.setVisible(False)
        recording_layout = QHBoxLayout(self.recording_panel)
        recording_layout.setContentsMargins(10, 4, 10, 4)
        recording_layout.setSpacing(8)
        self.recording_status = QPushButton("REC", self.recording_panel)
        self.recording_status.setEnabled(False)
        self.recording_status.setObjectName("recordingStatus")
        self.recording_timer_label = QPushButton("00:00", self.recording_panel)
        self.recording_timer_label.setEnabled(False)
        self.recording_timer_label.setObjectName("recordingTimer")
        self.recording_meter = AudioLevelMeter(self.recording_panel)
        self.cancel_record_button = GlyphToolButton("cancel", self.recording_panel)
        self.cancel_record_button.setToolTip("Cancel recording")
        self.cancel_record_button.clicked.connect(self._cancel_recording_flow)
        recording_layout.addWidget(self.recording_status)
        recording_layout.addWidget(self.recording_timer_label)
        recording_layout.addWidget(self.recording_meter, stretch=1)
        recording_layout.addWidget(self.cancel_record_button)
        action_row.addWidget(self.input_line, stretch=1)
        action_row.addWidget(self.recording_panel)
        action_row.addWidget(self.send_button)
        action_row.addWidget(self.record_button)
        root_layout.addLayout(action_row)
        self._input_line_normal_max_width = 16777215

        self.debug_panel = QFrame(self)
        self.debug_panel.setVisible(False)
        debug_layout = QVBoxLayout(self.debug_panel)
        self._debug_layout = debug_layout

        self.conversation = ConversationPanel(self)
        self.conversation.setMinimumHeight(130)
        self.dashboard = UserDashboard(self)
        debug_layout.addWidget(self.conversation)
        debug_layout.addWidget(self.dashboard)
        root_layout.addWidget(self.debug_panel)

        self._apply_density_mode()
        self._apply_theme()
        self._refresh_mode_buttons()
        self._show_mode_preview()

    def _install_shortcuts(self) -> None:
        close_shortcut = QShortcut(QKeySequence("Ctrl+Q"), self)
        close_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        close_shortcut.activated.connect(self._quit_application)

        start_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        start_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        start_shortcut.activated.connect(self._handle_start_shortcut)

    def _handle_send(self) -> None:
        if self._busy:
            return
        text = self.input_line.text().strip()
        if not text:
            return

        if self._selected_mode == "free" and text.lower() in {"start", "iniciar", "begin", "empezar"}:
            self.conversation.append_message("You", text)
            self._start_talk_phrase()
            self.input_line.clear()
            return

        self._set_busy(True, "Thinking...")
        try:
            user_id = self._get_user_id()
            self.conversation.append_message("You", text)
            self._show_active_agent("manager", "special", "Thinking...", text)

            result = self._supervisor.handle(
                content=text,
                preferred_mode=self._selected_mode,
                user_id=user_id,
            )
            self._apply_result(result)
            self.input_line.clear()
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def _handle_start_shortcut(self) -> None:
        if self._busy or self._recording_active:
            return

        if self._selected_mode == "free":
            self.conversation.append_message("You", "start")
            self._start_talk_phrase()
            return

        if self._selected_mode in {"listen", "spelling"}:
            self._submit_start_command()
            return

        self._show_active_agent(
            "manager",
            "special",
            "Shortcut",
            "Ctrl+N works like writing start in the practice modes that need a first prompt: Talk, Listen, or Spell.",
        )

    def _submit_start_command(self) -> None:
        self._set_busy(True, "Starting...")
        try:
            user_id = self._get_user_id()
            self.conversation.append_message("You", "start")
            result = self._supervisor.handle(
                content="start",
                preferred_mode=self._selected_mode,
                user_id=user_id,
            )
            self._apply_result(result)
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def _handle_record(self) -> None:
        if self._busy and not self._recording_active:
            return
        if self._recording_active:
            self._stop_recording_flow()
            return
        self._start_recording_flow()

    def _start_recording_flow(self) -> None:
        try:
            message = self._recorder.start_recording()
            self._recording_active = True
            self._recording_elapsed_seconds = 0
            self._set_recording_visual_state(True)
            self._recording_timer.start()
            self.conversation.append_message("System", message)
            agent_id, status, text = self._recording_prompt_for_mode()
            self._show_active_agent(
                agent_id,
                "special",
                status,
                text,
            )
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)

    def _stop_recording_flow(self) -> None:
        self._recording_active = False
        self._recording_timer.stop()
        self._set_recording_visual_state(False)
        self._set_busy(True, "Processing audio...")
        try:
            user_id = self._get_user_id()
            self._show_active_agent("transcription", "special", "Processing...", "Transcribing the captured audio.")
            recording = self._recorder.stop_recording()
            self.conversation.append_message("Recorder", recording.message)
            result = self._supervisor.handle_audio(
                audio_path=str(recording.audio_path),
                preferred_mode=self._selected_mode,
                user_id=user_id,
            )
            self._apply_result(result)
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def _cancel_recording_flow(self) -> None:
        if not self._recording_active:
            return
        self._recording_timer.stop()
        self._recording_active = False
        self._recorder.cancel_recording()
        self._recording_elapsed_seconds = 0
        self._set_recording_visual_state(False)
        self.conversation.append_message("System", "Recording cancelled.")
        self._show_mode_preview()

    def _update_recording_feedback(self) -> None:
        if not self._recording_active:
            return
        self._recording_elapsed_seconds += 0.15
        total_seconds = int(self._recording_elapsed_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        pulse_on = (int(self._recording_elapsed_seconds * 2) % 2) == 0
        self.recording_status.setText("REC" if pulse_on else " ")
        self.recording_timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        self.recording_meter.set_level(self._recorder.current_level)

    def _apply_result(self, result) -> None:
        transcript = result.metadata.get("transcript", "")
        if transcript:
            self.conversation.append_message("Pulse", str(transcript))
        self.conversation.append_message("Orion", result.final_text)
        if "explanation" in result.metadata:
            self.conversation.append_message("Note", str(result.metadata["explanation"]))
        if result.metadata.get("evaluation_errors"):
            self.conversation.append_message("Vera", ", ".join(result.metadata["evaluation_errors"]))
        if "next_focus" in result.metadata:
            self.conversation.append_message("Atlas", str(result.metadata["next_focus"]))
        if result.metadata.get("target_phrase"):
            self._last_target_phrase = str(result.metadata["target_phrase"])
        if result.metadata.get("target_word"):
            self._last_spelling_word = str(result.metadata["target_word"])

        selected_agent = str(result.metadata.get("selected_agent", "manager"))
        shell_agent = selected_agent if selected_agent in self._portraits else "manager"
        shell_expression = self._expression_for_result(shell_agent, result.metadata)
        shell_status = self._status_for_result(result)
        shell_text = self._balloon_text_for_result(result)
        self._show_active_agent(shell_agent, shell_expression, shell_status, shell_text)
        self._update_dashboard(result.metadata)
        if result.metadata.get("speak_after_display"):
            text_to_speak = str(result.metadata["speak_after_display"])
            QTimer.singleShot(180, lambda: self._speak_after_display(text_to_speak))

    def _speak_after_display(self, text: str) -> None:
        try:
            self.dialogue.status_label.setText("Speaking...")
            self._supervisor.speak_text(text, user_id=self._get_user_id())
            self.dialogue.status_label.setText("Talk mode")
        except Exception as exc:  # noqa: BLE001
            self.conversation.append_message("System", f"Voice preview error: {exc}")

    def _show_active_agent(self, agent_id: str, expression: str, status: str, text: str) -> None:
        for key, portrait in self._portraits.items():
            portrait.setVisible(key == agent_id)
            if key == agent_id:
                portrait.set_state(expression)
        display_name = self._portraits[agent_id].sub_agent.display_name
        self.dialogue.set_message(display_name, status, text, expression)

    def _expression_for_result(self, agent_id: str, metadata: dict[str, object]) -> str:
        errors = metadata.get("evaluation_errors", [])
        score = float(metadata.get("evaluation_score", 0.8))
        if agent_id == "manager":
            if errors:
                return "sad"
            return "smile" if score >= 0.9 else "special"
        if agent_id == "grammar":
            if len(errors) >= 2:
                return "angry"
            if len(errors) == 1:
                return "sad"
            if score >= 0.92:
                return "smile"
            if score >= 0.8:
                return "special"
            return "normal"
        if agent_id == "voice":
            return "smile"
        if agent_id == "transcription":
            transcript = str(metadata.get("transcript", ""))
            if transcript.startswith("[missing-audio]") or transcript.startswith("[empty transcription]"):
                return "angry"
            if transcript.startswith("[stub transcription]") or transcript.startswith("["):
                return "sad"
            if len(transcript.split()) >= 4:
                return "smile"
            return "special"
        if agent_id == "spelling":
            feedback = str(metadata.get("feedback", ""))
            target_word = str(metadata.get("target_word", ""))
            letter_count = int(metadata.get("letter_count", "0"))
            if "No recognizable letters found" in feedback or not target_word:
                return "angry"
            if letter_count <= 2:
                return "sad"
            if letter_count >= 5:
                return "smile"
            return "special"
        if errors:
            return "sad"
        if score >= 0.9:
            return "smile"
        if score >= 0.75:
            return "normal"
        return "angry"

    def _status_for_result(self, result) -> str:
        selected_mode = result.selected_mode
        if selected_mode == "grammar":
            return "Grammar review"
        if selected_mode == "listen":
            return "Listening feedback"
        if selected_mode == "spelling":
            return "Letter-by-letter check"
        if selected_mode == "tts":
            return "Speech playback"
        return "Conversation flow"

    def _balloon_text_for_result(self, result) -> str:
        if "explanation" in result.metadata:
            return f"{result.final_text}\n\n{result.metadata['explanation']}"
        if "next_focus" in result.metadata:
            return f"{result.final_text}\n\nNext: {result.metadata['next_focus']}"
        return result.final_text

    def _select_mode(self, mode: str) -> None:
        if self._busy:
            return
        self._selected_mode = mode
        self._refresh_header_summary()
        self._refresh_mode_buttons()
        self._show_mode_preview()

    def _start_talk_phrase(self) -> None:
        self._set_busy(True, "Preparing phrase...")
        try:
            result = self._supervisor.handle(
                content="new phrase",
                preferred_mode="free",
                user_id=self._get_user_id(),
            )
            self._apply_result(result)
        except Exception as exc:  # noqa: BLE001
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self._busy = busy
        self._busy_status = status if busy else None
        self.input_line.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.record_button.setEnabled(not busy or self._recording_active)
        self.menu_button.setEnabled(not busy)
        for button in self.mode_buttons.values():
            button.setEnabled(not busy)
        if busy and status:
            self.dialogue.status_label.setText(status)
        self._apply_busy_visual_state()

    def _set_recording_visual_state(self, active: bool) -> None:
        theme = self._current_theme()
        if active:
            record_bg = theme.get("recording_button_bg", "#b42318")
            record_fg = theme.get("recording_button_fg", "#fff7ed")
            self.record_button.setToolTip("Stop listening")
            self.record_button.setStyleSheet(
                f"QToolButton {{ background: {record_bg}; color: {record_fg}; border: 1px solid {record_bg}; border-radius: 14px; }}"
            )
            self.record_button.set_surface_color(record_bg)
            self.recording_panel.setVisible(True)
            self.input_line.setMaximumWidth(190 if self._density_mode == "compact" else 260)
            self.recording_status.setText("REC")
            self.recording_timer_label.setText("00:00")
            self.recording_meter.set_active(True)
            self.recording_meter.set_level(0.05)
            self.input_line.setEnabled(False)
            self.send_button.setEnabled(False)
            self.menu_button.setEnabled(False)
            for button in self.mode_buttons.values():
                button.setEnabled(False)
        else:
            self.record_button.setToolTip("Listen")
            self.recording_panel.setVisible(False)
            self.input_line.setMaximumWidth(self._input_line_normal_max_width)
            self.recording_meter.set_active(False)
            self.recording_meter.set_level(0.0)
            self.recording_status.setText("REC")
            self.recording_timer_label.setText("00:00")
            if not self._busy:
                self.record_button.setStyleSheet("")
                self.record_button.set_surface_color(theme.get('input_bg', '#fffdf8'))
                self.input_line.setEnabled(True)
                self.send_button.setEnabled(True)
                self.menu_button.setEnabled(True)
                for button in self.mode_buttons.values():
                    button.setEnabled(True)
            self._refresh_mode_buttons()

    def _show_error(self, exc: Exception) -> None:
        self.conversation.append_message("System", f"Error: {exc}")
        self._show_active_agent(
            "manager",
            "sad",
            "Error",
            "Something went wrong while processing your request.",
        )
        traceback.print_exc()

    def _show_mode_preview(self) -> None:
        agent_id, status, text = {
            "grammar": (
                "grammar",
                "Grammar review",
                (
                    "I am Nova.\n\n"
                    "In Grammar mode, write or say one sentence you want to practice.\n\n"
                    "I will read your idea carefully, check whether the words and grammar sound natural, "
                    "show you a corrected version, and explain the most important mistake in simple terms.\n\n"
                    "If your sentence is already correct, I can still suggest a smoother or more natural way to express it."
                ),
            ),
            "free": (
                "conversation",
                "Talk mode",
                (
                    "I am Nova.\n\n"
                    "In Talk mode I will give you one phrase to pronounce.\n\n"
                    "You should repeat the phrase by voice.\n\n"
                    "Then I will compare your attempt and help you retry or move to a new phrase.\n\n"
                    "To begin, write: start"
                ),
            ),
            "listen": (
                "transcription",
                "Listen mode",
                (
                    "I am Pulse.\n\n"
                    "In Listen mode I will share a short paragraph and ask one question about it.\n\n"
                    "You answer in your own words, and then I score how close your answer is to the main idea.\n\n"
                    "To begin, write: start"
                ),
            ),
            "spelling": (
                "spelling",
                "Spelling mode",
                (
                    "I am Glyph.\n\n"
                    "In Spell mode you can give me a word list, or I can propose words for you.\n\n"
                    "Then you spell the selected word letter by letter, and I tell you whether to retry or continue.\n\n"
                    "Write a list like: apple, window, garden\n\n"
                    "Or write: start"
                ),
            ),
        }.get(
            self._selected_mode,
            (
                "manager",
                "Welcome",
                self._orion_welcome_text(),
            ),
        )
        self._show_active_agent(agent_id, "idle", status, text)

    def _orion_welcome_text(self) -> str:
        snapshot = self._supervisor.user_snapshot(self._get_user_id())
        profile = snapshot.get("profile", {})
        user_name = str(profile.get("user_id", self._get_user_id()) or "there").strip()
        display_name = user_name[:1].upper() + user_name[1:] if user_name else "there"
        level = profile.get("difficulty_level", "B1")
        interaction_count = int(snapshot.get("interaction_count", 0))
        average_score = int(float(snapshot.get("average_score", 0.0)) * 100)
        recent_errors = profile.get("recent_errors", []) or []
        notes = profile.get("notes", []) or []
        last_session = snapshot.get("last_session") or {}

        if interaction_count == 0:
            progress_line = (
                "I do not have practice history for you yet, so I will start gently and adapt as you work."
            )
        else:
            progress_line = (
                f"I remember {interaction_count} practice interactions. "
                f"Your current level is {level}, with an average score near {average_score}%."
            )

        if last_session:
            resume_line = (
                f"Last time you were in {last_session.get('selected_mode', 'practice')} mode. "
                f"I would continue with: {last_session.get('next_focus', 'a short warm-up')}."
            )
        else:
            resume_line = "There is no previous session checkpoint yet."

        if recent_errors:
            weakness_line = (
                "I have noticed this area recently: "
                f"{str(recent_errors[-1]).replace('-', ' ')}."
            )
        elif notes:
            weakness_line = str(notes[-1])
        else:
            weakness_line = "Tip: short daily practice works better than long sessions with no review."

        recommendation = self._recommended_mode_from_snapshot(snapshot, recent_errors)
        return (
            f"Hi {display_name}, I am Orion.\n\n"
            "I coordinate your ukagakas and keep track of your progress.\n\n"
            f"{progress_line}\n\n"
            f"{resume_line}\n\n"
            f"{weakness_line}\n\n"
            f"My suggestion for today: try {recommendation}."
        )

    def _recommended_mode_from_snapshot(
        self,
        snapshot: dict[str, object],
        recent_errors: list[str],
    ) -> str:
        if any("spelling" in str(error) for error in recent_errors):
            return "Spell"
        if any("pronunciation" in str(error) for error in recent_errors):
            return "Talk"
        if any("listening" in str(error).lower() for error in recent_errors):
            return "Listen"
        mode_usage = snapshot.get("mode_usage", {}) or {}
        if int(mode_usage.get("listen", 0)) == 0:
            return "Listen"
        if int(mode_usage.get("spell", 0)) == 0:
            return "Spell"
        return "Grammar"

    def _recording_prompt_for_mode(self) -> tuple[str, str, str]:
        return {
            "grammar": (
                "grammar",
                "Listening for grammar",
                "Say your sentence naturally. I will transcribe it, review the grammar, and suggest a better phrasing if needed.",
            ),
            "free": (
                "conversation",
                "Listening for talk",
                (
                    f"Repeat this phrase:\n\n{self._last_target_phrase}\n\n"
                    "Click the microphone again when you finish."
                    if self._last_target_phrase
                    else "Repeat the phrase aloud. I will compare what I hear with the target phrase and help you improve it."
                ),
            ),
            "listen": (
                "transcription",
                "Listening for answer",
                "Answer the listening question in your own words. Click the microphone again when you finish.",
            ),
            "spelling": (
                "spelling",
                "Listening for spelling",
                (
                    f"Spell this word letter by letter:\n\n{self._last_spelling_word}\n\n"
                    "Click the microphone again when you finish."
                    if self._last_spelling_word
                    else "Spell the word letter by letter. Click the microphone again when you have finished spelling it."
                ),
            ),
        }.get(
            self._selected_mode,
            ("transcription", "Listening...", "Speak now and click the microphone again when you want to stop."),
        )

    def _refresh_mode_buttons(self) -> None:
        theme = self._current_theme()
        for mode, button in self.mode_buttons.items():
            active = mode == self._selected_mode
            background = theme.get('button_bg', 'rgba(255,255,255,0.96)')
            foreground = theme.get('button_fg', '#13212f')
            border = theme.get('button_border', '#cbbca7')
            weight = 600
            if active:
                background = theme.get('button_active_bg', '#13212f')
                foreground = theme.get('button_active_fg', '#fefae0')
                border = theme.get('button_active_border', '#13212f')
                weight = 700
            if self._busy:
                if active:
                    background = theme.get('busy_button_bg', '#6b7280')
                    foreground = theme.get('busy_button_fg', '#f8fafc')
                    border = theme.get('busy_button_border', '#6b7280')
                else:
                    background = theme.get('busy_button_muted_bg', '#d6dde3')
                    foreground = theme.get('busy_button_muted_fg', '#607080')
                    border = theme.get('busy_button_muted_border', '#c5ced6')
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background: {background};
                    color: {foreground};
                    font-weight: {weight};
                    border: 1px solid {border};
                    border-radius: 16px;
                    padding: 6px 12px;
                }}
                """
            )

    def _apply_busy_visual_state(self) -> None:
        theme = self._current_theme()
        if self._busy:
            active_bg = theme.get('busy_button_bg', '#6b7280')
            active_fg = theme.get('busy_button_fg', '#f8fafc')
            muted_bg = theme.get('busy_button_muted_bg', '#d6dde3')
            muted_fg = theme.get('busy_button_muted_fg', '#607080')
            muted_border = theme.get('busy_button_muted_border', '#c5ced6')
            self.send_button.setStyleSheet(
                f"QToolButton {{ background: {active_bg}; color: {active_fg}; border: 1px solid {active_bg}; border-radius: 14px; }}"
            )
            self.record_button.setStyleSheet(
                f"QToolButton {{ background: {active_bg}; color: {active_fg}; border: 1px solid {active_bg}; border-radius: 14px; }}"
            )
            self.send_button.set_surface_color(active_bg)
            self.record_button.set_surface_color(active_bg)
            self.input_line.setStyleSheet(
                f"QLineEdit {{ background: {muted_bg}; color: {muted_fg}; border: 1px solid {muted_border}; border-radius: 14px; }}"
            )
            self.input_line.setPlaceholderText(self._busy_status or "Working...")
        else:
            self.send_button.setStyleSheet("")
            self.send_button.set_surface_color(theme.get('input_bg', '#fffdf8'))
            if not self._recording_active:
                self.record_button.setStyleSheet("")
                self.record_button.set_surface_color(theme.get('input_bg', '#fffdf8'))
            self.input_line.setStyleSheet("")
            self.input_line.setPlaceholderText("Say something to your ukagaka...")
        self._refresh_mode_buttons()

    def _toggle_dashboard(self) -> None:
        self.debug_panel.setVisible(not self.debug_panel.isVisible())
        self._apply_density_mode()
        self._refresh_header_summary()

    def _export_report(self) -> None:
        snapshot = self._supervisor.persist_exit_summary(self._get_user_id())
        reports_dir = Path(self._settings.base_dir) / "runtime" / "reports"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._get_user_id()}_report_{timestamp}.pdf"
        output_path = export_user_report_pdf(snapshot, reports_dir / filename)
        self.dashboard.update_snapshot(snapshot)
        self.conversation.append_message("System", f"Report saved to {output_path}")
        self._show_active_agent(
            "manager",
            "smile",
            "Report ready",
            f"I saved your progress report to:\n{output_path}",
        )

    def _cycle_theme(self) -> None:
        if not self._theme_keys:
            return
        current_index = self._theme_keys.index(self._theme_key)
        self._theme_key = self._theme_keys[(current_index + 1) % len(self._theme_keys)]
        self._apply_theme()
        self._refresh_mode_buttons()

    def _cycle_density(self) -> None:
        self._density_mode = "classic" if self._density_mode == "compact" else "compact"
        self._apply_density_mode()
        self._apply_theme()
        self._refresh_mode_buttons()

    def _toggle_pin(self) -> None:
        flags = self.windowFlags()
        if flags & Qt.WindowType.WindowStaysOnTopHint:
            flags = flags & ~Qt.WindowType.WindowStaysOnTopHint
        else:
            flags = flags | Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.show()
        self._refresh_header_summary()

    def _apply_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )

    def _refresh_dashboard(self) -> None:
        snapshot = self._supervisor.user_snapshot(self._get_user_id())
        self.dashboard.update_snapshot(snapshot)

    def _update_dashboard(self, metadata: dict[str, object]) -> None:
        snapshot = self._supervisor.user_snapshot(self._current_user_id)
        self.dashboard.update_snapshot(snapshot, metadata)

    def _get_user_id(self) -> str:
        user_id = self._current_user_id or "guest"
        self._build_options_menu()
        return user_id

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape and self._recording_active:
            self._cancel_recording_flow()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._recording_active:
            self._cancel_recording_flow()
        if not self._closing:
            self._closing = True
            try:
                snapshot = self._supervisor.persist_exit_summary(self._get_user_id())
                self.dashboard.update_snapshot(snapshot)
            except Exception as exc:  # noqa: BLE001
                self.conversation.append_message("System", f"Close summary error: {exc}")
        super().closeEvent(event)
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _current_theme(self) -> Theme:
        theme = self._themes.get(self._theme_key)
        if theme is not None:
            return theme
        return Theme(name="Fallback", values={})

    def _apply_theme(self) -> None:
        theme = self._current_theme()
        self.menu_button.setToolTip("Menu")
        compact = self._density_mode == "compact"
        tool_height = 24 if compact else 28
        tool_width = 28 if compact else 32
        tool_radius = 8 if compact else 10
        tool_padding = "3px 6px" if compact else "4px 8px"
        field_height = 30 if compact else 34
        field_radius = 12 if compact else 14
        field_padding = "4px 10px" if compact else "6px 12px"
        field_font = 12 if compact else 13
        frame_radius = 16 if compact else 20
        self.centralWidget().setStyleSheet(
            f"""
            QWidget#root {{
                background: {theme.get('root_bg', 'rgba(0, 0, 0, 0)')};
            }}
            QToolButton {{
                min-height: {tool_height}px;
                min-width: {tool_width}px;
                border-radius: {tool_radius}px;
                background: {theme.get('window_control_bg', 'rgba(19, 33, 47, 0.82)')};
                color: {theme.get('window_control_fg', '#fefae0')};
                padding: {tool_padding};
            }}
            QLineEdit, QPushButton {{
                min-height: {field_height}px;
                border-radius: {field_radius}px;
                border: 1px solid {theme.get('input_border', '#cbbca7')};
                background: {theme.get('input_bg', 'rgba(255,255,255,0.92)')};
                color: {theme.get('input_fg', '#13212f')};
                padding: {field_padding};
                font-size: {field_font}px;
            }}
            QLineEdit {{
                selection-background-color: {theme.get('input_selection_bg', '#355070')};
                selection-color: {theme.get('input_selection_fg', '#fefae0')};
            }}
            QPushButton {{
                color: {theme.get('button_fg', '#13212f')};
                font-weight: 600;
            }}
            QFrame {{
                background: {theme.get('frame_bg', 'rgba(255, 253, 248, 0.97)')};
                border-radius: {frame_radius}px;
            }}
            QFrame#recordingPanel {{
                background: {theme.get('panel_bg', 'rgba(255,253,248,0.97)')};
                border: 1px solid {theme.get('panel_border', '#d9cbb4')};
                border-radius: 14px;
            }}
            QPushButton#recordingStatus, QPushButton#recordingTimer {{
                min-height: 22px;
                border-radius: 10px;
                border: none;
                background: transparent;
                color: {theme.get('panel_text', '#213547')};
                font-weight: 700;
                padding: 0 4px;
            }}
            """
        )
        self.drag_handle.apply_theme(theme)
        self.menu_button.apply_theme(theme, use_window_palette=True)
        self.send_button.apply_theme(theme)
        self.record_button.apply_theme(theme)
        self.cancel_record_button.apply_theme(theme)
        self.recording_meter.apply_theme(theme)
        self.dialogue.apply_theme(theme)
        self.conversation.apply_theme(theme)
        self.dashboard.apply_theme(theme)
        self._apply_busy_visual_state()
        if self._recording_active:
            self._set_recording_visual_state(True)
        self._refresh_header_summary()

    def _apply_density_mode(self) -> None:
        compact = self._density_mode == "compact"
        self._root_layout.setContentsMargins(10, 8, 10, 12) if compact else self._root_layout.setContentsMargins(14, 12, 14, 16)
        self._root_layout.setSpacing(4 if compact else 6)
        self._top_bar.setContentsMargins(0, 0, 0, 0)
        self._shell_row.setSpacing(0 if compact else 2)
        self._shell_row.setStretch(1, 6 if compact else 5)
        self._shell_row.setStretch(2, 5 if compact else 6)
        self._action_row.setContentsMargins(0, 0, 0, 2 if compact else 4)
        self._action_row.setSpacing(4 if compact else 8)
        self._bubble_layout.setContentsMargins(0, 34 if compact else 48, 0, 0)
        self._bubble_layout.setSpacing(0)
        self._debug_layout.setContentsMargins(10, 10, 10, 10) if compact else self._debug_layout.setContentsMargins(12, 12, 12, 12)
        self._debug_layout.setSpacing(8 if compact else 10)
        self.dialogue.setMinimumWidth(515 if compact else 640)
        self.dialogue.setMaximumWidth(650 if compact else 780)
        self.dialogue.setMinimumHeight(320 if compact else 410)
        self.dialogue.set_density(compact)
        self.conversation.set_density(compact)
        self.dashboard.set_density(compact)
        self.character_holder.setMinimumSize(230, 390) if compact else self.character_holder.setMinimumSize(420, 650)
        input_height = 32 if compact else 38
        button_size = 32 if compact else 38
        self.input_line.setMinimumHeight(input_height)
        self.send_button.setFixedSize(button_size, button_size)
        self.record_button.setFixedSize(button_size, button_size)
        self.cancel_record_button.setFixedSize(button_size, button_size)
        self.recording_panel.setFixedHeight(button_size + 2)
        self.recording_panel.setMinimumWidth(180 if compact else 220)
        for button in self.mode_buttons.values():
            button.setMinimumHeight(28 if compact else 34)
            button.setMinimumWidth(72 if compact else 86)
        for portrait in self._portraits.values():
            portrait.set_density(compact)
        self.setMinimumSize(0, 0)
        if compact:
            self.resize(700, 660 if self.debug_panel.isVisible() else 500)
        else:
            self.resize(1040, 900 if self.debug_panel.isVisible() else 760)
        self._refresh_header_summary()

    def _quit_application(self) -> None:
        self.close()

    def _build_options_menu(self) -> None:
        menu = self.menu_button.menu()
        if menu is None:
            from PyQt6.QtWidgets import QMenu

            menu = QMenu(self.menu_button)
            self.menu_button.setMenu(menu)

        menu.clear()
        menu.addAction(QAction(self._current_user_id.upper(), self, enabled=False))
        menu.addSeparator()
        menu.addAction(QAction("Theme", self, triggered=self._cycle_theme))
        next_density_label = "Classic" if self._density_mode == "compact" else "Compact"
        menu.addAction(QAction(next_density_label, self, triggered=self._cycle_density))
        menu.addAction(QAction("Pin", self, triggered=self._toggle_pin))
        menu.addAction(QAction("Dashboard", self, triggered=self._toggle_dashboard))
        menu.addAction(QAction("Report", self, triggered=self._export_report))
        menu.addAction(QAction("Close", self, triggered=self._quit_application))

    def _refresh_header_summary(self) -> None:
        self._build_options_menu()
