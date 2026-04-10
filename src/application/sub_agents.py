from __future__ import annotations

from dataclasses import dataclass

from src.application.agent import Agent
from src.domain.entities import AgentStep, SkillResult


@dataclass(slots=True)
class SubAgent:
    agent_id: str
    display_name: str
    mode: str
    role: str
    routable: bool = True

    def run(
        self,
        router: Agent,
        content: str,
        context: dict[str, object] | None = None,
    ) -> tuple[SkillResult, AgentStep]:
        result = router.route(content=content, mode=self.mode, context=context)
        step = AgentStep(
            agent_id=self.agent_id,
            display_name=self.display_name,
            mode=self.mode,
            state="completed",
            summary=self.role,
            output=result.content,
        )
        return result, step
