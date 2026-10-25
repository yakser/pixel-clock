# Pixel Clock

[![CI](https://github.com/yakser/pixel-clock/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/yakser/pixel-clock/actions/workflows/ci.yml)
[![Python 3.15.1](https://img.shields.io/badge/Python-3.15.1-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv 0.13.5+](https://img.shields.io/badge/uv-0.13.5%2B-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/badge/lint-Ruff-D7FF64?logo=ruff&logoColor=black)](https://docs.astral.sh/ruff/)

Учебный FastAPI-сервис: текущее время в JSON и в виде пиксельного PNG.
Цвета и размер изображения меняются через API.
Для разработчиков, которым нужно получать время и готовое изображение часов
через HTTP API.

<p align="center">
  <img src="assets/pixel-clock.png" alt="Пример часов: 12:34:56">
</p>

Пример PNG для `12:34:56` при `scale=12`.

## Установка

Установите [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.5
или новее. Склонируйте проект и установите зависимости:

```sh
git clone https://github.com/yakser/pixel-clock.git
cd pixel-clock
uv sync --locked
```

uv установит Python 3.15.1 из `.python-version`, если его нет, создаст `.venv`
и установит зависимости из `uv.lock`. `--locked` проверяет соответствие
lock-файла `pyproject.toml` и запрещает его изменение.

## Запуск

```sh
uv run uvicorn app_final:app --host 127.0.0.1 --port 8000 --workers 1
```

API доступен на `http://127.0.0.1:8000`, Swagger UI – на
[127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Остановка – Ctrl+C.

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

Размер PNG – `29 × scale` на `7 × scale`: по умолчанию 116×28, максимум 580×140.
Цифры рисуются без сглаживания, изображение непрозрачное. Время – `HH:MM:SS`.
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

64 проверки в `test_app.py` покрывают маршруты, часовые пояса и переход DST,
пиксели и размеры PNG, валидацию настроек, сохранение состояния при ошибках,
конкурентные обновления, изоляцию экземпляров приложения и логи.

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python -m pytest -v
```

Mypy строго проверяет типы в трёх модулях приложения; тесты в эту проверку не входят.
Pytest проверяет корректность конфигурации и маркеров, а неожиданный успех `xfail`
считает ошибкой.

При запуске тестов измеряется покрытие строк и ветвей приложения. Общий порог –
95%; если покрытие ниже, проверка завершается ошибкой. В консоли показаны результаты
по модулям и номера непокрытых строк.

Для HTML-отчёта выполните:

```sh
uv run python -m pytest -v --cov-report=html:htmlcov
```

Откройте `htmlcov/index.html` в браузере.

В активированном окружении тесты запускаются и без uv:

```sh
source .venv/bin/activate
python -m pytest -v
```

Списки зависимостей для pip экспортированы в `requirements.txt` и
`requirements-dev.txt`. Их источник – `pyproject.toml` и `uv.lock`.

## Логи и диагностика

Логи выводятся в терминал сервера: запуск, выбранный пояс и HTTP-запросы.
При изменении настроек записываются старые и новые значения. При генерации PNG –
время, пояс, настройки, ширина, высота, формат, цветовой режим и размер в байтах.

- `Connection refused`: проверьте, что сервер запущен на указанном порту.
- `Address already in use`: выберите свободный порт через `--port`.
- `Invalid PIXEL_CLOCK_TIMEZONE`: исправьте имя пояса или сбросьте переменную.
- `422`: поле и причина ошибки указаны в JSON `detail`.
- Одноцветный PNG: проверьте, что цвета цифр и фона различаются.
- Настройки сбросились: это ожидаемо после перезапуска.

## CI

GitHub Actions запускается на push и pull request: устанавливает зависимости,
проверяет код Ruff и mypy, выполняет тесты с покрытием и сверяет requirements
с lock-файлом. HTML-отчёт сохраняется отдельным artifact `coverage-report`, в том
числе при неуспешных тестах, если отчёт успел сформироваться.
После успешных проверок собирает artifact `pixel-clock` и проверяет его
установку, Ruff, mypy и тесты в отдельной папке.

Artifact `pixel-clock` содержит код приложения, тесты, пример PNG, эту инструкцию и файлы
зависимостей (`pyproject.toml`, `uv.lock`, `requirements*.txt`). Python и
установленные библиотеки, кеши и отчёты покрытия в этот архив не входят.

Скачайте artifact со страницы успешного запуска Actions и распакуйте.
В распакованной папке выполните `uv sync --locked`, затем команду из раздела
«Запуск». Клонировать репозиторий для этого не нужно.
