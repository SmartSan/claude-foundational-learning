"""
ProgressAgent — owns the learner's mastery record. The mastery decision
itself is deterministic (score vs. threshold) so it's auditable, but the
agent also generates the human-facing summary at the end of a session.
"""
from __future__ import annotations

from src.agents.base import Agent
from src.core.config import MASTERY_THRESHOLD, MAX_TOKENS
from src.core.state import TopicProgress


class ProgressAgent(Agent):
    name = "progress"
    max_tokens = MAX_TOKENS["progress"]
    system_prompt = (
        "You are the Progress agent in a foundational-learning tutoring system. "
        "You write short, honest, encouraging end-of-session summaries of what "
        "a learner mastered and what still needs work. No fluff, no JSON — "
        "plain text, 3-5 sentences."
    )

    def update(self, current: TopicProgress | None, topic: str, score: float) -> TopicProgress:
        """Deterministic mastery update — no LLM call, so it's fully auditable."""
        progress = current or TopicProgress(topic=topic)
        progress.attempts += 1
        progress.best_score = max(progress.best_score, score)
        progress.mastered = progress.best_score >= MASTERY_THRESHOLD
        return progress

    def summarize_session(self, learner_name: str, goal: str, progress: dict[str, TopicProgress]) -> str:
        lines = "\n".join(
            f"- {p.topic}: best score {p.best_score:.0%}, "
            f"{'mastered' if p.mastered else 'needs more practice'} "
            f"({p.attempts} attempt{'s' if p.attempts != 1 else ''})"
            for p in progress.values()
        )
        prompt = (
            f"Learner: {learner_name}\nGoal: {goal}\n\nTopic results:\n{lines}\n\n"
            "Write the end-of-session summary."
        )
        return self._ask(prompt)
