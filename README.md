# Public AI learning journey

This repository documents a hands-on learning journey through AI application
patterns: what each pattern does, how it is put together, and where it breaks.
Each proof of concept (POC) is a small, inspectable experiment rather than a
production system. The specifications and implementations are developed with
AI coding agents; I use the projects to learn, test the results, and share the
trade-offs and limitations publicly.

They are educational software only, not medical or clinical systems.

## The shared scenario: a health content recommender

Every POC in this repository solves the same small problem: given a synthetic
health assessment report, recommend a few relevant articles from a fixed content
library. POC 1 builds that scenario from scratch, and every later POC reuses it
unchanged. Only the pattern being studied changes.

**Why health content?** It makes the hard parts of AI retrieval visible. A
recommendation can be *relevant* yet *unsafe* (high-intensity exercise for
someone with high blood pressure), *approved* or not, and the library can simply
*lack* the content a person needs. Those are the same trade-offs that appear in
any enterprise knowledge or recommendation system, in a form small enough to
inspect line by line.

**What the scenario contains** (defined in the
[POC 1 build specification](POC%201%20--%20Health%20Content%20Recommender%20%28RAG%29.md)):

- **A content library** of 30 synthetic articles across three categories
  (physical, mental, well-being) plus three generic defaults, from two sources:
  `vendor` and a fictional in-house publisher, `Everwell`. Each article carries
  metadata: condition tags, intensity, contraindications, an approval flag and a
  default flag.
- **Three synthetic reports**, each designed to test one behaviour:
  - **R1, happy path:** high BMI, poor sleep, stress, a desk job. Relevant
    articles exist.
  - **R2, safety trap:** blood pressure 165/100 and a wish to "get fitter
    quickly". The closest matches are high-intensity workouts that are
    contraindicated for hypertension.
  - **R3, content gap:** "12 weeks postpartum". The library deliberately has no
    postpartum content.
- **Fixed rules** that turn report measurements into marker tags (for example,
  BMI 30 or more adds `high_bmi`) and **safety rules** that must never be broken:
  never return unapproved or default articles, and never return contraindicated
  or high-intensity physical content when hypertension is present.

Because the data, reports and rules stay constant, the differences between POCs
come from the pattern alone. R2 shows whether a design enforces safety, and R3
shows whether it can admit "I have nothing suitable" instead of returning the
nearest match.

## The learning path

The POCs explore patterns in sequence. POC 1 is the baseline, POC 2 adds an
iterative orchestration pattern, POC 3 is a planned protocol experiment, and
POC 4 moves the POC 1 retrieval onto a managed search service.

| Example | Approach | What changes from the baseline | What it demonstrates |
|---|---|---|---|
| [POC 1 — Health Content RAG](poc1-health-content-rag/README.md) | Fixed retrieval-augmented generation (RAG) pipeline | — (the baseline) | Shows how retrieval can ground a response, and how nearest-neighbor search can still return irrelevant content when the library has a gap. |
| [POC 2 — Health Content Agent Loop](poc2-health-content-agent/README.md) | Bounded retrieve, validate, retry, and fallback loop | Orchestration | Compares LangChain, LangGraph, and Agno orchestration, and shows the added complexity, latency, and model calls of an agent loop. |
| [POC 3 — MCP hands-on learning guide](POC%203%20--%20MCP-Hands-on-Example.md) | Planned Model Context Protocol (MCP) experiment | How retrieval is exposed | The guide outlines a future step: expose POC 1 retrieval through MCP and explore its primitives, transports, gateways, and security boundaries. |
| [POC 4 — Health Content Search on Azure AI Search](poc4-health-content-azure-search/README.md) | Managed vector search with integrated vectorization, as a portal-driven lab | The retrieval store | Rebuilds POC 1 retrieval on Azure AI Search, enforces the safety rules with pre-filtered vector queries, and tests a managed, LLM-driven knowledge base against the same cases. |

The build specifications show how each experiment is scoped for AI-assisted
implementation:
[POC 1](POC%201%20--%20Health%20Content%20Recommender%20%28RAG%29.md),
[POC 2](POC%202%20--%20Health%20Content%20Recommender%20%28Agent%20Loop%29.md),
[POC 3](POC%203%20--%20MCP-Hands-on-Example.md) and
[POC 4](POC%204%20--%20Health%20Content%20Search%20%28Azure%20AI%20Search%29.md).

## What you can learn

- **RAG:** convert a question into a search, retrieve relevant source material,
  and use that material to ground generation. Observe how similarity ranking,
  fixed filters, and a content gap affect the result.
- **Agent loops:** add a judge, bounded retries, and fallback behavior around
  retrieval. Compare framework orchestration while keeping the data and rules
  consistent.
- **Managed search:** see how a cloud search service splits indexing into an
  index, data source, skillset, indexer and vectorizer, and whether an LLM-driven
  knowledge base respects rules it was never given.
- **Evaluation and limits:** inspect traces and test cases to see where
  deterministic checks help, where model judgments vary, and what added calls
  and orchestration complexity cost.
- **AI-assisted development:** follow the specs, implementation, tests, and
  documented outcomes to see how AI coding agents can support a learning
  project—and why their output still needs review and validation.

## Where to start

- Start with **POC 1**: it defines the shared scenario and the retrieval and
  grounded-generation baseline without agent frameworks.
- Check out **POC 2** if you want to see validation, retries, fallback handling,
  and framework comparison in the same setup.
- POC 3 is currently a **planned learning guide**, not a runnable implementation.
- Try **POC 4** if you want to see the same retrieval and safety rules on a
  managed Azure service, step by step in the portal, with no code to run.
- Follow each project's README for setup details, prerequisites, commands, tests,
  and expected results. POC 2 uses a separate database and port so it can run
  alongside POC 1.

## Important limits

These are educational demos, not medical or clinical systems, and they do not
provide diagnosis or personalized health advice. Use only the bundled synthetic
reports; do not submit real health or personal data. The examples send report
information and retrieved article text to the configured OpenAI or Azure OpenAI
API. API requests can incur charges and require model access and billing to be
enabled. Never commit API keys or generated sensitive data.
