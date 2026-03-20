import logging
import re
import unicodedata

import pymorphy3

logger = logging.getLogger(__name__)

_morph = pymorphy3.MorphAnalyzer()


SYNONYM_MAP: dict[str, str] = {
    "вуз": "университет",
    "универ": "университет",
    "заведение": "университет",
    "учреждение": "университет",
    "институт": "университет",
    "академия": "университет",
    "учебный заведение": "университет",

    "препод": "преподаватель",
    "педагог": "преподаватель",
    "лектор": "преподаватель",
    "учитель": "преподаватель",
    "профессор": "преподаватель",
    "доцент": "преподаватель",
    "куратор": "преподаватель",

    "санузел": "туалет",
    "буфет": "кафетерий",

    "общага": "общежитие",

    "образовательное учреждение": "университет",
    "вечерняя форма": "форма обучения",
    "вечерняя форма обучения": "форма обучения",
}


def _clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text.strip().lower())


def _to_normal_form(word: str) -> str:
    words = word.split()
    if len(words) == 1:
        return _morph.parse(word)[0].normal_form
    else:
        return word


def normalize_entity(entity: str) -> str:
    cleaned = _clean(entity)
    if not cleaned:
        return entity
    normal = _to_normal_form(cleaned)
    return SYNONYM_MAP.get(normal, normal)


def normalize_segments(segments: list[dict]) -> list[dict]:
    result = []
    for seg in segments:
        raw_entity = seg.get("entity", "")
        normalized = normalize_entity(raw_entity)

        if normalized != raw_entity:
            logger.debug("entity: '%s' → '%s'", raw_entity, normalized)

        result.append({**seg, "entity": normalized})

    return result