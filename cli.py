#!/usr/bin/env python3
"""
CLI demo — runs one full learner session end-to-end in the terminal, printing
each agent handoff so it's obvious this is a multi-agent system, not one
long prompt.

Usage:
    python cli.py
"""
from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from src.orchestrator import Orchestrator
from src.core.state import SessionState

console = Console()


def trace(agent: str, action: str, detail: str = "") -> None:
    line = f"[bold cyan]{agent:>10}[/] → {action}"
    if detail:
        line += f"  [dim]({detail})[/]"
    console.print(line)


def ask(prompt: str) -> str:
    return console.input(f"[bold yellow]{prompt}[/] ").strip()


def run() -> None:
    console.print(Panel.fit(
        "[bold]Multi-Agent Foundational Learning Tutor[/]\n"
        "Agents: Assessor -> Planner -> Tutor <-> Critic -> Quiz <-> Critic -> Progress",
        border_style="green",
    ))

    learner_name = ask("Your name?") or "Learner"
    goal = ask("What do you want to learn? (e.g. 'the basics of Python loops')")

    orch = Orchestrator()
    state = SessionState.create(learner_name, goal)

    # ---- Assessor ----
    console.rule("[bold]Assessing your current level[/]")
    questions = orch.start_diagnostic(state)
    trace("assessor", "generated diagnostic questions", str(len(questions)))
    qa_pairs = []
    for q in questions:
        a = ask(f"  {q}")
        qa_pairs.append((q, a))
    state = orch.finish_diagnostic(state, qa_pairs)
    for entry in state.trace:
        trace(entry["agent"], entry["action"], entry["detail"])
    console.print(f"[green]Level:[/] {state.level}   [green]Gaps:[/] {', '.join(state.known_gaps) or 'none'}")
    console.print(f"[green]Curriculum:[/] {' -> '.join(state.curriculum)}")

    # ---- Teach / Quiz loop ----
    seen_trace = len(state.trace)
    while state.stage != "complete":
        topic = state.current_topic
        console.rule(f"[bold]{topic}[/]")
        for entry in state.trace[seen_trace:]:
            trace(entry["agent"], entry["action"], entry["detail"])
        seen_trace = len(state.trace)

        console.print(Panel(Markdown(state.current_lesson or ""), title="Tutor", border_style="blue"))

        console.print("[bold]Quick check — answer in your own words:[/]")
        qa_pairs = []
        for q in state.current_quiz:
            a = ask(f"  {q['question']}")
            qa_pairs.append((q["question"], a))

        state = orch.submit_quiz(state, qa_pairs)
        for entry in state.trace[seen_trace:]:
            trace(entry["agent"], entry["action"], entry["detail"])
        seen_trace = len(state.trace)

        result = state.progress.get(topic)
        if result:
            verdict = "[green]mastered[/]" if result.mastered else "[yellow]needs more practice[/]"
            console.print(f"Score: {result.best_score:.0%} — {verdict}")
        console.print(f"[dim]{state.last_quiz_feedback}[/]")

    # ---- Final summary ----
    console.rule("[bold]Session complete[/]")
    summary = orch.finish_session(state)
    console.print(Panel(summary, title="Progress summary", border_style="magenta"))
    console.print(f"[dim]Session saved as {state.session_id}. Full agent trace in data/{state.session_id}.json[/]")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        console.print("\n[dim]Session interrupted.[/]")
