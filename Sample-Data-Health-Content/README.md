# Shared health-content sample data

This folder is the canonical starting point for synthetic health-content data
used by the RAG, Agent AI, MCP, and Vector Search learning examples. Keep source
articles, synthetic reports, and evaluation references here so the examples can
be compared against the same inputs.

These samples are fictional and educational. They are not medical advice or
clinical guidance. Do not add real health or personal data.

## Contents

| Path | Purpose |
|---|---|
| [`sample-data/articles.json`](./sample-data/articles.json) | Canonical article catalog: 30 synthetic articles and three generic defaults. |
| [`sample-data/reports/`](./sample-data/reports/) | Three synthetic input reports: happy path, safety case, and content-gap case. |
| [`sample-data/evaluation-sets/recommendation-cases.json`](./sample-data/evaluation-sets/recommendation-cases.json) | Human-readable evaluation scenarios and expected behaviors for comparing the POCs. |

The evaluation set describes intended behavior, not clinical ground truth or a
guarantee that a model response is safe. Individual POCs can behave differently
on purpose: for example, basic RAG surfaces nearest neighbors for the content
gap, while the agent-loop POC demonstrates a bounded fallback.

## How projects use this data

The RAG and Agent AI projects load the canonical `articles.json` when seeding
their separate PostgreSQL databases. Their report selectors and CLI commands
read the shared `reports/` files. MCP loads the same fixtures and article
catalog, while Azure AI Search's `json/01-articles_prepared.json` is a
service-specific prepared snapshot derived from the canonical article file.

By default, the source path is resolved relative to the repository, so run
commands from each project's own folder as described in that project's README.
The `scripts/generate_seed_data.py` script recreates the canonical article
catalog. Both RAG and Agent AI projects' `scripts/generate_seed_data.py` commands
delegate to this one shared generator. Set `HEALTH_CONTENT_SAMPLE_DATA` to
override the shared `sample-data/` directory when running a project from
another checkout or environment.

Do not edit copies inside an application folder to change the shared scenario.
Update the canonical files here, then rerun that POC's seed/ingestion steps as
needed. Each POC has its own database and generated outputs; centralizing source
fixtures does not centralize runtime state or evaluation results.

## Updating or extending the sample set

- Keep report IDs stable (`R1`, `R2`, `R3`) unless every POC and evaluation
  reference is updated together.
- Keep article IDs stable because database rows, queries, and traces refer to
  them.
- Update the evaluation-set reference when a fixture or intended behavior
  changes.
- Preserve the explicit content-gap case: there is no postpartum article in
  the source catalog, so it can demonstrate the limits of nearest-neighbor
  retrieval.
- Do not add personal data, secrets, API keys, generated real-user content, or
  model outputs to this shared input folder.
