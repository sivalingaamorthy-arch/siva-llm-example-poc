CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('physical', 'mental', 'wellbeing')),
    condition_tags TEXT[] NOT NULL DEFAULT '{}',
    intensity TEXT NOT NULL CHECK (intensity IN ('low', 'medium', 'high')),
    contraindications TEXT[] NOT NULL DEFAULT '{}',
    source TEXT NOT NULL CHECK (source IN ('vendor', 'Everwell')),
    approved BOOLEAN NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    published_date DATE NOT NULL,
    embedding VECTOR(1536)
);

CREATE INDEX IF NOT EXISTS articles_embedding_hnsw_idx
    ON articles USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS articles_category_approved_idx
    ON articles (category, approved, is_default);
