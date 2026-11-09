# POC 7: MCP server with structured tool errors

**Part of [CLAUDE Samples](../README.md) · AI learning journey**
An MCP server whose tools return **structured errors** with `isError: true`, so the calling agent can tell a typo from an outage.

Scenario: the repo's canonical [health-content catalog](../../Sample-Data-Health-Content/README.md), exposed as three tools: `search_articles`, `get_article` and `flag_article`.

How this differs from [POC 3: MCP Samples](../../MCP%20Samples/README.md): POC 3 tours MCP broadly (tools, resources, prompts, transports, state). This one zooms in on a single question, the **error contract**, with no database or embeddings so the failure paths are easy to see.

## The one idea

MCP has **two** failure channels. Mixing them up is the most common MCP design bug.

| Channel | When | Who handles it |
|---|---|---|
| JSON-RPC protocol error | Malformed request, unknown tool | The client / host |
| `CallToolResult` with `isError: true` | The tool ran and couldn't do its job | **The model**, so it must say what to do next |

An uncaught exception in an `mcp` 2.x tool reaches the model as a bare `"Error executing tool X"`, with no category and no hint. The model then guesses, which usually means it retries something that will never work or gives up on something that would have succeeded a second later.

## The error envelope

```json
{
  "isError": true,
  "structuredContent": {
    "error": {
      "errorCategory": "transient",
      "code": "BACKEND_TIMEOUT",
      "message": "Content index did not respond in time.",
      "isRetryable": true,
      "retryAfterMs": 500,
      "suggestion": "Retry the same call after the delay."
    }
  },
  "content": [{ "type": "text", "text": "<same JSON, for text-only clients>" }]
}
```

| `errorCategory` | Example here | `isRetryable` | What the agent should do |
|---|---|---|---|
| `validation` | `EMPTY_QUERY`, `INVALID_ARTICLE_ID` | false | Fix the input |
| `not_found` | `ARTICLE_NOT_FOUND` | false | Search again or tell the user |
| `permission` | `CLINICIAN_REQUIRED` (flagging a contraindicated article such as `physical-08`) | false | Escalate; don't swap roles to sneak through |
| `business` | `ALREADY_FLAGGED` | false | Explain to the user |
| `transient` | `BACKEND_TIMEOUT` | **true** | Back off and retry (bounded) |
| `internal` | Any crash | false | Stop; details stay in server logs |

**An empty result is not an error.** `search_articles` with no matches returns `isError: false, count: 0`. If you report "nothing found" as an error, the agent can't tell "the search ran and found nothing" from "the search failed".

## Layout

```
src/health_content_mcp/errors.py   ErrorCategory, ToolFailure, error_result()
src/health_content_mcp/server.py   MCPServer + @structured_errors boundary wrapper
examples/retry_client.py           stdio client that branches on isRetryable
tests/test_server.py               in-process Client round-trips for every category
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
python examples/retry_client.py          # watch transient -> retry, validation -> stop
```

Use it from Claude Code (this is what [POC 6](../02-claude-code-setup/README.md) does in its `.mcp.json`):

```bash
claude mcp add health-content -- uv run --directory "$PWD" health-content-mcp   # run from this folder
```

Environment flags: `HEALTH_MCP_FLAKY_CALLS=N` makes the first N backend calls time out, and `HEALTH_MCP_DEBUG=1` exposes a `debug_crash` tool so you can see a safe `internal` error.

## Principles to take away

1. **Errors are part of the tool's interface.** Design them like the success response, with a stable `code`, a category and a next step.
2. **The `suggestion` field is prompt engineering.** It's the only text the model reads at the moment it's stuck.
3. **Catch everything at the boundary and leak nothing.** The crash test asserts the secret in the exception text never reaches the model.
4. **Retry policy belongs to the caller, retryability to the server.** The server knows whether something is transient; the agent decides how many times to try.

## MY EXPERIENCE
_Notes: where structured errors changed agent behaviour, and how this maps to API gateway error contracts (Apigee fault rules, RFC 9457 problem+json)._
