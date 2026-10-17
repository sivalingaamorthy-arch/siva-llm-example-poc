# Readyness-use-case-pocs

This repository contains two self-contained, educational proof-of-concept projects
that explore how to build a well-being content recommender. Both use the same
synthetic article catalog and example reports, but demonstrate different
architectures:

## Why

This is my personal LLM sample example repository. I created it to explore,
learn, and share how LLMs can be used in practical application patterns,
especially when paired with retrieval, validation, and structured workflows.
Some of the code in this repository was generated or assisted by LLMs, but
that is part of the point: it shows how AI can speed up prototyping and help
turn ideas into working examples that are easier to inspect, test, and improve.

The goal is not to claim these are production systems or clinical-grade
solutions. Instead, this repository demonstrates what can be built with LLMs,
how to think about their strengths and limitations, and how to keep the
workflow grounded through retrieval, deterministic checks, and explicit
validation.

I want to share this work as a practical learning artifact for others who are
interested in building with LLMs, understanding what is possible, and seeing
how experimentation can lead to better ideas.

| Example | Approach | What it demonstrates |
|---|---|---|
| [POC 1 — RAG recommender](poc1-wellbeing-rag/README.md) | A fixed retrieval-augmented generation (RAG) pipeline | Parse report markers, retrieve relevant content with PostgreSQL/pgvector, and generate grounded summaries. |
| [POC 2 — Agent framework comparison](poc2-wellbeing-agent/README.md) | A bounded retrieve, validate, retry, and fallback loop | Compare LangChain, LangGraph, and Agno using the same retrieval, validation, and safety rules. |

The longer [POC 1 design](POC%201%20%E2%80%94%20Well-being%20Recommender%20(RAG).md)
and [POC 2 design](POC%202%20%E2%80%94%20Well-being%20Recommender%20(Agent%20Loop).md)
documents describe the intended architecture, workflow, and learning goals.

## Why look at these examples?

The projects make the difference between a straightforward RAG workflow and an
agent loop concrete. POC 1 is a useful baseline: it shows what can be achieved
with a small, explicit pipeline before adding agent orchestration. POC 2 keeps
the task and safety checks comparable while making retries, framework behavior,
and recovery paths observable. Running both helps you evaluate whether an agent
loop provides enough value to justify its extra complexity, latency, and API
usage.

These are intentionally small, inspectable examples rather than production
health systems. They are useful for learning and prototyping retrieval,
orchestration, and validation patterns without treating a language model as the
source of safety decisions.

## What you can learn

- How to turn report fields into searchable topic markers and retrieve
  category-specific content using embeddings, metadata filters, and
  PostgreSQL/pgvector.
- How to ground generated summaries in retrieved article content.
- How to separate deterministic checks (such as approval, contraindications,
  category, and result-count rules) from an LLM's semantic relevance judgment.
- How bounded retries, feedback, rejected-item tracking, and a safe fallback
  behave when validation fails or relevant content is missing.
- How the same workflow looks as a plain Python pipeline, a LangChain
  tool-calling agent, a LangGraph state graph, and an Agno tool-calling agent.
- How to inspect run traces and compare the trade-offs in complexity,
  explainability, latency, and API usage.

## Choosing a starting point

- Start with **POC 1** to understand the retrieval and grounded-generation
  baseline without agent frameworks.
- Explore **POC 2** when you want to see explicit validation, retries, fallback,
  and framework orchestration compared against that baseline.
- Follow each project's README for setup, prerequisites, commands, tests, and
  expected results. POC 2 uses a separate database and host port so it can run
  alongside POC 1.

## Important limitations

Both projects are educational demonstrations, not medical or clinical systems,
and do not provide diagnosis or personalized health advice. Use only their
bundled synthetic reports; do not submit real health or personal data. The
examples send synthetic report details and retrieved article text to the
configured OpenAI API. API requests may incur charges and require model access
and billing to be enabled. Never commit API keys or generated sensitive data.
