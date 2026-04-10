from pathlib import Path

from src.application.agent import Agent
from src.application.skill_registry import SkillRegistry
from src.infrastructure.config import Settings
from src.infrastructure.skill_loader import SkillLoader


def build_agent() -> Agent:
    root = Path(__file__).parent
    settings = Settings.from_project_root(root)
    registry = SkillRegistry()
    SkillLoader(settings.skills_dir).load_into(registry)
    return Agent(registry)


if __name__ == "__main__":
    agent = build_agent()
    result = agent.route("this are a sample sentence", mode="free")
    print(result.content)
    print(result.metadata)
