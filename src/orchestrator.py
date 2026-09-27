"""
Orchestrator — the controller node. It holds no domain knowledge of its own
and never teaches, quizzes, or grades; it only decides, based on the shared
SessionState, which specialist agent runs next and feeds each one exactly
the slice of state it needs. This keeps control flow deterministic and
auditable (see SessionState.trace) even though each individual agent call
is an LLM generation.

The public methods below are the seams the CLI and the FastAPI backend both
call into — each one advances the session by exactly one step, so both
front ends drive the same state machine.
"""
from __future__ import annotations

from src.agents.assessor import AssessorAgent
from src.agents.critic import CriticAgent
from src.agents.planner import PlannerAgent
from src.agents.progress import ProgressAgent
from src.agents.quiz import QuizAgent
from src.agents.tutor import TutorAgent
from src.core.config import MAX_REMEDIATION_ROUNDS
from src.core.state import SessionState, TopicProgress


class Orchestrator:
    def __init__(self) -> None:
        self.assessor = AssessorAgent()
        self.planner = PlannerAgent()
        self.tutor = TutorAgent()
        self.critic = CriticAgent()
        self.quiz = QuizAgent()
        self.progress = ProgressAgent()

    # ---------- stage: assessing ----------
    def start_diagnostic(self, state: SessionState) -> list[str]:
        questions = self.assessor.generate_diagnostic(state.goal)
        state.log("assessor", "generated diagnostic", f"{len(questions)} questions")
        return questions

    def finish_diagnostic(self, state: SessionState, qa_pairs: list[tuple[str, str]]) -> SessionState:
        result = self.assessor.classify(state.goal, qa_pairs)
        state.level = result.get("level", "beginner")
        state.known_gaps = result.get("known_gaps", [])
        state.log("assessor", "classified learner", f"level={state.level}, gaps={state.known_gaps}")

        plan = self.planner.build_curriculum(state.goal, state.level, state.known_gaps)
        state.curriculum = plan.get("curriculum", [])
        state.log("planner", "built curriculum", " -> ".join(state.curriculum))

        state.stage = "teaching"
        self._prepare_lesson(state)
        state.save()
        return state

    # ---------- stage: teaching ----------
    def _prepare_lesson(self, state: SessionState, remediation_note: str | None = None) -> None:
        topic = state.current_topic
        if topic is None:
            state.stage = "complete"
            return

        lesson = self.tutor.teach(topic, state.level or "beginner", state.learner_name, remediation_note=remediation_note)
        state.log("tutor", "drafted lesson", topic)

        for _ in range(2):  # at most one revision round, keeps the demo snappy
            review = self.critic.review_lesson(topic, state.level or "beginner", lesson)
            if review.get("approved", True):
                state.log("critic", "approved lesson", topic)
                break
            state.log("critic", "requested lesson revision", review.get("feedback", ""))
            lesson = self.tutor.teach(
                topic, state.level or "beginner", state.learner_name,
                critic_feedback=review.get("feedback"),
            )
            state.lesson_revisions += 1

        state.current_lesson = lesson
        state.stage = "quizzing"
        self._prepare_quiz(state)

    def _prepare_quiz(self, state: SessionState) -> None:
        topic = state.current_topic
        lesson = state.current_lesson or ""
        questions = self.quiz.generate_quiz(topic, lesson)
        state.log("quiz", "drafted quiz", topic)

        review = self.critic.review_quiz(topic, lesson, questions)
        if not review.get("approved", True):
            state.log("critic", "requested quiz revision", review.get("feedback", ""))
            questions = self.quiz.generate_quiz(topic, lesson)  # one regeneration attempt
        else:
            state.log("critic", "approved quiz", topic)

        state.current_quiz = questions

    # ---------- stage: quizzing -> grading ----------
    def submit_quiz(self, state: SessionState, qa_pairs: list[tuple[str, str]]) -> SessionState:
        topic = state.current_topic
        result = self.quiz.grade(topic, state.current_lesson or "", qa_pairs)
        score = float(result.get("score", 0.0))
        state.last_quiz_feedback = result.get("feedback", "")
        state.log("quiz", f"graded quiz (score={score:.0%})", ", ".join(result.get("weak_points", [])))

        prior = state.progress.get(topic)
        updated: TopicProgress = self.progress.update(prior, topic, score)
        state.progress[topic] = updated
        state.log("progress", "updated mastery record", f"{topic}: {'mastered' if updated.mastered else 'not yet'}")

        if updated.mastered or updated.attempts > MAX_REMEDIATION_ROUNDS:
            state.current_topic_index += 1
            state.current_lesson = None
            state.current_quiz = []
            self._prepare_lesson(state)
        else:
            state.stage = "teaching"
            self._prepare_lesson(state, remediation_note=", ".join(result.get("weak_points", [])) or "low quiz score")

        state.save()
        return state

    # ---------- stage: complete ----------
    def finish_session(self, state: SessionState) -> str:
        summary = self.progress.summarize_session(state.learner_name, state.goal, state.progress)
        state.log("progress", "session summary generated")
        state.save()
        return summary
