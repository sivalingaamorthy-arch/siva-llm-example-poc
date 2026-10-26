# Public AI learning journey

This repository is a collection of small, inspectable AI learning examples.
Each use case explores an application pattern, how it is assembled, and where
it can fail. These are educational experiments, not production or clinical
systems.

## Start here: shared sample data

[`Sample-Data-Health-Content/`](./Sample-Data-Health-Content/README.md) is the
canonical source for the synthetic health-content scenario. It contains the
shared article catalog, sample reports, evaluation reference, and article
generator. Start there to understand the data before running a POC.

The applications use separate databases and generated outputs but read the
same canonical input samples. Set `HEALTH_CONTENT_SAMPLE_DATA` only when the
shared `sample-data/` directory is not at its default repository location.

## The shared scenario

Every use case works with the same fictional task: given a synthetic health
assessment report, find a few relevant articles in a fixed content catalog.
The scenario is intentionally small so retrieval, relevance, safety, and
content gaps can be inspected.

- **Articles:** 30 synthetic articles across physical, mental, and wellbeing
  categories, plus three generic defaults. Each includes tags, intensity,
  contraindications, source, approval status, and default status.
- **R1 — happy path:** the catalog contains articles matching the report's
  general topics.
- **R2 — safety case:** hypertension and prediabetes are present; the report
  also asks to get fitter quickly. High-intensity and contraindicated physical
  content must not appear in final recommendations.
- **R3 — content gap:** the report mentions postpartum concerns, but no
  postpartum article exists in the catalog. Similarity alone cannot fix that
  gap.
- **Evaluation reference:** shared expected markers and behavior checks are in
  [`recommendation-cases.json`](./Sample-Data-Health-Content/sample-data/evaluation-sets/recommendation-cases.json).

The data is fictional, not medical guidance or clinical ground truth. The POCs
deliberately differ in how they handle R3: baseline retrieval may show nearest
neighbors, while the agent-loop example demonstrates bounded fallback.

## Learning path

| Use case | Project guide | What it demonstrates |
|---|---|---|
| **POC 1 — RAG Samples** | [Project README](./RAG%20Samples/README.md) · [Use Case 1](./RAG%20Samples/Use%20Case%201%20--%20Health%20Recommender%20%28RAG%29.md) | A fixed retrieve/filter/generate pipeline and the limits of similarity when content is missing. |
| **POC 2 — Agent AI Samples** | [Project README](./AGENT%20AI%20Samples/README.md) · [Use Case 2](./AGENT%20AI%20Samples/POC%202%20--%20Health%20Content%20Recommender%20%28Agent%20Loop%29.md) | LangChain, LangGraph, and Agno orchestration with deterministic checks, bounded retries, and fallback. |
| **POC 3 — MCP Samples** | [Project README](./MCP%20Samples/README.md) · [Use Case 1](./MCP%20Samples/Use%20Case%201%20-%20MCP.md) · [Run notes](./MCP%20Samples/NOTES.md) | Expose a domain capability through MCP; learn tools, resources, prompts, transports, state handles, and security boundaries. |
| **POC 4 — Azure AI Search** | [Project README](./poc4-health-content-azure-search/README.md) · [Use Case 4](./POC%204%20--%20Health%20Content%20Search%20%28Azure%20AI%20Search%29.md) | A portal-driven managed vector search lab with integrated vectorization, safety filters, and knowledge-base evaluation. |

## What to learn across the examples

- **Retrieval:** how query embeddings, metadata filters, and similarity rank
  source content—and why similarity is not a relevance or safety score.
- **Orchestration:** what validation, retries, and fallback add in exchange for
  more calls, latency, and complexity.
- **Integration:** how an existing domain capability can be exposed through
  MCP without moving domain logic into the host.
- **Evaluation:** how the same synthetic reports reveal baseline, safety, and
  content-gap behavior across different implementations.
- **AI-assisted development:** inspect the specifications, code, tests, and
  run traces instead of assuming generated code or outputs are correct.

## Safety and data handling

Use only the bundled synthetic reports. Do not submit real health, personal, or
otherwise sensitive data. The examples may send synthetic report notes, article
text, or prompts to configured model APIs. API calls can incur charges and
depend on account access and billing. Never commit API keys, `.env` files with
real credentials, or sensitive generated outputs.
