"""
Tests for the deterministic parts of the system: session state persistence
and the Orchestrator's control-flow decisions. All LLM calls are mocked —
these tests verify the multi-agent *wiring*, not model output quality.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from src.core.state import SessionState, TopicProgress
from src.orchestrator import Orchestrator


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.core.state.DATA_DIR", tmp_path)
    state = SessionState.create("Sri", "learn Python loops")
    state.level = "beginner"
    state.curriculum = ["for loops", "while loops"]
    state.progress["for loops"] = TopicProgress(topic="for loops", attempts=1, best_score=0.8, mastered=True)
    state.save()

    loaded = SessionState.load(state.session_id)
    assert loaded.learner_name == "Sri"
    assert loaded.curriculum == ["for loops", "while loops"]
    assert loaded.progress["for loops"].mastered is True


def test_current_topic_advances_with_index():
    state = SessionState.create("Sri", "goal")
    state.curriculum = ["A", "B", "C"]
    assert state.current_topic == "A"
    state.current_topic_index = 2
    assert state.current_topic == "C"
    state.current_topic_index = 3
    assert state.current_topic is None


@patch("src.agents.quiz.QuizAgent.grade")
@patch("src.agents.progress.ProgressAgent.update")
def test_mastered_topic_advances_index(mock_update, mock_grade, monkeypatch, tmp_path):
    monkeypatch.setattr("src.core.state.DATA_DIR", tmp_path)
    mock_grade.return_value = {"score": 0.9, "feedback": "nice work", "weak_points": []}
    mock_update.return_value = TopicProgress(topic="A", attempts=1, best_score=0.9, mastered=True)

    orch = Orchestrator()
    state = SessionState.create("Sri", "goal")
    state.curriculum = ["A", "B"]
    state.current_lesson = "lesson text"
    state.current_quiz = [{"id": 1, "question": "q1"}]

    with patch.object(orch, "_prepare_lesson") as mock_prepare:
        result = orch.submit_quiz(state, [("q1", "my answer")])

    assert result.current_topic_index == 1  # advanced past "A"
    mock_prepare.assert_called_once()


@patch("src.agents.quiz.QuizAgent.grade")
@patch("src.agents.progress.ProgressAgent.update")
def test_low_score_triggers_remediation_not_advance(mock_update, mock_grade, monkeypatch, tmp_path):
    monkeypatch.setattr("src.core.state.DATA_DIR", tmp_path)
    mock_grade.return_value = {"score": 0.3, "feedback": "needs work", "weak_points": ["basics"]}
    mock_update.return_value = TopicProgress(topic="A", attempts=1, best_score=0.3, mastered=False)

    orch = Orchestrator()
    state = SessionState.create("Sri", "goal")
    state.curriculum = ["A", "B"]
    state.current_lesson = "lesson text"
    state.current_quiz = [{"id": 1, "question": "q1"}]

    with patch.object(orch, "_prepare_lesson") as mock_prepare:
        result = orch.submit_quiz(state, [("q1", "idk")])

    assert result.current_topic_index == 0  # still on "A"
    mock_prepare.assert_called_once_with(state, remediation_note="basics")


@patch("src.agents.critic.CriticAgent.review_lesson")
@patch("src.agents.tutor.TutorAgent.teach")
@patch("src.agents.critic.CriticAgent.review_quiz")
@patch("src.agents.quiz.QuizAgent.generate_quiz")
def test_critic_rejection_triggers_one_revision(mock_gen_quiz, mock_review_quiz, mock_teach, mock_review_lesson):
    mock_teach.side_effect = ["draft v1", "draft v2"]
    mock_review_lesson.side_effect = [
        {"approved": False, "feedback": "too advanced"},
        {"approved": True, "feedback": ""},
    ]
    mock_gen_quiz.return_value = [{"id": 1, "question": "q1"}]
    mock_review_quiz.return_value = {"approved": True, "feedback": ""}

    orch = Orchestrator()
    state = SessionState.create("Sri", "goal")
    state.curriculum = ["A"]
    state.level = "beginner"

    orch._prepare_lesson(state)

    assert mock_teach.call_count == 2
    assert state.current_lesson == "draft v2"
    assert state.lesson_revisions == 1
