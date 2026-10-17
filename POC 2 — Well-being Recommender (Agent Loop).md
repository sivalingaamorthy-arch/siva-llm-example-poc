# POC 2 — Well-being Recommender using an Agent Loop

Self-contained learning POC. It shares nothing with POC 1: own folder, own database, own data, own copy of the retrieval code. Both POCs can be built in parallel by two separate Claude Code sessions.

**Instruction to Claude Code:** build in the phases below, one at a time. After each phase, run its checkpoint, show me the output, and stop for my go-ahead before the next phase.

**Design note:** the retrieval code is deliberately duplicated from POC 1, not shared as a library. Duplication over coupling: each POC evolves independently.

## 1. Goal

Same feature as POC 1, built as an agent loop. A **retriever agent** proposes the top 3 physical and top 3 mental articles. A **validator agent** checks them. On failure the validator sends feedback and the retriever tries again, up to **3 retries**. If it still fails, a **fallback** shows safe default content, raises a content-gap alert, and flags the case for reassessment.

**What I want to learn:** LangGraph state, nodes and conditional edges; tool calling; maker-checker validation; bounded retries; safe fallback; tracing every iteration.

## 2. Stack

- Python 3.11
- PostgreSQL 16 + pgvector, installed locally, no Docker, **port 5432**, database `wellbeing_agent` (a separate database from POC 1's on the same local instance, so both run side by side)
- Ollama on the host: `llama3.1:8b` (supports tool calling) and `nomic-embed-text` (768 dimensions)
- Libraries: `langgraph`, `langchain-ollama`, `psycopg[binary]`, `pgvector`, `pydantic`, `pytest`

### 2.1 Local environment (no Docker, no admin rights)

- **PostgreSQL 16 installed locally** on the default port 5432. The same instance as POC 1 is fine; this POC uses its own database, `wellbeing_agent`.
- **pgvector** must be installed for that PostgreSQL. Check with `CREATE EXTENSION IF NOT EXISTS vector;` in `setup_db.sql`.
- **Python virtual environment** inside the POC folder: `python -m venv .venv`, then `pip install -r requirements.txt`. Nothing installed globally, so POC 1 and POC 2 dependencies never clash.
- **Ollama** running locally on port 11434, with `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text` done. Both POCs share it.
- Connection details live in `.env` (`DATABASE_URL`, `OLLAMA_HOST`), never hard-coded.
- **Rule for Claude Code:** do not install system software or anything needing admin rights. In Phase 1, run a preflight check (Postgres reachable, pgvector available, Ollama reachable, both models pulled) and stop with a clear message if anything is missing.
- **Temporary fallback, only if pgvector cannot be installed:** use **Chroma** (pip-only, runs in-process, persists to `./chroma_db`) behind the same `retrieval_tool` interface, with metadata filters via its `where` clause. Note the swap in the README; switch back to pgvector once available.
- **Running both POCs at once on one laptop:** Ollama serves requests one at a time by default, so parallel runs will be slower. Build both in parallel, but time the runs one after the other for the latency comparison.

## 3. Folder structure

```
poc2-wellbeing-agent/
  README.md
  setup_db.sql
  requirements.txt
  .env.example
  data/
    articles.json
  reports/
    report1_happy_path.json
    report2_safety_trap.json
    report3_content_gap.json
  src/
    config.py              # MAX_RETRIES = 3, model names, DB url
    models.py              # pydantic: Article, HealthReport, Verdict, Recommendation
    vendor_loader.py
    db.py
    ingest.py
    report_parser.py
    tools/
      retrieval_tool.py    # hybrid retrieval, exposed as a tool
      rules_tool.py        # deterministic safety checks
    agents/
      retriever_agent.py
      validator_agent.py
    graph.py               # LangGraph state machine
    fallback.py
    agent_app.py           # CLI entry point
  prompts/
    retriever_v1.txt
    validator_judge_v1.txt
    summary_v1.txt
  tests/
    test_rules_tool.py
    test_graph_paths.py
  output/
    runs/                  # one JSON trace per run
    content_gap_alerts.jsonl
    reassessment_queue.jsonl
```

## 4. Data

Use exactly the same data spec as POC 1, so results are comparable.

### 4.1 Article schema

id, title, body (150–300 words), category (`physical` | `mental` | `wellbeing`), condition\_tags (from: `high_bmi`, `hypertension`, `prediabetes`, `stress`, `poor_sleep`, `sedentary`, `general`), intensity (`low` | `medium` | `high`), contraindications (list of condition tags), source (`vendor` | `Everwell`), approved (bool), is\_default (bool), published\_date.

### 4.2 Seed content — generate `data/articles.json`

- 30 articles: 10 physical, 10 mental, 10 well-being. Mix of vendor and Everwell sources.
- 3 articles with `approved: false`.
- 2 high-intensity physical articles with `contraindications: ["hypertension"]`.
- At least 3 articles each for stress, poor\_sleep, high\_bmi, hypertension-safe low-intensity exercise, and prediabetes diet.
- **No postpartum content at all.** This gap is deliberate.
- 3 default articles (`is_default: true`), one per category, generic, approved, low intensity.

### 4.3 Health reports — create these exactly

`report1_happy_path.json`

```json
{"report_id": "R1", "age": 42, "sex": "male", "bmi": 31, "blood_pressure": "128/82", "fasting_glucose_mmol": 5.1, "sleep_hours": 5, "stress_level": "high", "activity": "sedentary", "notes": "Desk job, long hours."}
```

`report2_safety_trap.json`

```json
{"report_id": "R2", "age": 58, "sex": "female", "bmi": 26, "blood_pressure": "165/100", "fasting_glucose_mmol": 6.2, "sleep_hours": 7, "stress_level": "moderate", "activity": "occasional walking", "notes": "Wants to get fitter quickly."}
```

`report3_content_gap.json`

```json
{"report_id": "R3", "age": 34, "sex": "female", "bmi": 24, "blood_pressure": "118/76", "fasting_glucose_mmol": 4.9, "sleep_hours": 5, "stress_level": "moderate", "activity": "light", "notes": "12 weeks postpartum, low mood and fatigue."}
```

### 4.4 Marker rules

- BMI ≥ 30 → `high_bmi`
- Systolic ≥ 140 or diastolic ≥ 90 → `hypertension`
- Fasting glucose 5.6–6.9 → `prediabetes`
- Sleep < 6 hours → `poor_sleep`
- Stress high → `stress`
- Activity sedentary → `sedentary`
- Free-text notes also produce **unmatched topics** (e.g. `postpartum`) that the validator must check coverage for.

## 5. The agents

### 5.1 Retriever agent

- Tool: `retrieval_tool(query, category, exclude_ids, filters)`.
- **Important:** in this POC the retrieval tool does *not* apply the contraindication filter. It only filters `approved` and `is_default`. This lets the safety trap reach the validator, so you can see the validator catch it.
- On a retry, it receives the validator's feedback, reformulates the query, and excludes previously rejected article ids.

### 5.2 Validator agent — two layers

1. **Rules tool (deterministic, runs first):** approved = true; no contraindication overlap with user markers; intensity is `low` if `hypertension` is present; category correct; exactly 3 per category.
2. **LLM judge (only if rules pass):** is each article relevant to the report's markers and unmatched topics? Is the tone safe, with no diagnosis or medical advice? Returns JSON: `{"verdict": "pass" | "fail", "rejected_ids": [...], "feedback": "...", "uncovered_topics": [...]}`.

Principle to note in the README: rules for what must never happen, the model for judgement.

### 5.3 Fallback

Triggered when retry\_count reaches 3 and the verdict is still fail:

- Return the 3 default articles, with a line suggesting the user speak to a health adviser.
- Append to `content_gap_alerts.jsonl`: report\_id, uncovered\_topics, last feedback, timestamp.
- Append to `reassessment_queue.jsonl`: report\_id, reason, timestamp.

## 6. LangGraph design

**State:** report, markers, unmatched\_topics, candidates, rejected\_ids, verdict, feedback, retry\_count, final\_output, trace.

**Nodes:** `parse_report` → `retrieve` → `validate` → `generate_output` | `fallback`.

**Conditional edge after `validate`:**

- pass → `generate_output`
- fail and retry\_count < 3 → increment retry\_count → `retrieve`
- fail and retry\_count = 3 → `fallback`

Every node appends to `trace`: node name, query used, article ids, verdict, reason, and elapsed time. Save the trace to `output/runs/<report_id>.json`. Also print a Mermaid diagram of the graph into the README.

## 7. Build phases

**Phase 1 — Setup and data.** Local setup (venv, run setup\_db.sql, check pgvector and Ollama), schema, loader, seed data, reports. *Checkpoint:* 33 rows.

**Phase 2 — Ingest + retrieval tool.** Embed and load; implement `retrieval_tool`. *Checkpoint:* call the tool directly for each report and print results.

**Phase 3 — Rules tool.** Implement deterministic checks with unit tests. *Checkpoint:* the hypertension-contraindicated articles are rejected for R2.

**Phase 4 — Graph without the LLM judge.** Wire the LangGraph loop using rules only. *Checkpoint:* R2 shows at least one reject → retry → pass in the trace.

**Phase 5 — Add the LLM judge.** *Checkpoint:* R3 fails on relevance three times, then hits fallback.

**Phase 6 — Fallback, CLI and tests.** `python -m src.agent_app --report reports/report3_content_gap.json`.

## 8. Acceptance criteria (pytest)

- R1 passes, within 1–2 iterations.
- R2: the trace shows the validator rejecting a contraindicated article with a reason, and the retriever recovering. The final output contains no high-intensity or contraindicated article.
- R3: exactly 3 retries, then fallback. Default articles returned, one line in `content_gap_alerts.jsonl` naming `postpartum`, one line in `reassessment_queue.jsonl`.
- retry\_count never exceeds 3 in any run.
- No run ever returns an unapproved article.
- Empty database → immediate fallback, logged.
- Ollama stopped → rules-only validation if candidates exist, otherwise fallback; logged, no crash.

## 9. Out of scope

UI, auth, cloud deployment, more than two agents, human-in-the-loop approval.

## 10. README must include

How to run, the graph diagram, the trace for each report, and a comparison table against POC 1: number of LLM calls, latency, and how each handled R3. End with a one-line conclusion: when the fixed RAG path is enough, and when the agent loop earns its extra cost.

## 11. Optional extensions (only after Phase 6 works, one at a time)

1. **Tracing** with LangSmith or OpenTelemetry instead of the JSON trace.
2. **Evaluation set:** expected outcome per report (pass, retries, fallback), run as a regression check whenever a prompt changes.
3. Make the LLM switchable between Ollama and **Azure OpenAI**.
4. **Human-in-the-loop:** pause on fallback for a content author to approve or add content, using a LangGraph interrupt.
