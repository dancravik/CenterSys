import json
import logging
import re
import time
import unicodedata
from contextlib import contextmanager
from typing import Generator
 
import psycopg2
from psycopg2.extras import RealDictCursor
from groq import Groq, RateLimitError, APITimeoutError, APIError
import instructor
 
from config import settings, get_system_prompt
from models import LLMReviewResponse, ReviewSegment
from entity_normalizer import normalize_segments
 
logger = logging.getLogger(__name__)

 
_llm_client: "LLMClient | None" = None
 
 
def get_llm_client() -> "LLMClient":
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
 
 
@contextmanager
def get_db_connection() -> Generator:
    """Гарантирует закрытие соединения и rollback при ошибке."""
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
 
 
def get_unprocessed_reviews(limit: int | None = None) -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if limit:
                cur.execute(
                    "SELECT id, text FROM reviews_raw WHERE processed_at IS NULL LIMIT %s",
                    (limit,),
                )
            else:
                cur.execute(
                    "SELECT id, text FROM reviews_raw WHERE processed_at IS NULL"
                )
            return cur.fetchall()
 
 
def mark_as_processed(raw_id: int) -> None:
    """Помечает отзыв как обработанный без сохранения в reviews_analyzed."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE reviews_raw SET processed_at = NOW() WHERE id = %s",
                (raw_id,),
            )
        conn.commit()
 
 
def save_result_to_db(
    raw_id: int,
    is_relevant: bool,
    overall_sentiment: str,
    segments: list[dict],
) -> None:
    """Атомарно сохраняет результат и помечает отзыв как обработанный."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO reviews_analyzed (raw_id, is_relevant, overall_sentiment, segments)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    raw_id,
                    is_relevant,
                    overall_sentiment,
                    json.dumps(segments, ensure_ascii=False),
                ),
            )
            cur.execute(
                "UPDATE reviews_raw SET processed_at = NOW() WHERE id = %s",
                (raw_id,),
            )
        conn.commit()
 
 
class LLMClient:
    def __init__(self):
        groq_client = Groq(api_key=settings.groq_api_key)
        self._client = instructor.from_groq(groq_client, mode=instructor.Mode.JSON)
 
    def call_api_with_retry(
        self,
        review_text: str,
        system_prompt: str,
        max_retries: int = 3,
    ) -> LLMReviewResponse:
        for attempt in range(max_retries):
            try:
                return self._client.chat.completions.create(
                    model=settings.groq_model,
                    response_model=LLMReviewResponse,
                    temperature=0.0,
                    max_tokens=4096,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": f"Проанализируй следующий отзыв:\n{review_text}",
                        },
                    ],
                )
            except RateLimitError:
                wait = 60
                logger.warning(
                    "Rate limit. Ждём %d сек (попытка %d/%d)",
                    wait, attempt + 1, max_retries,
                )
                time.sleep(wait)
            except APITimeoutError:
                wait = 2 ** attempt
                logger.warning(
                    "Таймаут. Ждём %d сек (попытка %d/%d)",
                    wait, attempt + 1, max_retries,
                )
                time.sleep(wait)
            except APIError as e:
                logger.error("Ошибка API: %s", e)
                time.sleep(2)
 
        raise RuntimeError(
            f"Не удалось обработать отзыв после {max_retries} попыток"
        )
 
    def analyze(self, review_text: str, system_prompt: str) -> LLMReviewResponse:
        return self.call_api_with_retry(review_text, system_prompt)
 
 
 
def _normalize_whitespace(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()
 
 
def validate_quote(quote: str, original_text: str) -> tuple[bool, str | None]:
    norm_quote = _normalize_whitespace(quote)
    norm_original = _normalize_whitespace(original_text)
    if norm_quote in norm_original:
        return True, norm_quote
    return False, None
 
 
def analyze_review(review_text: str) -> LLMReviewResponse:
    client = get_llm_client()
    prompt = get_system_prompt()
 
    logger.info("Отправляем отзыв в LLM (%s)...", settings.groq_model)
    response = client.analyze(review_text, prompt)
    logger.info(
        "LLM ответила — is_relevant: %s, сегментов: %d",
        response.is_relevant,
        len(response.segments),
    )
 
    valid_segments: list[ReviewSegment] = []
    for segment in response.segments:
        is_valid, fixed_quote = validate_quote(segment.text, review_text)
        if is_valid:
            segment.text = fixed_quote
            valid_segments.append(segment)
        else:
            logger.warning("Галлюцинация — сегмент отброшен: '%.80s'", segment.text)

    raw_dicts = [s.model_dump() for s in valid_segments]
    clean_dicts = normalize_segments(raw_dicts)
    logger.info("Сегментов после нормализации: %d", len(clean_dicts))
 
    response.segments = [ReviewSegment(**s) for s in clean_dicts]
    return response
 

 
def run_pipeline_db(limit: int | None = None) -> None:
    reviews = get_unprocessed_reviews(limit)
    logger.info("Найдено %d необработанных отзывов", len(reviews))
 
    processed = 0
    failed = 0
 
    for review in reviews:
        raw_id: int = review["id"]
        review_text: str = review["text"]
 
        try:
            llm_response = analyze_review(review_text)
            if not llm_response.is_relevant:
                mark_as_processed(raw_id)
                logger.info("Отзыв #%d пропущен — не релевантен", raw_id)
                processed += 1
                continue
 
            save_result_to_db(
                raw_id=raw_id,
                is_relevant=llm_response.is_relevant,
                overall_sentiment=llm_response.overall_sentiment.value,
                segments=[s.model_dump() for s in llm_response.segments],
            )
 
            processed += 1
            logger.info(
                "Отзыв #%d обработан | тональность: %-8s | сегментов: %d",
                raw_id,
                llm_response.overall_sentiment.value,
                len(llm_response.segments),
            )
 
        except Exception as e:
            failed += 1
            logger.error("Ошибка при обработке отзыва #%d: %s", raw_id, e)
 
        time.sleep(2)
 
    logger.info("Готово. Обработано: %d, ошибок: %d", processed, failed)


# без main.py
if __name__ == "__main__":
    import argparse
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log", encoding="utf-8"),
        ]
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run_pipeline_db(limit=args.limit)