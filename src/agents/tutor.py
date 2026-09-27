"""
TutorAgent — teaches exactly one topic at a time, adapted to the learner's
level. Can be asked to re-teach a topic incorporating feedback from the
Critic agent (revision loop) or a low quiz score (remediation loop).
"""
from __future__ import annotations

from src.agents.base import Agent
from src.core.config import MAX_TOKENS


class TutorAgent(Agent):
    name = "tutor"
    max_tokens = MAX_TOKENS["tutor"]
    system_prompt = (
        "You are the Tutor agent in a foundational-learning tutoring system. "
        "You teach exactly one topic at a time, adapted to the learner's stated "
        "level. Use plain language, one concrete example or analogy, and keep "
        "it focused — this is a single micro-lesson, not a textbook chapter. "
        "End with a one-line 'why this matters' takeaway. Do not ask questions "
        "or include a quiz; that is handled by another agent. Reply in plain "
        "text (markdown allowed), not JSON."
    )

    def teach(
        self,
        topic: str,
        level: str,
        learner_name: str,
        critic_feedback: str | None = None,
        remediation_note: str | None = None,
    ) -> str:
        prompt = f"Teach the topic \"{topic}\" to {learner_name}, a {level}-level learner."
        if critic_feedback:
            prompt += (
                f"\n\nA reviewer flagged issues with your last draft of this lesson: "
                f"{critic_feedback}\nRevise fully, addressing that feedback."
            )
        if remediation_note:
            prompt += (
                f"\n\nThe learner struggled on the quiz for this topic last time "
                f"({remediation_note}). Re-teach it with a different example or "
                "angle than a standard first pass would use."
            )
        return self._ask(prompt)
