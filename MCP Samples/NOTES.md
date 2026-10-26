# POC 3 — Run instructions and lab notes

Use only the bundled synthetic reports. This project is a learning demo, not a
production or clinical service. Never put API keys in source control.

For an explanation of what each lab demonstrates and why, see
[Use Case 1 — MCP](./Use%20Case%201%20-%20MCP.md). For the implementation
summary and limitations, see the [project README](./README.md).

## 1. Set up the project

From the repository root:

```bash
cd "MCP Samples"
uv sync --all-groups
uv run python -c "import importlib.metadata as m; print(m.version('mcp'))"
uv run python -m pytest
```

The MCP SDK should report a 2.x version. If `uv` is not installed, install it
using the official uv instructions, then run the commands above. Run the MCP
commands below from this `MCP Samples/` directory.

## 2. Run the Inspector (Labs 1 and 4)

```bash
uv run mcp dev server.py
```

Open the Inspector link it prints. List tools, call `bmi` with
`{"weight_kg":72,"height_m":1.75}`, then try a zero height and inspect the
error. Read the `article://physical-01` resource and render the
`recommend_for_profile` prompt.

## 3. Connect a stdio host (Lab 2)

From this directory, register the server with Claude Code:

```bash
claude mcp add wellbeing -- uv run python server.py
claude mcp list
```

Open Claude Code and check `/mcp`. Ask it to calculate BMI. A permission prompt
depends on the host's configured approval policy; it is not guaranteed by MCP
itself. To remove the server later, use `claude mcp remove wellbeing`.

## 4. Run the RAG retrieval tool (Lab 3)

This lab additionally needs Docker, the RAG sample's PostgreSQL service,
seeded embeddings, and an OpenAI API key.

1. Set `OPENAI_API_KEY` in `RAG Samples/.env` or your Codespaces secrets. Do not
   commit the key. The canonical articles, reports, and evaluation references
   are in `Sample-Data-Health-Content/sample-data/`.
2. In a terminal from the repository root, prepare the RAG database:

   ```bash
   cd "RAG Samples"
   docker compose up -d db
   source .venv/bin/activate
   python -m src.rag_app --setup-db
   python -m src.rag_app --seed
   python -m src.rag_app --ingest
   ```

3. In a second terminal, start the MCP Inspector with the sibling RAG folder
   configured:

   ```bash
   cd "MCP Samples"
   export POC1_ROOT="../RAG Samples"
   export HEALTH_CONTENT_SAMPLE_DATA="../Sample-Data-Health-Content/sample-data"
   uv run mcp dev server.py
   ```

4. In the Inspector, call `recommendations_for_demo_report` with `R1`, `R2`, or
   `R3`. Note the returned article IDs and compare the fixtures.

The MCP tool sends the selected synthetic report through the existing RAG
validation and retrieval functions. It uses OpenAI to embed the report query;
it does not accept arbitrary report text or return a generated clinical
recommendation. Similarity is not a safety score.

## 5. Run Streamable HTTP (Lab 5)

In one terminal, from `MCP Samples/`:

```bash
uv run python server.py --transport streamable-http
```

In a second terminal, from the same directory:

```bash
uv run python client.py --tool bmi --arguments '{"weight_kg":72,"height_m":1.75}'
```

The default endpoint is `http://127.0.0.1:8000/mcp`. The SDK client performs
protocol discovery/negotiation. Use the Inspector or SDK client to observe
messages; protocol wire details can change between SDK versions. Do not assume
a copied curl example from another protocol revision matches this project.
Stop the server with Ctrl+C when finished.

## 6. Compare shortlist storage (Lab 6)

Memory storage is the default. The handle and its articles exist only in that
server process and disappear when it stops. Create a shortlist, add an article,
and restart the server to observe this.

For persistent storage, start the HTTP server from `MCP Samples/` with:

```bash
POC1_ROOT="../RAG Samples" \
HEALTH_CONTENT_SAMPLE_DATA="../Sample-Data-Health-Content/sample-data" \
SHORTLIST_STORAGE=postgres \
uv run python server.py --transport streamable-http
```

The PostgreSQL connection settings are read from the RAG sample's `.env` when
the sibling folder is configured. Create a shortlist and add an article, then
restart the server and look it up using the same handle. The MCP project
creates separate shortlist tables; it does not change the RAG article table.

The example command uses the default HTTP port. Comparing two live server
instances requires configuring different ports, which is outside this
walkthrough.

## 7. Gateway exercise (Lab 7)

No gateway is deployed by this project. Write a short policy and draw a
diagram showing the host, gateway, MCP server, and domain API. Include
consumer authentication, per-tool authorization, rate limits, and audit logs.
Do not treat MCP routing headers as identity or authorization.

## 8. Test destructive-tool authorization (Lab 8)

Use PostgreSQL mode so the shortlist survives a server restart:

1. Start the server with `SHORTLIST_STORAGE=postgres`, create a shortlist, and
   copy its returned UUID.
2. Stop the server. Start it again with the UUID on the server-side allowlist:

   ```bash
   POC1_ROOT="../RAG Samples" \
   HEALTH_CONTENT_SAMPLE_DATA="../Sample-Data-Health-Content/sample-data" \
   SHORTLIST_STORAGE=postgres \
   SHORTLIST_CLEAR_ALLOWED_IDS='paste-the-shortlist-uuid-here' \
   uv run python server.py --transport streamable-http
   ```

3. Try `clear_shortlist` with a different UUID and verify it fails. Confirm
   `get_shortlist` for the approved UUID still returns its entries.
4. Only in this isolated demo, call `clear_shortlist` for the allowlisted UUID
   and confirm it is removed.

The allowlist is a simple learning example, not a production identity system.
Tool annotations tell the host that a tool is destructive; the server checks
the allowlist independently.

## Evidence log

Record what you observed rather than treating these prompts as completed
evidence:

- Lab 0 — MCP SDK version: __________________________________________
- Lab 1 — BMI schema and invalid-input error: _________________________
- Lab 2 — Host connection and approval behavior: ______________________
- Lab 3 — Report ID and returned article IDs: _________________________
- Lab 4 — Who chose the tool, resource, and prompt: ___________________
- Lab 5 — HTTP call and observed protocol messages: ___________________
- Lab 6 — Memory restart vs. PostgreSQL restart: ______________________
- Lab 7 — Gateway policy and diagram location: _______________________
- Lab 8 — Denied call result and allowlisted test result: _______________

## Reflection

- What was easier to integrate through MCP than through a custom host adapter?
- Which responsibilities stayed in the existing RAG/domain code?
- Which controls belong to the host, and which must the server enforce?
