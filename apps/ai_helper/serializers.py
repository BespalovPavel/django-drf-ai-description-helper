from rest_framework import serializers


class ProductInputSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        required=True,
        allow_blank=False,
        help_text="Название прибора",
    )
    manufacturer = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        help_text="Производитель",
    )
    specs = serializers.DictField(
        child=serializers.CharField(),
        required=False,
        default=dict,
        help_text="Словарь технических характеристик",
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Текстовое описание или фрагмент технического паспорта",
    )


class ProductCardOutputSerializer(serializers.Serializer):
    seo_title = serializers.CharField(max_length=70, help_text="SEO-заголовок")
    seo_description = serializers.CharField(help_text="SEO-описание товара")
    key_specs = serializers.DictField(
        child=serializers.CharField(),
        help_text="Характеристики прибора",
    )
    search_queries = serializers.ListField(
        child=serializers.CharField(),
        help_text="3-5 целевых поисковых запроса",
    )
    commercial_block = serializers.CharField(
        help_text="Сферы применения и решаемые задачи"
    )
    missing_critical_data = serializers.ListField(
        child=serializers.CharField(),
        help_text="Параметры, которые не найдены во входе и требуют уточнения",
    )


class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.BooleanField(default=True, help_text="Флаг наличия ошибки")
    error_id = serializers.CharField(
        help_text="Уникальный короткий ID ошибки для логов"
    )
    error_type = serializers.CharField(
        help_text="Категория ошибки (validation_error, ai_provider_error и т.д.)"
    )
    message = serializers.CharField(help_text="Человекочитаемое описание ошибки")
    code = serializers.CharField(help_text="Код ошибки")
    details = serializers.DictField(
        required=False,
        help_text="Детализация ошибок по полям (только при 400 validation_error)",
    )
    timestamp = serializers.DateTimeField(
        help_text="Время возникновения ошибки (ISO 8601)"
    )
    path = serializers.CharField(help_text="URL запроса")
    method = serializers.CharField(help_text="HTTP-метод")
