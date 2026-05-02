from __future__ import annotations

from src.domain.entities import SkillResult, UserInput


class Agent:
    def __init__(self, registry) -> None:
        self._registry = registry

    def route(
        self,
        content: str,
        mode: str = "free",
        context: dict[str, object] | None = None,
    ) -> SkillResult:
        user_input = UserInput(content=content, mode=mode, context=context or {})
        skill = self._registry.resolve(mode)
        return skill.execute(user_input)
