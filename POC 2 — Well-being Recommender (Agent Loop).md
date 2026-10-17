# POC 2 — Well-being Recommender: Agent Framework Comparison

Self-contained Codespaces learning POC. It shares no runtime code or database with POC 1: it has its own app folder, PostgreSQL database, synthetic data copy, and retrieval implementation. Its data and models match POC 1 so the framework runs can be compared.

This POC implements the same bounded retrieve → validate → retry → fallback behavior three ways: **LangChain tool-calling agent**, **LangGraph state graph**, and **Agno tool-calling agent**. A Streamlit UI lets you run the same synthetic report through each implementation.

**Design note:** retrieval code and data are deliberately duplicated from POC 1. This keeps the examples independently runnable and avoids cross-POC coupling.

## 1. Goal

Same feature as POC 1, built as an agent loop. A **retriever agent** proposes the top 3 physical and top 3 mental articles. A **validator agent** checks them. On failure the validator sends feedback and the retriever tries again, up to **3 retries**. If it still fails, a **fallback** shows safe default content, raises a content-gap alert, and flags the case for reassessment.

**What I want to learn:** compare LangChain and Agno tool-using agents with explicit LangGraph nodes and conditional edges; deterministic maker-checker validation; bounded retries; safe fallback; and traces for every iteration.

## 2. Stack

- Python 3.12 or newer in a POC-local virtual environment
- PostgreSQL 16 + pgvector in Docker Compose, **host port 5433**, database `wellbeing_agent`
- OpenAI API for generation and embeddings: `gpt-4o-mini` and `text-embedding-3-small` (1536 dimensions)
- Libraries: `langchain`, `langchain-openai`, `langgraph`, `agno`, `openai`, `psycopg[binary]`, `pgvector`, `pydantic`, `streamlit`, `pytest`

### 2.1 Codespaces environment

- **Use Docker Compose for PostgreSQL only.** The POC uses the `pgvector/pgvector:pg16` image. POC1 uses host port 5432; POC2 uses 5433 so both databases can run together.
- **Use Python 3.12 or newer** from the Codespace and install project dependencies into this folder's `.venv`. No system packages or admin rights are needed.
- **Set `OPENAI_API_KEY` as a Codespaces secret.** Never commit it or log its value. Generation and embeddings use the OpenAI API over HTTPS; configure access and billing for both models.
- **Model defaults:** `GENERATION_MODEL=gpt-4o-mini`, `EMBEDDING_MODEL=text-embedding-3-small`, `EMBEDDING_DIMENSIONS=1536`. Keep model settings consistent across frameworks for a fair comparison.
- **Costs/data:** each framework may make OpenAI embedding, judge, and summary calls. Calls are usage-billed and can be rate-limited. Synthetic report notes and retrieved article text are sent to OpenAI. Never use real health or personal data.
- **No Chroma or Ollama fallback.** pgvector and OpenAI are common learning dependencies; if unavailable, preflight should explain how to fix the setup.
- **UI port:** Streamlit uses port 8502 (private Codespaces forwarding), allowing POC1's UI on 8501 to remain available.

## 3. Folder structure

```
poc2-wellbeing-agent/
  README.md
  compose.yaml
  setup_db.sql
  requirements.txt
  .env.example
  .gitignore
  data/
    articles.json
  reports/
    report1_happy_path.json
    report2_safety_trap.json
    report3_content_gap.json
  src/
    config.py              # Model/database config, MAX_RETRIES = 3
    models.py              # Pydantic report, article, verdict, trace, output types
    loader.py              # Seed catalog and load reports
    db.py
    ingest.py
    report_parser.py       # Markers and unmatched topics
    retrieval.py           # Own pgvector retrieval implementation
    rules.py               # Deterministic safety validation
    openai_service.py
    agents/
      shared.py            # Bounded retries, traces, fallback events
      langchain_agent.py   # Tool-using LangChain judge agent
      langchain_runner.py
      langgraph_agent.py   # Explicit StateGraph workflow
      agno_agent.py        # Tool-using Agno judge agent
      agno_runner.py
    runner.py
    preflight.py
    agent_app.py
    streamlit_app.py
  prompts/
    retriever_v1.txt
    validator_judge_v1.txt
    summary_v1.txt
  tests/
    test_rules_tool.py
    test_graph_paths.py
  output/
    runs/                  # JSON result + trace, separated per framework
    content_gap_alerts.jsonl
    reassessment_queue.jsonl
```

## 4. Data

Use the exact same synthetic data as POC 1, including the fictional `Everwell` source, so results are comparable. The POC2 copy is independent.

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

### 5.1 Shared retriever component

- Tool: `retrieve_candidates(report, markers, category, exclude_ids, feedback)`.
- **Important:** in this POC the retrieval tool does *not* apply the contraindication filter. It only filters `approved` and `is_default`. This lets the safety trap reach the validator, so you can see the validator catch it.
- On a retry, it receives validator feedback, uses it in the retrieval query, and excludes previously rejected article IDs.
- Retrieval is deterministic code; it embeds the query, filters metadata in PostgreSQL, and ranks with pgvector. It does not ask the LLM to invent or select article IDs.

### 5.2 Validator agent — two layers

1. **Rules validator (deterministic, runs first):** approved = true; no contraindication overlap with report markers; no high-intensity physical item if hypertension is present; category correct; exactly 3 candidates per category; unmatched topics must be covered.
2. **LLM judge (only if rules pass):** checks relevance to markers/topics. LangChain and Agno implement the judge as a tool-using agent; LangGraph calls a structured OpenAI judge node inside its graph. They return `{"verdict": "pass" | "fail", "rejected_ids": [...], "feedback": "...", "uncovered_topics": [...]}`.

**Principle:** deterministic rules guard what must never happen; the LLM provides a second opinion on semantic relevance. An LLM cannot override a deterministic rejection.

### 5.3 Fallback

Triggered after the initial attempt plus three retries when the verdict is still fail:

- Return approved generic physical and mental defaults, with a line suggesting the user speak to a health adviser. There is one default per category, so fallback shows one physical and one mental item rather than pretending there are three suitable options.
- Append to `content_gap_alerts.jsonl`: report\_id, uncovered\_topics, last feedback, timestamp.
- Append to `reassessment_queue.jsonl`: report\_id, reason, timestamp.

## 6. Framework implementations

### LangChain

Uses a LangChain `create_agent` validator with an article-reading tool and structured Pydantic verdict. The bounded retry loop and deterministic rule gate live in the shared runner.

### LangGraph

Uses an explicit `StateGraph` with parse, retrieval, deterministic validation, LLM judge, retry, fallback, generation, and finish nodes. Conditional edges make the workflow visible and inspectable.

### Agno

Uses an Agno `Agent` with an article-reading tool and Pydantic output schema. As with LangChain, the shared bounded runner enforces the same retry count and rule gate.

Every run records attempt, node, article IDs, verdict/reason, and elapsed time in `output/runs/<report_id>_<framework>.json`. Framework-specific orchestration and judge traces are shown in the UI.

## 7. Build phases

**Phase 1 — Setup and data.** Codespaces venv, Docker Compose PostgreSQL/pgvector, OpenAI secret/preflight, schema, seed data, and reports. *Checkpoint:* 33 rows.

**Phase 2 — Ingest + retrieval tool.** Embed and load articles; implement shared pgvector retrieval. *Checkpoint:* call retrieval for each report and inspect the ranked candidates.

**Phase 3 — Rules tool.** Implement deterministic checks with unit tests. *Checkpoint:* the hypertension-contraindicated articles are rejected for R2.

**Phase 4 — LangGraph.** Wire the explicit state graph, retries, and fallback. *Checkpoint:* graph trace shows R2 reject → retry → pass.

**Phase 5 — LangChain and Agno.** Implement their structured, tool-using validator agents over the shared rules and retry runner. *Checkpoint:* R1 and R2 pass validation; R3 reaches fallback after three retries.

**Phase 6 — Streamlit, CLI, and tests.** Compare reports and frameworks in Streamlit; run a framework from CLI, e.g. `python -m src.agent_app --report reports/report3_content_gap.json --framework langgraph`.

## 8. Acceptance criteria (pytest)

- All framework runs keep retry\_count at or below 3.
- R2: the trace shows the validator rejecting a contraindicated article with a reason, and the retriever recovering. The final output contains no high-intensity or contraindicated article.
- R3: exactly 3 retries after the initial attempt, then fallback. Approved defaults returned; one line in each alert/queue JSONL file includes `postpartum`.
- No run ever returns an unapproved article.
- Empty or unseeded database → clear setup error.
- Missing/unavailable OpenAI API or model → clear error, no silent fallback to another provider.
- All three frameworks run from the same Streamlit UI and produce separate comparable JSON traces.

## 9. Out of scope

Authentication/authorization, cloud deployment, arbitrary report uploads, human-in-the-loop approval, external tracing services, and real health data.

## 10. README must include

How to run, a plain-language technical explanation, Mermaid workflow, framework differences, Streamlit instructions, expected report outcomes, test results, costs/data handling, and how to inspect traces. Compare fixed RAG with this agent loop, including the additional judge calls/retries and R3 behavior. End with when fixed RAG is enough and when the agent loop earns its extra cost.

## 11. Optional extensions (only after Phase 6 works, one at a time)

1. **Tracing** with LangSmith or OpenTelemetry instead of the JSON trace.
2. **Evaluation set:** expected outcome per report (pass, retries, fallback), run as a regression check whenever a prompt changes.
3. Make OpenAI switchable to **Azure OpenAI** through configuration.
4. **Human-in-the-loop:** pause on fallback for a content author to approve or add content, using a LangGraph interrupt.
