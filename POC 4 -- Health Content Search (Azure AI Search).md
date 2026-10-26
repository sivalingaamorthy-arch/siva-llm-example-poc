# POC 4 — Health Content Search on Azure AI Search (hands-on lab)

This is the lab specification for the fourth experiment in my public AI learning
journey. It takes POC 1's retrieval step and rebuilds it on a managed service,
Azure AI Search, using the same synthetic health content, the same three
reports, and the same safety rules. It implements optional extension 1 of the
POC 1 specification: swap pgvector for Azure AI Search and compare.

Unlike POC 1 and POC 2, this is a **manual, portal-driven lab**: there is no
application code. Every step is done in the Azure portal or Cloud Shell, and
every JSON body is kept in one folder so the lab can be repeated exactly. The
specification and lab were developed with an AI assistant; the results recorded
in the README are what I observed when running it.

**Lab workflow:** complete the phases below one at a time. After each phase,
run its checkpoint and record the result before continuing.

## 1. Goal

Index the POC 1 content snapshot in Azure AI Search with integrated
vectorization, then reproduce POC 1's filtered vector retrieval for reports R1,
R2 and R3 using Search explorer queries. Finally, point Azure's managed
knowledge base (agentic retrieval) at the same index and test it against the
same safety cases.

**Learning objective:** understand how a managed search service stores vectors,
calls the embedding model on your behalf, and enforces deterministic filters,
and how that compares with the hand-built pgvector pipeline.

**What to observe:** the index / data source / skillset / indexer / vectorizer
split; pre-filtered vector queries; the R2 safety trap with and without the
filter; R3's nearest-but-irrelevant results; hybrid (keyword + vector) ranking;
and whether an LLM-driven knowledge base respects rules it was never given.

## 2. Stack

- Azure AI Search, **Free** tier (3 indexes, 3 indexers, 50 MB)
- Microsoft Foundry / Azure OpenAI: `text-embedding-3-small` (1536 dimensions)
  for embeddings; `gpt-5-mini` for the optional knowledge-base phase
- Azure Blob Storage (Standard LRS) as the indexer's data source
- Azure portal (Search explorer in **JSON view**) and Cloud Shell (`az`, `curl`)
- No application code, SDK or framework. Every Azure object is defined by a
  JSON body in `json/`.

### 2.1 Azure environment

- **Keep everything in one resource group** so cleanup is a single delete.
- **Use API keys for this lab.** The Free search tier has no managed identity.
  Never commit a real key; the committed JSON uses placeholders such as
  `<your-azure-openai-key>`. Rotate any key that has been pasted anywhere.
- **Use the same embedding deployment on both sides.** The skillset (index
  time) and the index vectorizer (query time) are configured separately and must
  name the same deployment. Different models produce plausible but wrong
  results with no error.
- **Data handling:** article text, report markers and notes are sent to Azure
  OpenAI. Use only the bundled synthetic content. A Global Standard deployment
  may process data outside your region.
- **Cost:** the Free search tier is free, storage is negligible, and Global
  Standard deployments are pay-per-token with no idle cost. Set a budget alert.

## 3. Folder structure

```
poc4-health-content-azure-search/
  README.md                          # the hands-on lab
  json/
    01-articles_prepared.json        # POC 1 articles + embed_text, ISO dates
    02-index.json                    # index schema, HNSW, vectorizer
    03-datasource.json               # Blob data source
    04-skillset.json                 # Azure OpenAI embedding skill
    05-indexer.json                  # jsonArray indexer + vector mapping
    10-query-count-all.json          # data checks
    11-query-check-safety-fields.json
    12-query-unapproved.json
    13-query-r1-mental.json          # acceptance cases
    14-query-r2-safety-filtered.json
    15-query-r2-unfiltered.json
    16-query-r3-content-gap.json
    17-query-r3-hybrid.json
```

## 4. Data

Use the shared content catalog and reports from
`Sample-Data-Health-Content/sample-data/`. The shared README describes the
article schema, seed rules, three reports, and evaluation markers.

### 4.1 Prepared articles — `json/01-articles_prepared.json`

Generated from `Sample-Data-Health-Content/sample-data/articles.json`:

- `published_date` becomes a full ISO timestamp (`2026-01-15T00:00:00Z`),
  because `Edm.DateTimeOffset` rejects a bare date.
- `embed_text` = title + blank line + body: the exact text POC 1 embeds, so
  scores stay comparable. It is input to the embedding skill only and is not an
  index field.

### 4.2 Index schema

Twelve fields: the eleven article fields plus `content_vector`
(`Collection(Edm.Single)`, 1536 dimensions, HNSW + cosine, not retrievable).
Safety fields (`approved`, `is_default`, `category`, `intensity`,
`contraindications`) must be filterable; `title` and `body` searchable. Index
name: `health-content-articles`.

### 4.3 Queries

The query text for each report is its markers plus its free-text note, as in
POC 1. The safety filter is POC 1's SQL `WHERE` clause written as OData:

```text
approved eq true and is_default eq false and category eq '<category>'
  and not contraindications/any(c: search.in(c, '<markers>', ','))
  and intensity ne 'high'          # physical category, when hypertension is a marker
```

with `vectorFilterMode: preFilter`.

## 5. Lab phases

**Phase 1 — Azure setup.** Create the Search service (Free), deploy
`text-embedding-3-small`, and create the storage account. *Checkpoint:* a
direct `curl` to the embeddings endpoint returns a vector.

**Phase 2 — Load.** Upload `01-articles_prepared.json`; create the index,
data source, skillset and indexer from `json/`. *Checkpoint:* indexer run
Success with 0 warnings, 33 documents, vector index usage > 0.

**Phase 3 — Verify data.** Run queries 10–12. *Checkpoint:* count = 33; the
safety fields hold real values; exactly three unapproved articles.

**Phase 4 — Acceptance cases.** Run queries 13–17. *Checkpoint:* the results
in section 6 are met and recorded with scores.

**Phase 5 — Knowledge base (optional).** Deploy a chat model, create a
knowledge source over the index and a knowledge base, and ask the R2 question in
the chat playground. *Checkpoint:* cited articles and the activity log are
recorded against the section 6 rules.

## 6. Acceptance criteria

- R1 returns stress, sleep and weight-related articles.
- R2 (filtered) never returns an article contraindicated for hypertension, and
  never a high-intensity one.
- No filtered query returns an unapproved or default article.
- R2 (unfiltered) **records** where the unsafe and unapproved articles rank.
- R3 **records** what comes back and its scores. Expected: nearest-but-irrelevant
  articles, exactly as in POC 1.
- R3 hybrid **records** whether keyword search changes the order.
- Knowledge base: **records** whether unapproved or contraindicated articles are
  cited, whether claims are grounded in the cited text, and whether the gap is
  admitted. The lab passes as long as the behaviour is recorded, not hidden.

## 7. Out of scope

Application code, SDK clients, push indexing, managed identity, private
networking, chunking, security trimming, production tiers, and real health data.
These are listed as next experiments in the README.

## 8. README must include

The step-by-step lab with a checkpoint per step, the purpose of every file in
`json/`, the observed results with scores, a "What the knowledge base got wrong"
section, a troubleshooting table of real failures, cost and cleanup notes, and
sources.

## 9. Optional extensions (one at a time)

1. Strip the shared disclaimer from `embed_text` and measure whether the R2
   score spread widens.
2. Split the catalogue into one blob per article and test add, edit and soft
   delete through the indexer.
3. Push the same documents with the REST API (no indexer) and compare freshness.
4. Move to the Basic tier and replace API keys with managed identity.
5. Put the same index behind POC 1's `retriever.py` interface and compare
   results programmatically.
