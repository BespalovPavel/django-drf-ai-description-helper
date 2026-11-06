import uuid
from datetime import UTC, datetime
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from loguru import logger
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    MethodNotAllowed,
    NotFound,
    ParseError,
    Throttled,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class AIServiceAPIException(APIException):
    """Базовое исключение для сервиса"""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Произошла ошибка при обращении к LLM-провайдеру"
    default_code = "ai_service_error"

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(detail, code)
        if status_code:
            self.status_code = status_code


class LLMConfigurationError(AIServiceAPIException):
    """Отсутствует или некорректен API-ключ провайдера"""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Сервис AI не сконфигурирован (отсутствует или невалиден API-ключ)"
    default_code = "llm_configuration_error"


class LLMProviderUnavailableError(AIServiceAPIException):
    """Все модели в цепочке вернули 503/500 или таймаут"""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Серверы LLM временно перегружены или недоступны. Попробуйте позже"
    default_code = "llm_provider_unavailable"


class LLMQuotaExceededError(AIServiceAPIException):
    """Превышена квота бесплатного тарифа"""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Превышен лимит запросов к LLM API"
    default_code = "llm_quota_exceeded"


class LLMInvalidResponseError(AIServiceAPIException):
    """Модель вернула невалидный JSON"""

    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "Модель LLM вернула некорректную структуру данных"
    default_code = "llm_invalid_response"


def format_validation_errors(validation_errors: Any) -> Any:
    if isinstance(validation_errors, dict):
        return {
            field: [str(err) for err in errors]
            if isinstance(errors, list)
            else [str(errors)]
            for field, errors in validation_errors.items()
        }
    if isinstance(validation_errors, list):
        return [str(error) for error in validation_errors]
    return [str(validation_errors)]


def log_exception(exc: Exception, context: dict[str, Any], error_id: str) -> None:
    view = context.get("view")
    request: Request | None = context.get("request")

    log_context = {
        "error_id": error_id,
        "exception_type": type(exc).__name__,
        "view": f"{view.__class__.__module__}.{view.__class__.__name__}"
        if view
        else None,
        "path": request.path if request else None,
        "method": request.method if request else None,
    }

    if isinstance(exc, (ValidationError, ParseError, NotFound)):
        logger.warning(
            f"Client Request Error [{error_id}]: {exc} | context={log_context}"
        )
    elif isinstance(exc, AIServiceAPIException):
        logger.warning(f"AI Domain Error [{error_id}]: {exc} | context={log_context}")
    else:
        logger.exception(
            f"Unhandled Server Error [{error_id}]: {exc} | context={log_context}"
        )


def build_error_response(
    exc: Exception,
    original_data: Any,
    request: Request | None,
    error_id: str,
) -> dict[str, Any]:
    error_response: dict[str, Any] = {
        "error": True,
        "error_id": error_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "path": request.path if request else None,
        "method": request.method if request else None,
    }

    if isinstance(exc, ValidationError):
        error_response.update(
            {
                "error_type": "validation_error",
                "message": "Ошибка валидации входных данных о товаре",
                "details": format_validation_errors(original_data),
                "code": getattr(exc, "default_code", "validation_error"),
            }
        )

    elif isinstance(exc, ParseError):
        error_response.update(
            {
                "error_type": "invalid_json",
                "message": "Некорректный входной JSON: проверьте синтаксис (кавычки, запятые, скобки)",
                "code": "parse_error",
            }
        )

    elif isinstance(exc, AIServiceAPIException):
        error_response.update(
            {
                "error_type": "ai_provider_error",
                "message": str(exc.detail) if hasattr(exc, "detail") else str(exc),
                "code": getattr(exc, "default_code", "ai_service_error"),
            }
        )

    elif isinstance(exc, Throttled):
        error_response.update(
            {
                "error_type": "rate_limit_exceeded",
                "message": "Превышен лимит запросов к сервису",
                "code": "throttled",
                "retry_after_seconds": exc.wait,
            }
        )

    elif isinstance(exc, MethodNotAllowed):
        error_response.update(
            {
                "error_type": "method_not_allowed",
                "message": f"Метод {request.method if request else ''} не поддерживается. Используйте POST",
                "code": "method_not_allowed",
            }
        )

    elif isinstance(exc, UnsupportedMediaType):
        error_response.update(
            {
                "error_type": "unsupported_media_type",
                "message": "Неподдерживаемый формат данных (ожидается application/json)",
                "code": "unsupported_media_type",
            }
        )

    else:
        detail_msg = (
            original_data.get("detail", "Произошла ошибка при обработке запроса")
            if isinstance(original_data, dict)
            else str(original_data)
        )
        error_response.update(
            {
                "error_type": "api_error",
                "message": detail_msg,
                "code": getattr(exc, "default_code", "api_error"),
            }
        )

    return error_response


def custom_exception_handler(
    exc: Exception, context: dict[str, Any]
) -> Response | None:
    response = drf_exception_handler(exc, context)
    request: Request | None = context.get("request")
    error_id = str(uuid.uuid4())[:8]

    log_exception(exc, context, error_id)

    if response is not None:
        response.data = build_error_response(exc, response.data, request, error_id)
        if isinstance(exc, Throttled) and exc.wait:
            response["Retry-After"] = str(int(exc.wait))
        return response

    if isinstance(exc, DjangoValidationError):
        return Response(
            {
                "error": True,
                "error_id": error_id,
                "error_type": "validation_error",
                "message": "Ошибка валидации данных",
                "details": exc.message_dict
                if hasattr(exc, "message_dict")
                else [str(exc)],
                "code": "validation_error",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.path if request else None,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, Http404):
        return Response(
            {
                "error": True,
                "error_id": error_id,
                "error_type": "not_found",
                "message": "Запрашиваемый эндпоинт не найден",
                "code": "not_found",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": request.path if request else None,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "error": True,
            "error_id": error_id,
            "error_type": "server_error",
            "message": "Внутренняя ошибка сервера",
            "code": "internal_server_error",
            "timestamp": datetime.now(UTC).isoformat(),
            "path": request.path if request else None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
