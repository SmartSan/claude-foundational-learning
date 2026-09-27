"""
FastAPI backend exposing the multi-agent orchestrator over HTTP, so the
static frontend (or any client) can drive a session step by step. Each
endpoint corresponds to exactly one Orchestrator method — the API is a thin
shell over the same state machine the CLI uses.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.state import SessionState
from src.orchestrator import Orchestrator

app = FastAPI(title="Foundational Learning Multi-Agent Tutor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

orch = Orchestrator()

# in-memory cache of diagnostic questions per session (not worth persisting)
_diagnostic_cache: dict[str, list[str]] = {}


class StartRequest(BaseModel):
    learner_name: str
    goal: str


class DiagnosticAnswers(BaseModel):
    session_id: str
    answers: list[str]


class QuizAnswers(BaseModel):
    session_id: str
    answers: list[str]


def _load(session_id: str) -> SessionState:
    if not SessionState.exists(session_id):
        raise HTTPException(404, "Unknown session_id")
    return SessionState.load(session_id)


@app.post("/session/start")
def start_session(req: StartRequest):
    state = SessionState.create(req.learner_name, req.goal)
    questions = orch.start_diagnostic(state)
    _diagnostic_cache[state.session_id] = questions
    state.save()
    return {"session_id": state.session_id, "diagnostic_questions": questions, "trace": state.trace}


@app.post("/session/diagnostic")
def submit_diagnostic(req: DiagnosticAnswers):
    state = _load(req.session_id)
    questions = [q for q in _diagnostic_cache.get(req.session_id, [])]
    qa_pairs = list(zip(questions, req.answers)) if questions else [("(diagnostic)", a) for a in req.answers]
    state = orch.finish_diagnostic(state, qa_pairs)
    return _session_view(state)


@app.post("/session/quiz")
def submit_quiz(req: QuizAnswers):
    state = _load(req.session_id)
    questions = [q["question"] for q in state.current_quiz]
    qa_pairs = list(zip(questions, req.answers))
    state = orch.submit_quiz(state, qa_pairs)
    return _session_view(state)


@app.get("/session/{session_id}")
def get_session(session_id: str):
    state = _load(session_id)
    return _session_view(state)


@app.post("/session/{session_id}/finish")
def finish_session(session_id: str):
    state = _load(session_id)
    summary = orch.finish_session(state)
    return {"summary": summary, "progress": state.to_dict()["progress"]}


def _session_view(state: SessionState) -> dict:
    return {
        "session_id": state.session_id,
        "stage": state.stage,
        "level": state.level,
        "known_gaps": state.known_gaps,
        "curriculum": state.curriculum,
        "current_topic": state.current_topic,
        "current_lesson": state.current_lesson,
        "current_quiz": state.current_quiz,
        "last_quiz_feedback": state.last_quiz_feedback,
        "progress": state.to_dict()["progress"],
        "trace": state.trace,
    }


# serve the minimal demo frontend at /
app.mount("/", StaticFiles(directory="frontend/static", html=True), name="frontend")
