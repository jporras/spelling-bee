from __future__ import annotations

from src.application.agents.sub_agent import SubAgent


def build_default_agents() -> dict[str, SubAgent]:
    return {
        "transcription": SubAgent(
            agent_id="transcription",
            display_name="Pulse",
            mode="transcription",
            role="Turns microphone audio into text.",
        ),
        "learning": SubAgent(
            agent_id="learning",
            display_name="Atlas",
            mode="free",
            role="Tracks progress and proposes the next learning focus.",
            routable=False,
        ),
        "evaluation": SubAgent(
            agent_id="evaluation",
            display_name="Vera",
            mode="free",
            role="Evaluates the quality of each learning interaction.",
            routable=False,
        ),
        "conversation": SubAgent(
            agent_id="conversation",
            display_name="Alden",
            mode="free",
            role="Guides talk-mode pronunciation practice and spoken retries.",
        ),
        "grammar": SubAgent(
            agent_id="grammar",
            display_name="Nova",
            mode="grammar",
            role="Evaluates grammar and explains the mistakes clearly.",
        ),
        "spelling": SubAgent(
            agent_id="spelling",
            display_name="Glyph",
            mode="spelling",
            role="Validates spelling letter by letter.",
        ),
        "voice": SubAgent(
            agent_id="voice",
            display_name="Echo",
            mode="tts",
            role="Prepares the response for spoken playback.",
        ),
    }
