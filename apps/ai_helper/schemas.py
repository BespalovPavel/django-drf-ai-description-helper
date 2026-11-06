from pydantic import BaseModel, ConfigDict, Field


class CharacteristicItem(BaseModel):
    """Отдельная характеристика товара"""

    name: str = Field(
        ...,
        description="Название технического параметра (например: 'Диапазон измерений', 'Класс точности')",
    )
    value: str = Field(
        ...,
        description="Значение параметра из входных данных. Если данных нет, строго писать: 'данных нет'",
    )


class LLMProductCardOutput(BaseModel):
    """Схема выходных данных для генерации карточки товара"""

    seo_title: str = Field(
        ...,
        description="SEO-заголовок карточки товара. Строго до 70 символов. Формат: [Тип] [Модель] [Производитель]",
    )
    seo_description: str = Field(
        ...,
        description="SEO-описание товара объемом 800-1200 символов в деловом B2B-стиле",
    )
    key_specs: list[CharacteristicItem] = Field(
        ...,
        description="Список подтвержденных технических характеристик. При отсутствии данных строго писать: 'данных нет'",
    )
    search_queries: list[str] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="3-5 целевых коммерческих поисковых запроса для B2B",
    )
    commercial_block: str = Field(
        ...,
        description="Коммерческий блок: кому подходит прибор и какие задачи решает",
    )
    missing_critical_data: list[str] = Field(
        default_factory=list,
        description="Список критических для КИПиА параметров, которые отсутствуют во входных данных (например класс точности, IP, межповерочный интервал)",
    )

    model_config = ConfigDict(strict=True, from_attributes=True)
