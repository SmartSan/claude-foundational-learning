"""
Thin wrapper around the Anthropic API used by every agent.

Keeping this in one place means:
- one spot to swap models / add retries / add logging
- agents stay simple: they just supply a system prompt + messages and
  get text back (or parsed JSON, for agents that need structured output)
"""
import json
import re
from typing import Any

import anthropic

from src.core.config import ANTHROPIC_API_KEY, CLAUDE_MODEL

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


class LLMError(RuntimeError):
    pass


def call_agent(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_tokens: int = 800,
    model: str = CLAUDE_MODEL,
) -> str:
    """Send a system prompt + conversation turns to Claude, return the raw text reply."""
    if _client is None:
        raise LLMError(
            "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    response = _client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


def call_agent_json(
    system_prompt: str,
    messages: list[dict[str, str]],
    max_tokens: int = 800,
    model: str = CLAUDE_MODEL,
) -> dict[str, Any]:
    """
    Same as call_agent, but for agents whose system prompt instructs them to
    reply with a single JSON object. Strips markdown code fences defensively
    and raises a clear error if the model didn't return parseable JSON.
    """
    raw = call_agent(system_prompt, messages, max_tokens=max_tokens, model=model)
    cleaned = _strip_code_fence(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Agent did not return valid JSON. Raw reply:\n{raw}") from exc


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, flags=re.DOTALL)
    return match.group(1) if match else text
