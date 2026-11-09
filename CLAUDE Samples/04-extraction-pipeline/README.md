# POC 8: Extraction pipeline with validation, retry and human review

**Part of [CLAUDE Samples](../README.md) · AI learning journey**
An LLM extraction pipeline with a **strict schema**, a **validation–retry loop** and **human review routing**.

Scenario: vendors send messy health-content articles (HTML fragments, all-caps, promo copy). The pipeline extracts the same metadata the [canonical catalog](../../Sample-Data-Health-Content/README.md) uses (`category`, `condition_tags`, `intensity`, `contraindications`), so a reviewed record could join it. The tag vocabulary is **read from the catalog at runtime**, not hard-coded. Only records that are safe and certain are auto-approved; everything else goes to a person.

`data/raw/` holds this pipeline's own *unprocessed* vendor inputs, and `data/fixtures/` holds the scripted model answers. Neither belongs in the shared sample data, which holds finished catalog content.

```
raw .txt ─▶ Claude (forced tool_use, strict: true) ─▶ validate ──ok──▶ route ─┬─▶ auto_approved.jsonl
               ▲                                         │                    └─▶ human_review.jsonl
               └── previous answer + specific errors ◀───┘ fail (≤ 3 attempts)  ▲
                                                          exhausted ────────────┘ (with last_errors)
```

## Three layers of "correct", three different tools

| Layer | Question | Enforced by | On failure |
|---|---|---|---|
| **Shape** | Right keys, types, enums, no extras? | `strict: true` + forced `tool_choice` (`schema.py`) | Can't happen in live mode |
| **Rules** | Lengths, ranges, known tags, cross-field logic (high intensity ⇒ contraindications) | Pydantic `ArticleMetadata` | Retry with the error text |
| **Truth** | Is it grounded in the source? | `validate.py`: quote/author must appear verbatim | Retry, then human review |
| **Risk** | Safe to publish without a person? | `route()`: contraindications, high intensity, confidence, `uncertain_fields` | Human review |

**The principle:** strict mode makes the output *parseable*, not *true*. A perfectly valid JSON object can still carry an invented author. Each layer catches what the one before it can't.

## What the mock run shows

`python -m extraction.pipeline --mock` replays scripted model answers in `data/fixtures/`:

| Doc | What happens | Route |
|---|---|---|
| 01-morning-walks | Clean first time | auto_approved (1 attempt) |
| 02-hiit-bootcamp | Tags it high intensity with no contraindications, so the cross-field rule fails; adds `hypertension` on retry | human_review: contraindicated + high intensity |
| 03-desk-stretches | Invents "Dr. Priya Raman" and paraphrases the quote; grounding fails, fixed on retry | auto_approved (2 attempts) |
| 04-evening-tips | Valid, but confidence 0.6 and unsure fields | human_review |
| 05-vendor-supplement-promo | Keeps fabricating a "clinically proven" quote | human_review after 3 attempts, with `last_errors` |

## Design choices worth defending in an interview

- **Retry with specifics.** The retry prompt carries the original document, the previous answer and each error as an instruction. A bare "try again" mostly reproduces the mistake.
- **Bounded retries (3).** If information isn't in the source, retrying only teaches the model to fabricate. Missing data should be `null` plus `uncertain_fields`, which the schema allows on purpose.
- **Self-reported confidence is one signal, not the gate.** Contraindicated content goes to review even at 0.99 confidence. That's the R2 lesson applied upstream: catch the HIIT article at ingestion, before any recommender can surface it.
- **Reviewers see why.** A failed record carries `last_errors`, so the reviewer starts from the diagnosis.
- **The pipeline depends on an `Extractor` protocol**, so the mock and real adapters swap with no code change (mock data first).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                    # 13 tests, offline
python -m extraction.pipeline --mock         # scripted run, writes output/
export ANTHROPIC_API_KEY=sk-ant-...
python -m extraction.pipeline                # live run against data/raw/
```

> Live mode hasn't been run yet. On the first run, check that strict mode accepts the nullable `["string", "null"]` fields. If it rejects them, switch those to `anyOf: [{type: string}, {type: null}]`.

## Experiments

- Set `MAX_ATTEMPTS = 1` and count how many records land in review. That count is what the retry loop is worth.
- Remove the grounding check, run live on doc 05, and see whether an invented claim gets through.
- Use the Message Batches API for the live run (50% cheaper, fine for non-urgent backfills) and keep per-document `custom_id`s for resubmitting failures.

## MY EXPERIENCE
_Notes: how this compares with the Copilot-based tagging of ~4–5k vendor articles; what the business reviewers actually needed to see in the review queue._
