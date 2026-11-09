"""LLM adapters. The pipeline depends on the Extractor protocol, not on Anthropic."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol

from .schema import TOOL, TOOL_NAME

SYSTEM = (
    "You extract catalog metadata from vendor health-content articles. "
    "Use only information in the article. If something is not stated, use null and "
    "list the field in uncertain_fields. Never invent authors, sources or claims."
)


class Extractor(Protocol):
    def extract(self, messages: list[dict[str, Any]]) -> dict[str, Any]: ...


class AnthropicExtractor:
    def __init__(self, model: str | None = None) -> None:
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("CLAUDE_MODEL_ID", "claude-sonnet-5-5")

    def extract(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM,
            tools=[TOOL],
            # Forced tool use: the model MUST answer by calling this tool.
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=messages,
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == TOOL_NAME:
                return dict(block.input)
        raise RuntimeError(f"no tool_use in response (stop_reason={response.stop_reason})")


class ScriptedExtractor:
    """Deterministic stand-in: replays canned responses per document.

    fixtures/<doc_id>.json holds a LIST of attempts, so a fixture can deliberately
    fail validation on attempt 1 to exercise the retry loop.
    """

    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = fixtures_dir
        self._cursor: dict[str, int] = {}

    def extract(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        doc_id = messages[0]["content"].split("doc_id=")[1].split("\n")[0].strip()
        attempts = json.loads((self.fixtures_dir / f"{doc_id}.json").read_text("utf-8"))
        i = self._cursor.get(doc_id, 0)
        self._cursor[doc_id] = i + 1
        return attempts[min(i, len(attempts) - 1)]
