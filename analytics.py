import logging
from contextlib import contextmanager
from typing import Generator
 
import psycopg2
from psycopg2.extras import RealDictCursor
 
from config import settings
 
logger = logging.getLogger(__name__)
 
 


@contextmanager
def get_db_connection() -> Generator:
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
 
 


#---------------------------------------------------------------------------
# Главная страница 
def get_sentiment_distribution() -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    overall_sentiment,
                    COUNT(*) AS total_reviews,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS percentage
                FROM reviews_analyzed
                WHERE is_relevant = true
                GROUP BY overall_sentiment
                ORDER BY total_reviews DESC
            """)
            return [dict(r) for r in cur.fetchal]


def get_top_entities_overall(limit: int = 5) -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    segment->>'entity' AS entity_name,
                    segment->>'aspect' AS aspect_name,
                    COUNT(*) AS total_mentions,
                    SUM(CASE WHEN segment->>'sentiment' = 'positive' THEN 1 ELSE 0 END) AS positive_count,
                    SUM(CASE WHEN segment->>'sentiment' = 'negative' THEN 1 ELSE 0 END) AS negative_count
                FROM reviews_analyzed ra
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true
                GROUP BY 1, 2
                ORDER BY total_mentions DESC
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]


def get_aspect_stats() -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    segment->>'aspect' AS aspect_name,
                    COUNT(*) AS total_mentions,
                    
                    ROUND(
                        SUM(CASE WHEN segment->>'sentiment' = 'positive' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 
                        2
                    ) AS positive_percentage,
                    
                    ROUND(
                        SUM(CASE WHEN segment->>'sentiment' = 'negative' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 
                        2
                    ) AS negative_percentage
                    
                FROM reviews_analyzed ra
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true
                GROUP BY 1
                ORDER BY total_mentions DESC
            """)
            return [dict(r) for r in cur.fetchall()]



#---------------------------------------------------------------------------
#Страница Аспекты

def get_top_entities_combined(aspect: str, limit: int = 5) -> dict:
    """
    Топ entity для аспекта — все, позитивные, негативные.
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""
                SELECT segment->>'entity' AS entity_name, COUNT(*) AS mentions
                FROM reviews_analyzed ra
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true AND segment->>'aspect' = %s
                GROUP BY 1 ORDER BY 2 DESC LIMIT %s
            """, (aspect, limit))
            all_entities = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT segment->>'entity' AS entity_name, COUNT(*) AS mentions
                FROM reviews_analyzed ra
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true AND segment->>'aspect' = %s
                  AND segment->>'sentiment' = 'positive'
                GROUP BY 1 ORDER BY 2 DESC LIMIT %s
            """, (aspect, limit))
            positive_entities = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT segment->>'entity' AS entity_name, COUNT(*) AS mentions
                FROM reviews_analyzed ra
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true AND segment->>'aspect' = %s
                  AND segment->>'sentiment' = 'negative'
                GROUP BY 1 ORDER BY 2 DESC LIMIT %s
            """, (aspect, limit))
            negative_entities = [dict(r) for r in cur.fetchall()]

    return {
        "all": all_entities,
        "positive": positive_entities,
        "negative": negative_entities,
    }


def get_resonance_reviews(aspect: str, limit: int = 5) -> list[dict]:
    """Резонансные отзывы — много лайков + дизлайков в сумме."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT
                    r.posted_at,
                    r.author,
                    r.likes,
                    r.dislikes,
                    r.text AS full_review_text,
                    (COALESCE(r.likes, 0) + COALESCE(r.dislikes, 0)) AS total_reactions
                FROM reviews_analyzed ra
                JOIN reviews_raw r ON ra.raw_id = r.id
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true
                  AND segment->>'aspect' = %s
                ORDER BY total_reactions DESC
                LIMIT %s
            """, (aspect, limit))
            rows = cur.fetchall()
            return [
                {**dict(r), "posted_at": str(r["posted_at"])}
                for r in rows
            ]


def get_mixed_reviews(aspect: str, limit: int = 5) -> list[dict]:
    """Смешанные отзывы — есть и позитив и негатив в одном аспекте."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH mixed AS (
                    SELECT
                        ra.raw_id,
                        BOOL_OR(segment->>'sentiment' = 'positive'
                            AND segment->>'aspect' = %s) AS has_pos,
                        BOOL_OR(segment->>'sentiment' = 'negative'
                            AND segment->>'aspect' = %s) AS has_neg
                    FROM reviews_analyzed ra
                    CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                    WHERE ra.is_relevant = true
                    GROUP BY ra.raw_id
                )
                SELECT
                    r.posted_at,
                    r.author,
                    r.likes,
                    r.dislikes,
                    r.text AS full_review_text
                FROM mixed m
                JOIN reviews_raw r ON m.raw_id = r.id
                WHERE m.has_pos = true AND m.has_neg = true
                ORDER BY r.posted_at DESC
                LIMIT %s
            """, (aspect, aspect, limit))
            rows = cur.fetchall()
            return [
                {**dict(r), "posted_at": str(r["posted_at"])}
                for r in rows
            ]

#----------------------------------------------------------------------------
# Страница Отзывы



def get_reviews_filtered(
    search: str | None = None,
    sentiment: str | None = None,
    aspect: str | None = None,
    limit: int = 20
) -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            query = """
                SELECT DISTINCT
                    r.posted_at,
                    r.rating,
                    r.likes,
                    r.dislikes,
                    r.text AS full_review_text,
                    ra.overall_sentiment
                FROM reviews_analyzed ra
                JOIN reviews_raw r ON ra.raw_id = r.id
                CROSS JOIN jsonb_array_elements(ra.segments) AS segment
                WHERE ra.is_relevant = true
            """

            params = []

            if search:
                query += " AND r.text ILIKE %s"
                params.append(f"%{search}%")

            if sentiment:
                query += " AND ra.overall_sentiment = %s"
                params.append(sentiment)

            if aspect:
                query += " AND segment->>'aspect' = %s"
                params.append(aspect)

            query += " ORDER BY r.posted_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                {**dict(r), "posted_at": str(r["posted_at"])}
                for r in rows
            ]


#----------------------------------------------------------------------------
# Страница Тренды