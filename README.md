# Public AI learning journey

This repository documents a hands-on learning journey through AI application
patterns: what each pattern does, how it is put together, and where it breaks.
Each proof of concept (POC) is a small, inspectable experiment rather than a
production system. The specifications and implementations are developed with
AI coding agents; I use the projects to learn, test the results, and share the
trade-offs and limitations publicly.

The examples use a fictional health-content recommendation scenario because it
makes retrieval, relevance, and safety trade-offs visible. They are educational
software only, not medical or clinical systems.

## The learning path

The POCs explore patterns in sequence. POC 1 is a baseline, POC 2 adds an
iterative orchestration pattern, POC 3 is the next planned experiment, and
POC 4 moves the POC 1 retrieval onto a managed search service.

| Example | Approach | What it demonstrates |
|---|---|---|
| [POC 1 — Health Content RAG](poc1-health-content-rag/README.md) | Fixed retrieval-augmented generation (RAG) pipeline | Shows how retrieval can ground a response, and how nearest-neighbor search can still return irrelevant content when the library has a gap. |
| [POC 2 — Health Content Agent Loop](poc2-health-content-agent/README.md) | Bounded retrieve, validate, retry, and fallback loop | Compares LangChain, LangGraph, and Agno orchestration, and shows the added complexity, latency, and model calls of an agent loop. |
| [POC 3 — MCP hands-on learning guide](POC%203%20--%20MCP-Hands-on-Example.md) | Planned Model Context Protocol (MCP) experiment | The guide outlines a future step: expose POC 1 retrieval through MCP and explore its primitives, transports, gateways, and security boundaries. |
| [POC 4 — Azure AI Search hands-on lab](poc4-azure-ai-search-lab/README.md) | Managed vector search with integrated vectorization, run in the Azure portal | Rebuilds POC 1 retrieval on Azure AI Search, enforces the safety rules with pre-filtered vector queries, and tests a managed knowledge base against the same cases. |

The [POC 1 build specification](POC%201%20--%20Health%20Content%20Recommender%20%28RAG%29.md)
and [POC 2 build specification](POC%202%20--%20Health%20Content%20Recommender%20%28Agent%20Loop%29.md)
show how the experiments are scoped for AI-assisted implementation.

## What you can learn

- **RAG:** convert a question into a search, retrieve relevant source material,
  and use that material to ground generation. Observe how similarity ranking,
  fixed filters, and a content gap affect the result.
- **Agent loops:** add a judge, bounded retries, and fallback behavior around
  retrieval. Compare framework orchestration while keeping the data and rules
  consistent.
- **Evaluation and limits:** inspect traces and test cases to see where
  deterministic checks help, where model judgments vary, and what added calls
  and orchestration complexity cost.
- **AI-assisted development:** follow the specs, implementation, tests, and
  documented outcomes to see how AI coding agents can support a learning
  project—and why their output still needs review and validation.

## Where to start

- Start with **POC 1** if you want to understand the retrieval and grounded-generation
  baseline without agent frameworks.
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
information and retrieved article text to the configured OpenAI API. API requests
can incur charges and require model access and billing to be enabled. Never commit
API keys or generated sensitive data.
