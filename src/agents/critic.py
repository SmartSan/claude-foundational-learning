"""
CriticAgent — an independent quality gate. Reviews the Tutor's lesson and the
Quiz agent's questions *before* the learner ever sees them, and can send
either back for revision. This is the self-correction loop of the system:
no single agent's output reaches the learner unchecked.
"""
from __future__ import annotations

from src.agents.base import Agent
from src.core.config import MAX_TOKENS


class CriticAgent(Agent):
    name = "critic"
    max_tokens = MAX_TOKENS["critic"]
    system_prompt = (
        "You are the Critic agent in a foundational-learning tutoring system. "
        "You review another agent's draft for correctness, clarity, and fit to "
        "the learner's level — you never rewrite it yourself, only approve or "
        "reject with specific feedback. Be strict about factual accuracy and "
        "reasonably strict about clarity; do not nitpick style. Always reply "
        "with exactly the JSON shape requested."
    )

    def review_lesson(self, topic: str, level: str, lesson: str) -> dict:
        prompt = (
            f'Topic: "{topic}"\nLearner level: {level}\n\nDraft lesson:\n{lesson}\n\n'
            "Review this lesson draft. Reply as JSON:\n"
            '{"approved": true|false, "feedback": "specific issues to fix, or '
            'empty string if approved"}'
        )
        return self._ask_json(prompt)

    def review_quiz(self, topic: str, lesson: str, questions: list[dict]) -> dict:
        q_text = "\n".join(f"- {q['question']}" for q in questions)
        prompt = (
            f'Topic: "{topic}"\n\nLesson content:\n{lesson}\n\nDraft quiz questions:\n{q_text}\n\n'
            "Review whether these questions fairly test the lesson content above "
            "(not outside knowledge). Reply as JSON:\n"
            '{"approved": true|false, "feedback": "specific issues to fix, or '
            'empty string if approved"}'
        )
        return self._ask_json(prompt)
