# AI Product Description Helper API

Прототип сервиса автоматической подготовки черновиков карточек товаров КИПиА на Django 6 / Python 3.13 / Gemini API.

---

## Функционал

- **Создание черновика:** по входным данным о контрольно-измерительном
  приборе создаёт черновик карточки товара для B2B-интернет-магазина.
- **Документация Swagger:** доступна по адресу `/api/docs/`.

---

## Технологический стек

- **Язык и среда:** Python 3.12+, `uv`
- **Бэкенд:** Django 6, Django REST Framework
- **Документация:** OpenAPI / Swagger UI (`drf-spectacular`)

---

## Ключевые архитектурные решения

1. **Декомпозиция бизнес-логики:** views / services / serializers / schemas / prompts и т.д.
2. **Архитектура промпта, защита от галлюцинаций и инъекций:** Взаимодействие с Google Gemini реализовано через официальный SDK `google-genai` с передачей `response_schema=LLMProductCardOutput` и `response_mime_type="application/json"`. Для обхода ограничения Gemini Developer API на произвольные ключи словаря (`additionalProperties`) модель возвращает типизированный список объектов `list[CharacteristicItem]`, который трансформируется в словарь `key_specs: dict[str, str]`.
   Реализован контроль объёма, поставлен запрет на додумывание информации. Для защиты от инъекций все входные данные рассматриваются как недоверенные данные. В начале промпта задан абсолютный приоритет системных правил над пользовательским вводом, блокирующий попытки переопределения роли, вывода системного промпта или инъекции вредоносной разметки.

3. **Централизованная обработка ошибок:** Исключения перехватываются глобальным обработчиком `custom_exception_handler`, возвращая предсказуемый JSON:

```json
{
  "error": true,
  "error_id": "...",
  "timestamp": "...",
  "path": "...",
  "method": "...",
  "error_type": "...",
  "message": "...",
  "details": "...",
  "code": "..."
}
```

---

## Как запустить проект

### Предварительные требования

- **Python 3.12+**
- Пакетный менеджер **[uv](https://docs.astral.sh/uv/)**
- Бесплатный API-ключ **Google Gemini** ([Google AI Studio](https://aistudio.google.com/apikey))

---

### 1. Клонирование репозитория

```bash
git clone https://github.com/BespalovPavel/django-drf-ai-description-helper.git
cd django-drf-ai-description-helper
```

### 2. Настройка переменных окружения

Создайте файл `.env` в корне проекта (на основе `.env.example`):

```bash
cp .env.example .env
```

Заполните `.env` (обязательно укажите ваш `GEMINI_API_KEY`):

```env
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

GEMINI_API_KEY=ваш_ключ_из_google_ai_studio
GEMINI_MODEL=gemini-3.5-flash-lite

# База данных (по умолчанию False — используется локальный SQLite без необходимости поднимать PostgreSQL)
USE_POSTGRES=False
```

### 3. Установка зависимостей

Проект использует менеджер пакетов **uv** (создаст виртуальное окружение `.venv` и установит все пакеты из `uv.lock`):

```bash
uv sync
```

\*(Если `uv` ещё не установлен в системе, установите его одной командой: `pip install uv`)\*

### 4. Применение миграций и запуск сервера

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

Сервер запустится по адресу: `http://127.0.0.1:8000/`

---

## Как протестировать работу сервиса

После запуска сервера доступны **3 способа** отправки данных о товаре:

### Способ 1. Через интерактивный Swagger UI (Рекомендуется)

1. Откройте в браузере: **[http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)**
2. Раскройте метод `POST /api/ai/generate-card/`.
3. Нажмите кнопку **Try it out** (в поле запроса уже предзаполнен пример с манометром `DM 02` из тестового задания).
4. Нажмите **Execute** — ниже отобразится сгенерированный JSON карточки товара.

### Способ 2. Через веб-форму DRF Browsable API

1. Откройте в браузере: **[http://127.0.0.1:8000/api/ai/generate-card/](http://127.0.0.1:8000/api/ai/generate-card/)**
2. Вставьте входной JSON товара в текстовое поле **Content** и нажмите кнопку **POST**.

### Способ 3. Через `curl` из терминала

```bash
curl -X POST http://127.0.0.1:8000/api/ai/generate-card/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Манометр показывающий DM 02",
    "manufacturer": "Манотомь",
    "specs": {
      "диапазон измерений": "0–1,6 МПа",
      "класс точности": "1,5",
      "присоединение": "G1/2",
      "диаметр корпуса": "100 мм"
    },
    "description": "Прибор предназначен для измерения избыточного давления некристаллизующихся сред, неагрессивных к медным сплавам..."
  }'
```

---

Проверка кода линтером и форматером (`ruff`):

```bash
uv run ruff check .
uv run ruff format --check .
```

---

## Документация API и панель управления

- **Интерактивная документация Swagger UI:** [http://127.0.0.1:8000/api/docs/](http://127.0.0.1:8000/api/docs/)
- **Схема OpenAPI (JSON):** [http://127.0.0.1:8000/api/schema/](http://127.0.0.1:8000/api/schema/)
- **Админ-панель Django:** [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)

---

## Основные зависимости

### [django rest framework](https://www.django-rest-framework.org/)

### [django debug toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/)

### [drf-spectacular](https://drf-spectacular.readthedocs.io/en/latest/readme.html)
