"""
Shared base for all agents: each agent is just a system prompt + a couple of
typed methods that call the LLM client and return structured data. Keeping
every agent this small is deliberate — it makes the division of labor (and
the trace log of who-did-what) legible to hackathon judges reading the code.
"""
from __future__ import annotations

from src.core.llm_client import call_agent, call_agent_json


class Agent:
    name: str = "agent"
    system_prompt: str = ""
    max_tokens: int = 800

    def _ask(self, user_content: str, max_tokens: int | None = None) -> str:
        return call_agent(
            self.system_prompt,
            [{"role": "user", "content": user_content}],
            max_tokens=max_tokens or self.max_tokens,
        )

    def _ask_json(self, user_content: str, max_tokens: int | None = None) -> dict:
        return call_agent_json(
            self.system_prompt,
            [{"role": "user", "content": user_content}],
            max_tokens=max_tokens or self.max_tokens,
        )
