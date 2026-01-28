# Kassa Core Backend

Backend-проект на Django 6 + Django REST Framework для управления пользователями, точками продаж и интеграциями.

## Требования

- Python 3.12
- Poetry
- PostgreSQL

## Переменные окружения

Минимальный набор переменных, ожидаемых приложением:

- `DJANGO_SECRET_KEY` — секретный ключ Django
- `DJANGO_DEBUG` — режим отладки (`true`/`false`)
- `DJANGO_ALLOWED_HOSTS` — список хостов (через запятую)
- `POSTGRES_DB` — имя базы данных
- `POSTGRES_USER` — пользователь БД
- `POSTGRES_PASSWORD` — пароль пользователя БД
- `POSTGRES_HOST` — хост БД
- `POSTGRES_PORT` — порт БД
- `DADATA_AUTH_TOKEN` — токен доступа к Dadata API
- `ENVIRONMENT` — окружение (`dev` или `prod`)

## Установка и запуск

```bash
poetry install

cp .env.example .env  # при наличии шаблона

poetry run python manage.py migrate
poetry run python manage.py createsuperuser

poetry run python manage.py runserver
```

Альтернативно можно использовать Docker:

```bash
docker-compose up --build
```

## Тесты

Для запуска тестов используется `pytest` и `pytest-django`:

```bash
poetry run pytest
```

## Структура тестов

- `accounts/tests/test_models.py` — тесты моделей и сигналов приложения `accounts`
- `common/tests/test_models.py` — тесты общих моделей (`BaseModel`, `Address`)
- `stores/tests/test_models.py` — тесты моделей приложения `stores`
- `common/tests/test_error_handling.py` — тесты централизованной обработки ошибок и middleware

