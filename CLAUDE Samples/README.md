# CLAUDE Samples

Four small projects on building with Claude: the Agent SDK, Claude Code configuration,
MCP error design and structured extraction. Like the rest of this repository, they
use the shared [health-content sample data](../Sample-Data-Health-Content/README.md)
and are educational experiments, not production or clinical systems.

| POC | Folder | What it demonstrates |
|---|---|---|
| **POC 5** | [01-agent-sdk-loop](./01-agent-sdk-loop/README.md) | An Agent SDK agent with two tools, a `PreToolUse` guard enforcing the R2 safety rules, and a turn limit, plus the same loop hand-written on the Messages API. |
| **POC 6** | [02-claude-code-setup](./02-claude-code-setup/README.md) | A small FastAPI codebase configured with CLAUDE.md, path-scoped `.claude/rules/`, a skill, a read-only subagent and an MCP server. |
| **POC 7** | [03-mcp-structured-errors](./03-mcp-structured-errors/README.md) | An MCP server whose tools return `isError: true` with a category, a retryable flag and a next step, so agents can tell a typo from an outage. |
| **POC 8** | [04-extraction-pipeline](./04-extraction-pipeline/README.md) | Vendor-article extraction into the catalog schema: `strict` tool schema, Pydantic and grounding validation, a bounded retry loop and human review routing. |

## How they connect to the shared scenario

- **R2 safety rules** (no unapproved articles, nothing contraindicated by the report's
  markers, no high-intensity content with hypertension) are enforced in a hook (POC 5),
  in an API guard (POC 6) and at ingestion (POC 8).
- **Markers** are derived with the same thresholds as `RAG Samples/src/report_parser.py`.
- POC 6's `.mcp.json` launches POC 7's server from the sibling folder.

## Running

Each project has its own `pyproject.toml`; run commands from that project's folder.
Data is located by walking up to `Sample-Data-Health-Content/`. Set
`HEALTH_CONTENT_SAMPLE_DATA` to use another copy. All tests run offline with
scripted model responses; live runs need `ANTHROPIC_API_KEY` and can incur charges.

```bash
cd "CLAUDE Samples/01-agent-sdk-loop"
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && pytest -q
```

## Shared code note

Each project carries its own copy of `sample_data.py` (data location, markers, safety
rules) so it stays independently runnable. If a rule changes, change it in all four
copies, or promote it to a shared package once a fifth project needs it.
