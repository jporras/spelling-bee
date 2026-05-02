from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.application.memory.manager import MemoryManager
from src.application.services.router import Agent
from src.application.services.skill_registry import SkillRegistry
from src.application.supervisor.orchestrator import SupervisorAgent
from src.infrastructure.audio.microphone_recorder import MicrophoneRecorder
from src.infrastructure.config import Settings
from src.infrastructure.runtime_paths import get_app_root, get_resource_root
from src.infrastructure.persistence.user_store import UserStore
from src.infrastructure.skill_loader import SkillLoader
from src.application.modes.practice_content import load_practice_content
from src.ui.pyqt.main_window import MainWindow


def build_desktop_dependencies(root: Path) -> tuple[SupervisorAgent, MicrophoneRecorder, Settings]:
    app_root = get_app_root(root)
    resource_root = get_resource_root(root)
    settings = Settings.from_runtime(app_root, resource_root)
    registry = SkillRegistry()
    SkillLoader(settings.skills_dir).load_into(registry)
    router = Agent(registry)
    memory = MemoryManager(UserStore(settings.data_dir))
    practice_content = load_practice_content(resource_root / "prompts" / "skills" / "practice_content.json")
    supervisor = SupervisorAgent(router, memory, practice_content=practice_content)
    recorder = MicrophoneRecorder(output_dir=settings.recordings_dir)
    return supervisor, recorder, settings


def run_app(root: Path) -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    supervisor, recorder, settings = build_desktop_dependencies(root)
    window = MainWindow(supervisor, recorder, settings)
    window.show()
    return app.exec()
