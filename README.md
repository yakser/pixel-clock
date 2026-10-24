# Pixel Clock

[![CI](https://github.com/yakser/pixel-clock/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/yakser/pixel-clock/actions/workflows/ci.yml)
[![Python 3.15.1](https://img.shields.io/badge/Python-3.15.1-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv 0.13.5+](https://img.shields.io/badge/uv-0.13.5%2B-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)

Учебный FastAPI-сервис: текущее время в JSON и в виде пиксельного PNG.
Цвета и размер изображения меняются через API.

![Пример часов: 12:34:56](assets/pixel-clock.png)

Пример PNG для `12:34:56` при `scale=12`.

## Установка

Установите [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.5
или новее. В папке проекта выполните:

```sh
uv sync --locked
```

uv установит Python 3.15.1 из `.python-version`, если его нет, создаст `.venv`
и установит зависимости из `uv.lock`. `--locked` проверяет соответствие
lock-файла `pyproject.toml` и запрещает его изменение.

## Запуск

```sh
uv run uvicorn app_final:app --host 127.0.0.1 --port 8000 --workers 1
```

API доступен на `http://127.0.0.1:8000`, Swagger UI — на
[localhost:8000/docs](http://127.0.0.1:8000/docs). Остановка — Ctrl+C.

Запускайте один worker: настройки хранятся в памяти процесса и общие для всех
его запросов. После перезапуска они сбрасываются. Авторизации нет.

## API

| Метод и путь | Результат |
| --- | --- |
| `GET /health` | `{"status":"ok"}` |
| `GET /version` | Версия приложения из `pyproject.toml` |
| `GET /time` | Например, `{"time":"12:34:56","timezone":"Europe/Moscow"}` |
| `GET /time-png` | PNG с текущим временем |
| `PATCH /settings` | Меняет переданные настройки, возвращает полный набор |

```sh
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/version
curl -fsS http://127.0.0.1:8000/time
curl -fsS http://127.0.0.1:8000/time-png -o /tmp/pixel-clock.png
curl -fsS -X PATCH http://127.0.0.1:8000/settings \
  -H 'Content-Type: application/json' \
  -d '{"scale":6,"foreground":"#00ff00"}'
```

Ответ на PATCH:

```json
{"scale":6,"foreground":"#00FF00","background":"#000000"}
```

| Поле | Значения | По умолчанию |
| --- | --- | --- |
| `scale` | Целое число от 1 до 20 | `4` |
| `foreground` | Цвет цифр в формате `#RRGGBB` | `#FFFFFF` |
| `background` | Цвет фона в формате `#RRGGBB` | `#000000` |

Пропущенные поля сохраняются. PATCH с `{}` возвращает настройки без изменений.
Цвета в ответе приводятся к верхнему регистру. Неверные значения, неизвестные
поля и `null` возвращают `422`; настройки при этом не меняются.

Размер PNG — `29 × scale` на `7 × scale`: по умолчанию 116×28, максимум 580×140.
Цифры рисуются без сглаживания, изображение непрозрачное. Время — `HH:MM:SS`.
Картинка статичная: для обновления времени нужен новый запрос.

## Часовой пояс

`PIXEL_CLOCK_TIMEZONE` задаёт пояс IANA, по умолчанию `Europe/Moscow`.
Например, перед запуском сервера:

```sh
export PIXEL_CLOCK_TIMEZONE=UTC
```

После изменения переменной перезапустите сервер. Пустой или неизвестный пояс
вызывает ошибку запуска. `unset PIXEL_CLOCK_TIMEZONE` возвращает значение
по умолчанию. `.env.example` содержит пример; файл `.env` автоматически не читается.

## Тесты

```sh
uv run python -m pytest -v
uv run ruff check .
uv run ruff format --check .
```

В активированном окружении тесты запускаются и без uv:

```sh
source .venv/bin/activate
python -m pytest -v
```

Зависимости для установки через pip также экспортированы в `requirements.txt`
и `requirements-dev.txt`. Их источник — `pyproject.toml` и `uv.lock`.

## Логи и диагностика

Логи выводятся в терминал сервера: запуск, выбранный пояс и HTTP-запросы.
Изменение настроек также записывается в лог.

- `Connection refused`: проверьте, что сервер запущен на указанном порту.
- `Address already in use`: выберите свободный порт через `--port`.
- `Invalid PIXEL_CLOCK_TIMEZONE`: исправьте имя пояса или сбросьте переменную.
- `422`: поле и причина ошибки указаны в JSON `detail`.
- Одноцветный PNG: проверьте, что цвета цифр и фона различаются.
- Настройки сбросились: это ожидаемо после перезапуска.

## CI

GitHub Actions запускается на push и pull request: устанавливает зависимости,
проверяет код Ruff, выполняет тесты и сверяет requirements с lock-файлом.
После успешных проверок собирает artifact `pixel-clock` и проверяет его
установку и тесты в отдельной папке.

Artifact содержит приложение, зависимости, тесты и эту инструкцию. Скачайте его
со страницы успешного запуска Actions, распакуйте и выполните команды установки
и запуска выше.
