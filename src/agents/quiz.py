"""
QuizAgent — writes a short quiz for the current topic and grades the
learner's free-text answers against it.
"""
from __future__ import annotations

from src.agents.base import Agent
from src.core.config import MAX_TOKENS


class QuizAgent(Agent):
    name = "quiz"
    max_tokens = MAX_TOKENS["quiz"]
    system_prompt = (
        "You are the Quiz agent in a foundational-learning tutoring system. "
        "You write short, fair quizzes that test understanding of exactly the "
        "lesson content you're given (never anything outside it), and you grade "
        "answers generously but honestly — partial understanding gets partial "
        "credit. Always reply with exactly the JSON shape requested."
    )

    def generate_quiz(self, topic: str, lesson: str) -> list[dict]:
        prompt = (
            f'Topic: "{topic}"\n\nLesson content:\n{lesson}\n\n'
            "Write 3 short-answer questions testing understanding of this "
            "lesson (no multiple choice). Reply as JSON:\n"
            '{"questions": [{"id": 1, "question": "..."}, {"id": 2, "question": "..."}, '
            '{"id": 3, "question": "..."}]}'
        )
        data = self._ask_json(prompt)
        return data.get("questions", [])

    def grade(self, topic: str, lesson: str, qa_pairs: list[tuple[str, str]]) -> dict:
        transcript = "\n".join(f"Q: {q}\nLearner's answer: {a}" for q, a in qa_pairs)
        prompt = (
            f'Topic: "{topic}"\n\nLesson content:\n{lesson}\n\n'
            f"Learner's quiz answers:\n{transcript}\n\n"
            "Grade this quiz. Reply as JSON:\n"
            '{"score": 0.0-1.0, '
            '"feedback": "2-3 sentences of specific, encouraging feedback", '
            '"weak_points": ["short phrase", "..."]}'
        )
        return self._ask_json(prompt)
