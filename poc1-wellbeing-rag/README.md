# POC 1 — Well-being Recommender using RAG

Codespaces-ready, self-contained RAG learning POC. The Python application runs in the Codespace, PostgreSQL 16 with pgvector runs in Docker Compose, and OpenAI provides embeddings and grounded summaries. The Streamlit UI and CLI call the same pipeline.

> Use only the bundled synthetic reports. This is an educational demo, not medical advice. Do not submit real health or other personal data: report notes and retrieved article text are sent to the OpenAI API.

## Implementation summary

POC 1 is implemented as a fixed Python RAG pipeline: it parses a synthetic report into health markers, embeds queries and article content with the OpenAI API, retrieves eligible articles from PostgreSQL using pgvector cosine similarity and deterministic safety filters, then generates a cited summary using only the retrieved articles.

- **Data:** 30 synthetic articles plus three generic defaults, with `vendor` and fictional `Everwell` sources; three synthetic reports cover a happy path, hypertension safety case, and postpartum content gap. No postpartum article is included.
- **Storage and retrieval:** PostgreSQL 16 with pgvector runs through Docker Compose. Only approved, non-default articles are eligible; contraindications and high-intensity physical articles for hypertension are excluded before ranking.
- **Models:** `text-embedding-3-small` creates 1536-dimensional embeddings; `gpt-4o-mini` generates the summary. Model names are configurable.
- **Ways to run:** the Streamlit testing UI and CLI use the same pipeline. The UI requires an explicit button click to make API calls, displays markers, recommendations and scores, and saves JSON results under `output/`.
- **Validation:** the five unit tests pass. The database was started, pgvector enabled, and 33 articles seeded; Streamlit returned HTTP 200 in a startup smoke test.
- **Remaining prerequisite:** recommendation runs require `OPENAI_API_KEY` as a Codespaces secret. Once configured, run `python -m src.rag_app --ingest` to create embeddings before using the UI or CLI.

## How the RAG implementation works

**RAG** means **Retrieval-Augmented Generation**. In everyday terms, the program first looks up a small set of relevant passages in its own article library, then asks a language model to write an answer using those passages. The model is not expected to know this POC's article library in advance.

The run follows the same five steps from the Streamlit button or CLI:

1. **Read and check the report.** The selected JSON report is checked against the expected fields and value types. The three bundled reports are synthetic examples, not real people.
2. **Turn measurements into simple tags.** The report parser applies explicit rules: for example, BMI of 30 or more adds `high_bmi`, blood pressure of 140/90 or higher adds `hypertension`, and sleep under six hours adds `poor_sleep`. It does not diagnose a person. Notes are kept as free text.
3. **Find candidate articles.** OpenAI converts the article text and the report's tags/notes into *embeddings*: lists of numbers that represent patterns in text. During setup, each article's title and body are converted once and stored in PostgreSQL using pgvector. During a run, the query is embedded and compared with article vectors using cosine similarity. A higher score means the text is closer in this mathematical comparison; it is **not** a probability, a medical relevance guarantee, or a safety rating.
4. **Apply fixed safety and category filters.** PostgreSQL first excludes unapproved articles and generic defaults, limits results to the requested category, removes articles whose contraindications match the report's tags, and excludes high-intensity physical articles when hypertension is marked. It then returns up to three closest remaining physical and three closest remaining mental articles. These are explicit program rules, not decisions made by the language model.
5. **Write a grounded summary.** The program sends the selected article IDs/text and report context to OpenAI. A versioned prompt instructs the model to use only those articles, cite IDs, avoid diagnosis and medical advice, and advise speaking to a health adviser when markers are present. The program also adds that adviser sentence if markers exist and the model omitted it. The generated text can still be mistaken or incomplete, so inspect it.

In short:

```text
Synthetic report
  → validate and calculate marker tags
  → embed report query
  → filter articles for category and fixed safety rules
  → rank eligible articles by vector similarity
  → ask OpenAI for a cited summary of those articles
  → display results and save JSON
```

The Streamlit page is the testing screen; it calls the same pipeline as the CLI. PostgreSQL stores article fields and embeddings. The OpenAI API performs embedding and summary generation. Docker Compose starts only the local PostgreSQL/pgvector service; it does not run the Python app.

### Where each part lives

| Part | File | What it does |
|---|---|---|
| App flow and JSON output | [`src/pipeline.py`](./src/pipeline.py) | Runs parsing, retrieval, generation, and result saving in order. |
| Report rules | [`src/report_parser.py`](./src/report_parser.py) | Converts report measurements to marker tags. |
| Vector search and fixed filters | [`src/retriever.py`](./src/retriever.py) | Embeds each category query and runs filtered pgvector similarity search. |
| OpenAI calls | [`src/openai_client.py`](./src/openai_client.py) | Makes embedding and summary requests, with clear errors and no automatic retries. |
| Summary instructions | [`prompts/summary_v1.txt`](./prompts/summary_v1.txt) | Defines what the generated summary may and may not say. |
| Article input | [`data/articles.json`](./data/articles.json) | Contains the 30 synthetic articles plus three defaults, with `vendor` and fictional `Everwell` sources. |
| Browser testing screen | [`src/streamlit_app.py`](./src/streamlit_app.py) | Lets a tester choose a bundled report, run the pipeline, and inspect results. |
| Command-line entry point | [`src/rag_app.py`](./src/rag_app.py) | Sets up, seeds, embeds, checks, or runs a report without the browser UI. |

### What this version does not guarantee

- Similarity only compares language patterns. The nearest article can still be irrelevant. R3 deliberately demonstrates this: there is no postpartum article and this version still returns the closest eligible articles rather than deciding that none is relevant.
- The fixed filters cover only the rules coded here. They are not a complete clinical safety system and do not establish that a recommendation is medically suitable.
- The summary prompt and article citations help constrain the generated response, but do not prove every sentence is correct. This is a learning/demo system, not a clinical product.
- The report notes, marker-based query, and retrieved article text are sent to the external OpenAI API. Use the bundled synthetic reports only.

## Requirements

- GitHub Codespace with Python 3.12 or newer and Docker Compose enabled (validated here with Python 3.14.2)
- OpenAI API key with access and billing enabled for `gpt-4o-mini` and `text-embedding-3-small`
- Internet access from the Codespace

API calls incur usage-based charges and can be rate-limited or unavailable. The default model names are configurable through the environment.

## Setup

Run commands from this folder (`poc1-wellbeing-rag/`):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
docker compose up -d db
python -m src.rag_app --setup-db
```

Set `OPENAI_API_KEY` as a GitHub Codespaces secret (recommended), then restart the Codespace so the environment variable is available. Do not put a real key in `.env`, code, logs, or output. `.env` is gitignored and contains only local database settings by default.

Check the environment. The preflight never prints the API key and only checks API authentication; access to each configured model is confirmed on its first actual request.

```bash
python -m src.rag_app --preflight
```

Seed the 30 articles plus three defaults, then create embeddings:

```bash
python -m src.rag_app --seed
python -m src.rag_app --ingest
```

The article snapshot can be regenerated deterministically with:

```bash
python scripts/generate_seed_data.py
```

## Streamlit testing UI

```bash
streamlit run src/streamlit_app.py --server.address 0.0.0.0
```

Open port `8501` in the Codespaces **Ports** panel and keep its visibility **Private**. Select one of the bundled reports and click **Run recommendation**. No model calls are made on page load or ordinary Streamlit reruns; each explicit click runs retrieval and generation and saves `output/<report_id>.json`. The UI shows marker tags, the top three physical and mental recommendations with similarity scores, and the cited summary. R3 intentionally demonstrates nearest-but-irrelevant results because this baseline RAG has no relevance threshold.

## CLI

The CLI uses the same pipeline and output format:

```bash
python -m src.rag_app --report reports/report1_happy_path.json
python -m src.rag_app --report reports/report2_safety_trap.json
python -m src.rag_app --report reports/report3_content_gap.json
```

Outputs are written to `output/R1.json`, `output/R2.json`, and `output/R3.json`. The output directory is gitignored.

## Checks and tests

Pure unit tests do not require PostgreSQL or an OpenAI key:

```bash
pytest
```

The app preflight checks Docker Compose, PostgreSQL/pgvector, and API authentication. Clear prerequisite and request errors are shown by both the CLI and UI; the API key is never included in output.

## Results and learning notes

Expected behavior to verify in the UI and saved outputs:

- **R1:** markers include high BMI, poor sleep, stress, and sedentary activity; recommendations are selected from eligible physical and mental articles.
- **R2:** hypertension and prediabetes are marked; hypertension-contraindicated and high-intensity physical content is excluded.
- **R3:** postpartum appears only in the synthetic report note, not in the article catalog; the UI highlights the returned nearest-neighbor articles as a content gap.

Inspect the output JSON files for the actual article IDs, scores, and summaries from your run. The OpenAI-generated summaries and cosine similarities depend on model behavior and may vary.

### What RAG got wrong on R3

R3 describes a concern not covered by the content snapshot. The baseline retriever still returns the closest eligible articles, even when they are irrelevant. The UI marks this case as a content-gap demonstration; compare the articles and similarity scores with the report notes. No postpartum-specific article is present in the snapshot.

## Start and stop the database

```bash
docker compose up -d db
docker compose ps
docker compose down
```

The named PostgreSQL volume preserves data across `docker compose down` and Codespace restarts when volumes are retained. To intentionally reset the local database and all seeded data, run `docker compose down -v`, then repeat database setup and seeding. Do not expose PostgreSQL publicly.

## Implementation notes

- One embedding is generated per article. Smaller chunks become useful when articles are long, contain multiple topics, or retrieval needs finer-grained citations.
- Retrieval filters approval, defaults, category, contraindications, and high-intensity physical content for hypertension before ranking by cosine similarity.
- The R3 behavior is a known limitation of plain RAG. A threshold or a content-gap/validation loop is intentionally deferred to a later experiment.
- Generated summaries are constrained by a prompt to cite article IDs, avoid diagnosis or medical advice, and recommend speaking to a health adviser when markers exist. Always inspect results; this is not a clinical system.
