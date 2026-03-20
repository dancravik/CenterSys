import argparse
import json
import logging
import sys

import psycopg2
from config import settings


logger = logging.getLogger(__name__)


INSERT_QUERY = """
    INSERT INTO reviews_raw (author, rating, posted_at, text, likes, dislikes, owner_response)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (author, posted_at) DO NOTHING
"""


def load_reviews(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Ожидался список отзывов, получен {type(data).__name__}")
    return data


def import_reviews(json_path: str, truncate: bool = False) -> int:
    reviews = load_reviews(json_path)
    logger.info("Загружено %d отзывов из %s", len(reviews), json_path)
 
    rows = [
        (
            review.get("author"),
            review.get("rating"),
            review.get("date"),
            review.get("text"),
            review.get("likes"),
            review.get("dislikes"),
            review.get("owner_response"),
        )
        for review in reviews
    ]
 
    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        user=settings.db_user,
        password=settings.db_password,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                if truncate:
                    cur.execute("TRUNCATE TABLE reviews_raw RESTART IDENTITY CASCADE")
                    logger.warning("Таблица reviews_raw очищена (--truncate)")
 
                cur.executemany(INSERT_QUERY, rows)
                inserted = cur.rowcount
                logger.info(
                    "Импортировано %d из %d (дубли пропущены)", inserted, len(rows)
                )
                return inserted
    finally:
        conn.close()
 
 
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Импорт отзывов из JSON в БД")
    parser.add_argument(
        "--file",
        required=True,
        help="Путь к JSON-файлу с отзывами",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Очистить таблицу перед импортом (осторожно!)",
    )
    return parser.parse_args()
 
 
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
        logging.StreamHandler(),                    
        logging.FileHandler("app.log", encoding="utf-8"),
    ]
    )
    args = parse_args()
    try:
        import_reviews(args.file, truncate=args.truncate)
    except Exception as e:
        logger.error("Импорт завершился с ошибкой: %s", e)
        sys.exit(1)
 