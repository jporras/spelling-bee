from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SkillResult:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UserInput:
    content: str
    mode: str = "free"
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentStep:
    agent_id: str
    display_name: str
    mode: str
    state: str
    summary: str
    output: str = ""


@dataclass(slots=True)
class OrchestrationResult:
    selected_mode: str
    final_text: str
    steps: list[AgentStep] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InteractionRecord:
    user_id: str
    source: str
    original_input: str
    selected_mode: str
    final_text: str
    timestamp: str
    difficulty_level: str
    evaluation_score: float
    errors: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UserProfile:
    user_id: str
    difficulty_level: str = "B1"
    total_interactions: int = 0
    correction_count: int = 0
    spelling_count: int = 0
    pronunciation_count: int = 0
    recent_errors: list[str] = field(default_factory=list)
    preferred_modes: dict[str, int] = field(default_factory=dict)
    last_transcript: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvaluationReport:
    score: float
    errors: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    next_focus: str = "Keep practicing."
