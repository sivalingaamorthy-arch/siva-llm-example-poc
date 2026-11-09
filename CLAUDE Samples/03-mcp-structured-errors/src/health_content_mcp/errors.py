"""Structured tool errors.

Two kinds of failure exist in MCP, and they must not be confused:

* Protocol errors (JSON-RPC error): the request itself is malformed, e.g. an
  unknown tool. The *client* deals with these; the model usually never sees them.
* Tool execution errors (CallToolResult with isError=true): the tool ran and
  could not do its job. These go to the *model*, so they must tell it what to do
  next: retry? fix the input? give up and tell the user?

This module standardises the second kind into one envelope the agent can branch on.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from mcp_types import CallToolResult, TextContent


class ErrorCategory(str, Enum):
    VALIDATION = "validation"   # caller sent bad input -> fix input, do not retry as-is
    NOT_FOUND = "not_found"     # valid input, nothing there -> do not retry
    PERMISSION = "permission"   # caller may not do this -> escalate, do not retry
    BUSINESS = "business"       # rule violation -> explain to user
    TRANSIENT = "transient"     # backend hiccup -> retry with backoff
    INTERNAL = "internal"       # our bug -> do not retry; details stay server-side


RETRYABLE = {ErrorCategory.TRANSIENT}


class ToolFailure(Exception):
    """Raise inside a tool; the wrapper turns it into a structured isError result."""

    def __init__(
        self,
        category: ErrorCategory,
        code: str,
        message: str,
        *,
        suggestion: str | None = None,
        retry_after_ms: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.code = code
        self.message = message
        self.suggestion = suggestion
        self.retry_after_ms = retry_after_ms
        self.details = details or {}

    def envelope(self) -> dict[str, Any]:
        err: dict[str, Any] = {
            "errorCategory": self.category.value,
            "code": self.code,
            "message": self.message,
            "isRetryable": self.category in RETRYABLE,
        }
        if self.retry_after_ms is not None:
            err["retryAfterMs"] = self.retry_after_ms
        if self.suggestion:
            err["suggestion"] = self.suggestion
        if self.details:
            err["details"] = self.details
        return {"error": err}


def error_result(failure: ToolFailure) -> CallToolResult:
    payload = failure.envelope()
    return CallToolResult(
        is_error=True,
        # Text for clients/models that only read content; structured for code.
        content=[TextContent(type="text", text=json.dumps(payload))],
        structured_content=payload,
    )


def ok_result(payload: dict[str, Any]) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))],
        structured_content=payload,
    )
