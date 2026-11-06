import json
from dataclasses import dataclass
from typing import Any, Never, cast

import httpx
from django.conf import settings
from google import genai
from google.genai import errors, types
from loguru import logger

from apps.ai_helper.prompts import SYSTEM_INSTRUCTION
from apps.ai_helper.schemas import LLMProductCardOutput
from custom_exceptions import (
    AIServiceAPIException,
    LLMConfigurationError,
    LLMInvalidResponseError,
    LLMProviderUnavailableError,
    LLMQuotaExceededError,
)

ERROR_MAP: dict[int, type[AIServiceAPIException]] = {
    401: LLMConfigurationError,
    403: LLMConfigurationError,
    429: LLMQuotaExceededError,
    500: LLMProviderUnavailableError,
    503: LLMProviderUnavailableError,
}


@dataclass(frozen=True, slots=True)
class GeneratedProductCardDTO:
    seo_title: str
    seo_description: str
    key_specs: dict[str, str]
    search_queries: list[str]
    commercial_block: str
    missing_critical_data: list[str]


class ProductCardGeneratorService:
    def __init__(self) -> None:
        self._api_key = settings.GEMINI_API_KEY
        if not self._api_key:
            logger.error("GEMINI_API_KEY_IS_EMPTY")
            raise LLMConfigurationError()

        self._client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                httpx_client=httpx.Client(timeout=30.0),
                retry_options=types.HttpRetryOptions(attempts=2),
            ),
        )
        self._model = settings.GEMINI_MODEL

    def execute(
        self,
        name: str,
        manufacturer: str = "",
        specs: dict[str, Any] | None = None,
        description: str = "",
    ) -> GeneratedProductCardDTO:
        user_prompt = self._build_user_prompt(
            name, manufacturer, specs or {}, description
        )
        logger.info(f"Запрос генерации к LLM (model={self._model} | product={name})")

        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=LLMProductCardOutput,
                ),
            )
        except Exception as exc:
            self._raise_domain_error(exc)

        if not response or not response.parsed:
            raise LLMInvalidResponseError()

        validated_output = cast(LLMProductCardOutput, response.parsed)

        return GeneratedProductCardDTO(
            seo_title=validated_output.seo_title[:70],
            seo_description=validated_output.seo_description,
            key_specs={item.name: item.value for item in validated_output.key_specs},
            search_queries=validated_output.search_queries,
            commercial_block=validated_output.commercial_block,
            missing_critical_data=validated_output.missing_critical_data,
        )

    @staticmethod
    def _build_user_prompt(
        name: str,
        manufacturer: str,
        specs: dict[str, Any],
        description: str,
    ) -> str:
        return (
            f"ВХОДНЫЕ ДАННЫЕ О ПРИБОРЕ:\n"
            f"Название: {name}\n"
            f"Производитель: {manufacturer or 'Не указан'}\n"
            f"Характеристики (specs):\n"
            f"{json.dumps(specs, ensure_ascii=False, indent=2)}\n\n"
            f"Паспорт / Описание:\n"
            f"{description or 'Не предоставлено'}"
        )

    def _raise_domain_error(self, exc: Exception) -> Never:
        if isinstance(exc, httpx.TimeoutException):
            logger.error(f"Таймаут запроса к LLM: {exc}")
            raise LLMProviderUnavailableError(
                detail="Превышено время ожидания ответа от LLM API"
            ) from exc

        if isinstance(exc, errors.APIError):
            logger.error(f"Ошибка Gemini API ({exc.code}): {exc.message}")
            exception_cls = self.ERROR_MAP.get(exc.code or 502, AIServiceAPIException)
            raise exception_cls() from exc

        logger.error(f"Сбой при вызове LLM: {exc}")
        raise AIServiceAPIException() from exc
