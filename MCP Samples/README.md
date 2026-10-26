# POC 3 — MCP hands-on lab

This Codespaces-friendly project exposes selected POC 1 behavior through the
Model Context Protocol (MCP). It is a learning demo, not a production or
clinical service. Use only the bundled synthetic reports; never submit real
health or personal data.

## What's implemented

- `bmi`: validated example tool with a schema derived from Python type hints.
- `recommendations_for_demo_report`: read-only POC 1 vector retrieval restricted
  to the bundled `R1`, `R2`, and `R3` reports. It requires the POC 1 PostgreSQL
  database, ingested embeddings, and `OPENAI_API_KEY`.
- `article://{article_id}` resource and the `recommend_for_profile` prompt.
- Explicit shortlist handles with either process-local memory or shared
  PostgreSQL storage.
- A destructive `clear_shortlist` tool that is disabled unless the server is
  configured with an allowlist of shortlist IDs; MCP annotations alone do
  not authorize or prevent operations.
- stdio and Streamable HTTP transports, plus a small HTTP client.

POC 1 is not imported until the retrieval tool is called. The BMI tool, article
resource, prompt, and in-memory shortlist can be explored without Docker or an
OpenAI key.

All sample articles and reports come from the repository's canonical
[`Sample-Data-Health-Content/sample-data/`](../Sample-Data-Health-Content/README.md)
directory. The RAG implementation code is imported from the sibling
`RAG Samples/` project; set `POC1_ROOT` if it is elsewhere.

## Setup

From this folder:

```bash
uv sync --all-groups
uv run python -c "import importlib.metadata as m; print(m.version('mcp'))"
uv run python -m pytest
```

`mcp` should report a 2.x version. POC 1's Python dependencies are included in
this project's environment. The sibling `RAG Samples/` folder provides the
retrieval implementation; `HEALTH_CONTENT_SAMPLE_DATA` can override the
canonical sample-data directory.

## Lab 1: inspect tools and schemas

```bash
uv run mcp dev server.py
```

Use the MCP Inspector to list tools, inspect the generated schemas, call
`bmi` with `72` and `1.75`, then try an invalid value such as a zero height.
Input validation failures are tool errors; they do not terminate the server.
Tool names, descriptions, type hints, and annotations form the contract that a
host can inspect.

## Lab 2: connect a stdio host

From this folder, register the local process with Claude Code:

```bash
claude mcp add wellbeing -- uv run python server.py
claude mcp list
```

Claude Code is the host: it launches this server over stdio, presents its tools
to the model, and applies its own consent policy. Server annotations describe
tool behavior; they are not a permission system.

## Lab 3: expose POC 1 retrieval

1. Set `OPENAI_API_KEY` in the Codespaces secret manager.
2. From `RAG Samples/`, start and prepare the existing database:

   ```bash
   docker compose up -d db
   python -m src.rag_app --setup-db
   python -m src.rag_app --seed
   python -m src.rag_app --ingest
   ```

   Use the Python environment where POC 1's declared requirements are
   installed.
3. Start this MCP server from this folder with `uv run mcp dev server.py`.
4. Call `recommendations_for_demo_report` with `R1`, `R2`, or `R3`.

The tool never accepts report contents or arbitrary IDs. It reads the
corresponding bundled synthetic fixture, uses POC 1 validation and retrieval,
and returns article IDs, titles, categories, tags, and similarity scores.
Similarity is not a probability or safety rating. Report notes are sent to the
configured OpenAI embedding API as part of POC 1 retrieval.

## Lab 4: resources and prompts

In the Inspector, read `article://physical-01` and render
`recommend_for_profile` using an age band and goal. The application/user
chooses whether to read a resource or invoke a prompt; the model chooses
whether to call a tool. Article text is untrusted content and must not be
treated as instructions.

## Lab 5: Streamable HTTP

Run the server in one terminal:

```bash
uv run python server.py --transport streamable-http
```

Then call it from another terminal:

```bash
uv run python client.py --tool bmi --arguments '{"weight_kg":72,"height_m":1.75}'
```

The HTTP endpoint is `http://127.0.0.1:8000/mcp`. The client uses the SDK's
discovery/negotiation behavior; use the installed SDK or Inspector to observe
the exact wire messages instead of copying a hand-crafted request from an older
protocol revision. Restart the server and call it again to demonstrate that
BMI has no connection-bound state.

## Lab 6: explicit shortlist state

By default, `SHORTLIST_STORAGE=memory`: handles live only in the current server
process and disappear on restart. To share handles across server processes,
prepare POC 1's PostgreSQL service and run the MCP server with:

```bash
SHORTLIST_STORAGE=postgres uv run python server.py --transport streamable-http
```

The MCP project creates separate `mcp_shortlists` and
`mcp_shortlist_articles` tables in the configured `DATABASE_URL`; no POC 1
article tables are modified. Compare calls routed to two independent
memory-mode processes with calls using the shared PostgreSQL mode.

The in-memory store is a teaching example, not a durable or multi-worker store.
PostgreSQL IDs are explicit UUID handles; no MCP session state is required.

## Lab 7: gateway design exercise

MCP itself does not authorize based on caller-supplied routing headers. If a
gateway routes by MCP method or tool name, validate the body and headers
consistently, authenticate the consumer, authorize tools per consumer,
rate-limit, and log the validated tool name. Do not interpret a routing header
or a tool annotation as authorization. Design a policy and diagram before
placing a remote server behind a gateway; this project does not deploy a
gateway or implement OAuth.

## Lab 8: security exercise

To test destructive-tool authorization, set the server-side list of shortlist
IDs that an operator has approved for clearing:

```bash
export SHORTLIST_CLEAR_ALLOWED_IDS='uuid-of-approved-shortlist'
```

Call `clear_shortlist` only for an allowlisted ID. Calls without a server-side
allowlist or with any other ID fail without deleting anything. The allowlist is
a demo authorization policy, not a production identity system. The tool is
marked destructive for host visibility, but server-side authorization is still
enforced independently. In memory mode, a restart creates a new store; use the
PostgreSQL mode if demonstrating the allowlist across restarts.

Suggested mitigations to record: least-privilege credentials, server-side
authorization for destructive actions, and narrow tool sets per agent. Tool
results and article bodies are untrusted input; host approval prompts are not
a substitute for server checks.

## Tests and limits

```bash
uv run pytest
```

The automated tests cover BMI validation, the fixed report-ID schema, fixture
resource access, shortlist handles, and server-side authorization. They do not
claim to have captured an Inspector screenshot, Claude Code permission prompt,
live OpenAI response, PostgreSQL multi-process run, or gateway behavior; record
those observations in `NOTES.md` when you perform the labs.

The tool intentionally returns concise recommendation metadata, not article
bodies. This keeps output bounded. Nothing here guarantees that retrieved
content is relevant or suitable for an individual. Review the existing
[Use Case 1 — MCP](./Use%20Case%201%20-%20MCP.md) for the lab explanations and
[NOTES.md](./NOTES.md) for step-by-step run instructions and evidence notes.