# My LLM Learning POCs

This is my personal playground for learning and experimenting with LLM-based ideas.
I built this repo to explore what is possible with language models in a hands-on,
practical way. These are small proof-of-concept projects, not polished production
systems — just easy-to-follow examples you can run, inspect, and learn from.

A bit of the code in here was generated or assisted by LLMs, and that is part of
what I want to show: AI can speed up prototyping, help turn rough ideas into
working code, and make it easier to explore different patterns quickly.

I am not trying to present this as a clinical or production-grade solution. The
main goal is simple: learn by building, share what I find, and keep the workflow
transparent, grounded, and easy to reason about.

## Why these examples?

These projects are meant to make the difference between a plain RAG flow and an
agent loop easy to see. POC 1 is a good starting point: it shows the basics of
retrieval and grounded generation in a simple, explicit pipeline. POC 2 builds on
that by adding validation, retries, fallback logic, and framework comparisons.

They are intentionally small and inspectable rather than full health systems. That
makes them useful for understanding patterns around retrieval, orchestration,
validation, and safety without treating an LLM as the final source of truth.

| Example | Approach | What it demonstrates |
|---|---|---|
| [POC 1 — RAG recommender](poc1-wellbeing-rag/README.md) | A simple retrieval-augmented generation (RAG) pipeline | Parses report markers, fetches relevant content using PostgreSQL/pgvector, and generates grounded summaries. |
| [POC 2 — Agent framework comparison](poc2-wellbeing-agent/README.md) | A bounded retrieve, validate, retry, and fallback loop | Compares LangChain, LangGraph, and Agno on the same retrieval and safety workflow. |

The longer [POC 1 design](POC%201%20%E2%80%94%20Well-being%20Recommender%20(RAG).md)
and [POC 2 design](POC%202%20%E2%80%94%20Well-being%20Recommender%20(Agent%20Loop).md)
documents explain the architecture, workflow, and learning goals in more detail.

## What you can learn

- How to turn report fields into searchable topic markers and retrieve
  category-specific content with embeddings, metadata filters, and PostgreSQL/pgvector.
- How to keep generated summaries grounded in fetched article content.
- How to separate deterministic rules (such as approval, contraindications,
  category checks, and result counts) from an LLM's semantic judgment.
- How retry loops, rejected-item tracking, and safe fallbacks behave when a
  result is uncertain or no relevant content is found.
- How the same workflow can look as a plain Python pipeline, a LangChain agent,
  a LangGraph workflow, and an Agno agent.
- How to inspect run traces and compare trade-offs like complexity,
  explainability, latency, and API usage.

## Where to start

- Start with **POC 1** if you want to understand the retrieval and grounded-generation
  baseline without agent frameworks.
- Check out **POC 2** if you want to see validation, retries, fallback handling,
  and framework comparison in the same setup.
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
