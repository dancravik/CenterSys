CREATE TABLE IF NOT EXISTS reviews_raw (
    id              SERIAL PRIMARY KEY,
    author          TEXT,
    rating          NUMERIC(2, 1),
    posted_at       TIMESTAMP,
    text            TEXT NOT NULL,
    likes           INTEGER DEFAULT 0,
    dislikes        INTEGER DEFAULT 0,
    owner_response  TEXT,
    imported_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at    TIMESTAMP,
    CONSTRAINT unique_review UNIQUE (author, posted_at)
);
 
-- Индекс для быстрого поиска необработанных отзывов
CREATE INDEX IF NOT EXISTS idx_reviews_raw_unprocessed
    ON reviews_raw (processed_at)
    WHERE processed_at IS NULL;
 
 

 
CREATE TABLE IF NOT EXISTS reviews_analyzed (
    id                SERIAL PRIMARY KEY,
    raw_id            INTEGER NOT NULL REFERENCES reviews_raw(id) ON DELETE CASCADE,
    is_relevant       BOOLEAN NOT NULL,
    overall_sentiment TEXT NOT NULL CHECK (overall_sentiment IN ('positive', 'negative', 'neutral')),
    segments          JSONB NOT NULL DEFAULT '[]',
    analyzed_at       TIMESTAMP NOT NULL DEFAULT NOW()
);
 
-- Индекс для аналитических запросов по тональности
CREATE INDEX IF NOT EXISTS idx_analyzed_sentiment
    ON reviews_analyzed (overall_sentiment);
 
-- Индекс для быстрого поиска по сегментам (jsonb)
CREATE INDEX IF NOT EXISTS idx_analyzed_segments_gin
    ON reviews_analyzed USING GIN (segments);
 
-- Индекс для связи с сырыми отзывами
CREATE INDEX IF NOT EXISTS idx_analyzed_raw_id
    ON reviews_analyzed (raw_id);
 