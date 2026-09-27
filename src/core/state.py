"""
Shared session state — the "blackboard" that every agent reads from and
writes to. This is what makes the system multi-agent rather than a single
long prompt: each agent only sees the slice of state it needs, and the
Orchestrator is the only thing that decides what happens next.

Persisted to a JSON file per session so a demo can be paused/resumed and
so the FastAPI backend can serve multiple concurrent learners.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.core.config import DATA_DIR

Stage = Literal[
    "assessing", "planning", "teaching", "quizzing", "remediating", "complete"
]


@dataclass
class TopicProgress:
    topic: str
    attempts: int = 0
    best_score: float = 0.0
    mastered: bool = False


@dataclass
class SessionState:
    session_id: str
    learner_name: str
    goal: str
    stage: Stage = "assessing"

    # filled in by AssessorAgent
    level: str | None = None
    known_gaps: list[str] = field(default_factory=list)

    # filled in by PlannerAgent
    curriculum: list[str] = field(default_factory=list)
    current_topic_index: int = 0

    # filled in by TutorAgent / CriticAgent for the current topic
    current_lesson: str | None = None
    lesson_revisions: int = 0

    # filled in by QuizAgent
    current_quiz: list[dict[str, Any]] = field(default_factory=list)
    last_quiz_feedback: str | None = None

    # filled in by ProgressAgent
    progress: dict[str, TopicProgress] = field(default_factory=dict)

    # append-only log of what each agent did, shown in the demo UI/CLI
    # so judges can see the multi-agent handoffs happening
    trace: list[dict[str, Any]] = field(default_factory=list)

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ---- convenience ----
    @property
    def current_topic(self) -> str | None:
        if 0 <= self.current_topic_index < len(self.curriculum):
            return self.curriculum[self.current_topic_index]
        return None

    def log(self, agent: str, action: str, detail: str = "") -> None:
        self.trace.append(
            {
                "agent": agent,
                "action": action,
                "detail": detail,
                "at": datetime.now(timezone.utc).isoformat(),
            }
        )

    # ---- persistence ----
    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["progress"] = {k: asdict(v) for k, v in self.progress.items()}
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "SessionState":
        d = dict(d)
        progress_raw = d.pop("progress", {})
        state = cls(**d)
        state.progress = {k: TopicProgress(**v) for k, v in progress_raw.items()}
        return state

    def save(self) -> None:
        path = DATA_DIR / f"{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, session_id: str) -> "SessionState":
        path = DATA_DIR / f"{session_id}.json"
        return cls.from_dict(json.loads(path.read_text()))

    @classmethod
    def create(cls, learner_name: str, goal: str) -> "SessionState":
        return cls(session_id=str(uuid.uuid4())[:8], learner_name=learner_name, goal=goal)

    @staticmethod
    def exists(session_id: str) -> bool:
        return (DATA_DIR / f"{session_id}.json").exists()
