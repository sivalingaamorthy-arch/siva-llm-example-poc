# POC 1 — Well-being Recommender using RAG (Codespaces)

Self-contained learning POC for GitHub Codespaces. It shares nothing with POC 2: own folder, own database, own data. Hand this whole spec to one Claude Code session.

**Instruction to Claude Code:** build in the phases below, one at a time. After each phase, run its checkpoint, show me the output, and stop for my go-ahead before the next phase.

## 1. Goal

Given a user's health assessment report, return the top 3 physical and top 3 mental well-being articles from a content snapshot, plus a short summary grounded only in those articles. This is a fixed pipeline: parse, retrieve, generate. No loops, no agents.

**What I want to learn:** chunking and embedding, pgvector, hybrid retrieval (metadata filters + vector similarity), grounded generation, and where plain RAG fails.

## 2. Stack

- Python 3.12 or newer from the Codespace image, in a project-local virtual environment
- PostgreSQL 16 + pgvector in a Docker Compose service, **port 5432**, database `wellbeing_rag`
- OpenAI API for generation (`gpt-4o-mini`) and embeddings (`text-embedding-3-small`, 1536 dimensions)
- Libraries: `psycopg[binary]`, `pgvector`, `openai`, `pydantic`, `streamlit`, `pytest`
- No LangChain, LlamaIndex or LangGraph. Plain Python, so every RAG step is visible.

### 2.1 Codespaces environment

- **Use Docker Compose for PostgreSQL only.** Do not install PostgreSQL into the Codespace host. Use the `pgvector/pg16` image so the database and required extension are available together. Keep the Python application in the Codespace rather than adding an application container; this keeps the learning/debugging loop simple. Generation and embedding use the OpenAI API, so no local model runtime or GPU is needed.
- **Use Python 3.12 or newer from the Codespace image.** Create `.venv` inside this POC folder and install only the project requirements there. Do not install system packages or require admin rights.
- **Start the database** with `docker compose up -d db`. Publish its port only to the Codespace (do not make it public) and configure a health check. The application preflight must wait for PostgreSQL and verify that pgvector is enabled.
- **Configure the OpenAI API:** set `OPENAI_API_KEY` as a GitHub Codespaces secret (preferred) or an untracked local environment variable. Never put a real key in source control, output files, command examples, or logs. `.env.example` documents non-secret settings and may include only an empty placeholder for the key. The application runs in the Codespace and calls the API over HTTPS; no OpenAI key is needed by the database container.
- **Model configuration:** default to `GENERATION_MODEL=gpt-4o-mini` and `EMBEDDING_MODEL=text-embedding-3-small`. The embedding output must be 1536 dimensions and the pgvector column and queries must use that same dimension. Keep model names configurable and record them in each run output; do not silently switch models.
- **API trade-offs:** API access requires internet connectivity, a valid key, and access/billing enabled for the configured models. Requests incur usage-based charges and may be subject to rate limits, service availability, or account policies. Preflight must report a missing key or failed API authentication/connectivity clearly; model-access and request errors must be actionable, not silently retried or replaced.
- **Data handling:** OpenAI receives the report markers and notes used to form retrieval queries and the retrieved article text sent for summarization. This POC's reports are synthetic. Do not run real health reports or other personal/sensitive data through the external API.
- **No Chroma fallback.** pgvector is a core learning objective, and Compose provides it without changing the retrieval implementation. If Docker is unavailable, fail preflight with the exact start-up requirement rather than silently changing databases.
- **Phase 1 preflight:** report the detected Python version, Docker/Compose availability, PostgreSQL and pgvector readiness, whether `OPENAI_API_KEY` is configured, and whether the API can be reached and authenticated. Do not print or log the key. Give actionable guidance for missing prerequisites and stop before ingestion or generation when required dependencies are unavailable.

## 3. Folder structure

```
poc1-wellbeing-rag/
  README.md
  compose.yaml
  setup_db.sql
  requirements.txt
  .env.example
  data/
    articles.json          # 30 articles + 3 defaults
  reports/
    report1_happy_path.json
    report2_safety_trap.json
    report3_content_gap.json
  src/
    config.py
    models.py              # pydantic: Article, HealthReport, Recommendation
    vendor_loader.py       # mimics a third-party API client over the JSON snapshot
    db.py                  # schema + connection
    ingest.py              # embed + load into pgvector
    report_parser.py       # report -> marker tags
    retriever.py           # hybrid retrieval
    generator.py           # grounded summary
    rag_app.py             # reusable pipeline + CLI entry point
    streamlit_app.py       # local Codespaces testing UI
  prompts/
    summary_v1.txt         # prompt kept as a versioned file
  tests/
    test_retrieval.py
    test_end_to_end.py
  output/                  # run results as JSON
```

## 4. Data

### 4.1 Article schema

id, title, body (150–300 words), category (`physical` | `mental` | `wellbeing`), condition\_tags (from: `high_bmi`, `hypertension`, `prediabetes`, `stress`, `poor_sleep`, `sedentary`, `general`), intensity (`low` | `medium` | `high`), contraindications (list of condition tags), source (`vendor` | `Everwell`), approved (bool), is\_default (bool), published\_date.

### 4.2 Seed content — generate `data/articles.json`

- 30 articles: 10 physical, 10 mental, 10 well-being. Mix of vendor and Everwell sources.
- 3 articles with `approved: false` (must never be returned).
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

### 4.4 Marker rules for `report_parser.py`

- BMI ≥ 30 → `high_bmi`
- Systolic ≥ 140 or diastolic ≥ 90 → `hypertension`
- Fasting glucose 5.6–6.9 → `prediabetes`
- Sleep < 6 hours → `poor_sleep`
- Stress high → `stress`
- Activity sedentary → `sedentary`
- Free-text notes are passed through to the query as-is (this is where postpartum shows up).

## 5. Build phases

**Phase 1 — Codespaces setup and data.** Add `compose.yaml` for PostgreSQL 16 with pgvector and a health check. Create a project-local Python 3.12+ virtual environment, document database start/stop and Codespaces secret setup, and implement the preflight described above. Run `setup_db.sql`, schema, vendor loader, seed data, and reports. *Checkpoint:* preflight succeeds, pgvector is enabled, and row count = 33 in `articles` table.

**Phase 2 — Ingest.** Embed title + body per article using the configured OpenAI embedding model (one chunk per article is fine at this size; note in README when chunking would matter). *Checkpoint:* every row has a 1536-dimension embedding.

**Phase 3 — Retrieval.** Parse report into markers. For each category, query = markers + notes. Hybrid retrieval: SQL filter first (`approved = true`, `is_default = false`, category match, no overlap between contraindications and the user's markers), then rank by cosine similarity, top 3. Return the similarity score with each result. *Checkpoint:* retrieval results and scores are available to the UI for all 3 reports.

**Phase 4 — Generation.** Load `prompts/summary_v1.txt`. The prompt must use only the retrieved articles, cite them by id, give no diagnosis or medical advice, and say "speak to a health adviser" when a risk marker is present. *Checkpoint:* generated summaries for all 3 reports are visible in the UI.

**Phase 5 — Streamlit testing UI, CLI, and tests.** Build the Streamlit UI as a thin presentation layer over the same pipeline used by the CLI; do not duplicate retrieval or generation logic. Provide a selector for the three bundled synthetic reports and a **Run recommendation** button so OpenAI calls happen only on explicit user action, not on every Streamlit rerun. Show parsed marker tags, the top 3 physical and top 3 mental recommendations, article ids/titles, similarity scores, and the generated cited summary. Clearly identify R3's nearest-but-irrelevant results as the content-gap demonstration. Save each successful run to `output/<report_id>.json`, show actionable pipeline errors in the UI, and do not expose secrets. Keep the CLI command `python -m src.rag_app --report reports/report1_happy_path.json` working and writing the same JSON shape. Run the UI in the Codespace with `streamlit run src/streamlit_app.py`; forward its port privately using the Codespaces port controls. Add the tests below. README must also include Codespaces setup, UI/CLI run instructions, API secret configuration, model names, usage-cost/data-handling notes, and database start/stop commands.

## 6. Acceptance criteria (pytest)

- R1 returns stress, sleep and weight-related articles.
- R2 never returns an article contraindicated for hypertension, and never a high-intensity one.
- No run ever returns an unapproved or default article.
- R3: the test **records** what comes back and its similarity scores. Expected: RAG returns nearest-but-irrelevant articles, because it always returns something. This is the known weakness POC 2 fixes. The test passes as long as the behaviour is logged, not hidden.
- Empty database → clear error message, no crash.
- OpenAI key missing, API unavailable, authentication fails, or configured model inaccessible → clear, actionable error message, no crash.
- The UI can run each bundled report on demand, displays markers/recommendations/similarity scores/summary, and writes the same output JSON as the CLI.
- Streamlit reruns do not make OpenAI calls unless the user explicitly starts a run.
- UI pipeline errors are visible and actionable; secrets are never displayed.

## 7. Out of scope

Agents, retries, validators, application fallbacks, UI authentication, arbitrary report uploads, cloud deployment, and real health data. The Streamlit UI is a local Codespaces testing interface, not a production application. Docker Compose is used only to run the local-development database inside the Codespace.

## 8. README must include

How to start the database, launch the Streamlit UI and CLI, configure the Codespaces API secret, and stop services. Include the three results and a short "What RAG got wrong on R3" section with the scores. This feeds my interview talking points.

## 9. Optional extensions (only after Phase 5 works, one at a time)

1. Swap pgvector for **Azure AI Search** behind the same `retriever.py` interface, and compare results.
2. Add an **evaluation set**: expected article ids per report, and report precision@3.
3. Make the LLM and embedding provider switchable between OpenAI and **Azure OpenAI** via config.
4. Add a similarity **threshold**, and see how it changes R3.
