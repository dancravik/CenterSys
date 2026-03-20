from enum import Enum
from pydantic import BaseModel, Field, field_validator



class SentimentEnum(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class AspectEnum(str, Enum):
    INFRASTRUCTURE = "Инфраструктура и МТБ"
    TEACHING = "Преподавание и кадры"
    ADMINISTRATION = "Администрация и орг. процессы"
    OVERALL = "Общий настрой и рекомендации"
    ATMOSPHERE = "Атмосфера и студенческая общность"
    ACADEMICS = "Академические возможности"
    REPUTATION = "Репутация и бренд"
    CAREER = "Карьера и связь с практикой"
    WORKLOAD = "Учебная нагрузка и сложность"
    OTHER = "Другое"


class ReviewSegment(BaseModel):
    text: str = Field(
        description="ТОЧНАЯ цитата из отзыва. Строгая подстрока без перефразирования."
    )
    aspect: AspectEnum = Field(
        description="К какому аспекту из списка относится этот фрагмент."
    )
    sentiment: SentimentEnum = Field(
        description="Тональность конкретно этого фрагмента."
    )
    entity: str = Field(
        description=(
            "Конкретный объект, человек или процесс из цитаты в начальной форме "
            "(именительный падеж, единственное число). "
            "Например: 'преподаватель', 'туалет', 'расписание', 'документ'. "
            "Максимум 1-3 слова."
        )
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Текст сегмента не может быть пустым")
        return cleaned


class LLMReviewResponse(BaseModel):
    is_relevant: bool = Field(
        description=(
            "True, если текст похож на реальный отзыв об учебном заведении. "
            "False, если это спам, стихи, бессмысленный набор букв или текст на отвлеченную тему."
        )
    )
    segments: list[ReviewSegment] = Field(
        description="Список смысловых фрагментов отзыва"
    )
    overall_sentiment: SentimentEnum = Field(
        description="Общая тональность всего отзыва целиком"
    )
