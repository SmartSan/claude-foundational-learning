"""
AssessorAgent — figures out where the learner actually stands before any
teaching happens. Two-step: generate a short diagnostic, then classify the
learner's level and gaps from their answers.
"""
from __future__ import annotations

from src.agents.base import Agent
from src.core.config import MAX_TOKENS


class AssessorAgent(Agent):
    name = "assessor"
    max_tokens = MAX_TOKENS["assessor"]
    system_prompt = (
        "You are the Assessor agent in a foundational-learning tutoring system. "
        "Your only job is to figure out a learner's current level and knowledge "
        "gaps for a stated learning goal — you never teach content yourself. "
        "Be concise, encouraging, and avoid jargon. Always reply with exactly "
        "the JSON shape requested, no prose outside the JSON."
    )

    def generate_diagnostic(self, goal: str) -> list[str]:
        """Return 2-3 short diagnostic questions to gauge the learner's starting level."""
        prompt = (
            f'A learner wants to learn: "{goal}".\n'
            "Write 2-3 short diagnostic questions (plain text, no code needed to answer) "
            "that would reveal what they already know and where the gaps are. "
            'Reply as JSON: {"questions": ["...", "..."]}'
        )
        data = self._ask_json(prompt)
        return data.get("questions", [])

    def classify(self, goal: str, qa_pairs: list[tuple[str, str]]) -> dict:
        """Classify level + gaps from the learner's answers to the diagnostic."""
        transcript = "\n".join(f"Q: {q}\nA: {a}" for q, a in qa_pairs)
        prompt = (
            f'Learning goal: "{goal}"\n\n'
            f"Diagnostic transcript:\n{transcript}\n\n"
            "Based on this, classify the learner. Reply as JSON:\n"
            '{"level": "beginner|intermediate|advanced", '
            '"known_gaps": ["short gap description", "..."], '
            '"summary": "one encouraging sentence about where they stand"}'
        )
        return self._ask_json(prompt)
