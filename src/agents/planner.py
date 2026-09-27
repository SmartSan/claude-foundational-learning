"""
PlannerAgent — turns an assessment into an ordered curriculum: a short
sequence of concrete topics that build on each other toward the learner's goal.
"""
from __future__ import annotations

from src.agents.base import Agent
from src.core.config import MAX_TOKENS


class PlannerAgent(Agent):
    name = "planner"
    max_tokens = MAX_TOKENS["planner"]
    system_prompt = (
        "You are the Planner agent in a foundational-learning tutoring system. "
        "You never teach content yourself — you only design the sequence of "
        "topics a learner should go through, ordered from foundational to "
        "advanced, each one buildable on the last. Keep curricula short and "
        "achievable (4-6 topics) so a learner can complete them in one sitting. "
        "Always reply with exactly the JSON shape requested."
    )

    def build_curriculum(self, goal: str, level: str, known_gaps: list[str]) -> dict:
        gaps = ", ".join(known_gaps) if known_gaps else "none identified"
        prompt = (
            f'Learning goal: "{goal}"\n'
            f"Learner level: {level}\n"
            f"Known gaps: {gaps}\n\n"
            "Design a short curriculum (4-6 topics, plain short titles, ordered "
            "foundational-first) that will get this learner to their goal, "
            "specifically addressing their gaps. Reply as JSON:\n"
            '{"curriculum": ["Topic 1", "Topic 2", ...], '
            '"rationale": "one short sentence on why this order"}'
        )
        return self._ask_json(prompt)
