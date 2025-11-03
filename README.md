# YouTube → RuTube Autoposter

Автоматизирует публикацию роликов на RuTube сразу после выхода на YouTube. Сервис включает вебхук WebSub, резервный RSS-поллинг, пайплайн скачивания/транскодирования/аплоада и очередь RQ.

## Возможности
- WebSub нотификации и резервный RSS-поллер.
- Скачивание через `yt-dlp`, опциональный `ffmpeg` транскодинг.
- Маппинг метаданных YouTube → RuTube (название, описание, теги, видимость, превью).
- Загрузка в RuTube Studio с Playwright (Chromium, headless) и storage state.
- Дедупликация по `videoId` (SQLite).
- RQ + Redis: ретраи с экспоненциальным бэкофом, worker, DLQ через стандартный реестр RQ.
- Docker + docker-compose для быстрого запуска.

## Быстрый старт
1. Скопируйте `.env.example` → `.env` и заполните `YOUTUBE_CHANNEL_ID`, домен коллбэка и прочие параметры.
2. Запустите сервисы: `make up`.
3. Авторизуйте аккаунт RuTube и сохраните cookies: `make auth` (откроется окно Chromium, после логина нажмите Enter в терминале). Файл появится в `auth/rutube_cookies.json`.
4. Подпишитесь на WebSub (однократно): `python scripts/init_websub.py`.
5. Проверка живости: `curl http://localhost:8080/health` и `curl http://localhost:8080/api/version`.
6. Тест ручного запуска: `curl "http://localhost:8080/api/trigger?videoId=<TEST_ID>"`. После успешного выполнения появится публикация на RuTube.

## Запуск без Docker
```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
python -m app.workers.worker
python -m app.services.rss
```

## Тесты и линтеры
```bash
make test        # pytest
make lint        # ruff + mypy
```

## Структура
```
app/
  main.py             # FastAPI приложение
  routes/             # вебхуки, админские ручки
  services/           # rss-поллер, downloader, transcoder, mapper, uploader, orchestrator
  db/                 # SQLAlchemy модель и доступа к данным
  workers/worker.py   # RQ worker
scripts/
  init_websub.py      # подписка на WebSub
  auth_playwright.py  # интерактивная авторизация и сохранение storage_state
tests/                # pytest сценарии
```

## Playwright и селекторы RuTube
- Загрузка: `input[type="file"]`.
- Название: `textarea[name="title"]`, `[data-testid="title-input"]` (fallback).
- Описание: `textarea[name="description"]`, `[data-testid="description-input"]`.
- Теги: `[data-testid="tags-input"] input`, `input[placeholder*="Теги"]`.
- Видимость: поиск по тексту `Открытый доступ` / `Доступ по ссылке` / `Частный доступ`.
- Превью: `input[type="file"][data-testid="thumbnail-upload"]`, `input[name="poster"]`.

При изменении UI достаточно обновить списки селекторов в `app/services/uploader.py` (все сгруппированы в начале файла). Скрипт логирует «uploader_thumbnail_ui_unavailable», если RuTube временно недоступен для загрузки превью.

## Очередь и ретраи
- Очередь публикаций `publish`, job-id формата `publish:<videoId>`.
- Ретраи: до 5 попыток, экспоненциальная задержка с джиттером.
- Конкурентность ограничена Redis-lock на `videoId`.
- Неуспешные задачи остаются в `FailedJobRegistry` RQ — просматривайте через `rq info` или CLI. Для ручного повтора используйте `curl /api/trigger?videoId=...&force=true`.

## Конфигурация
Переменные окружения описаны в `.env.example`. Главное:
- `WORK_DIR` — временные файлы задач (по умолчанию монтируется в `./data`).
- `DATABASE_PATH` — путь к SQLite.
- `ENABLE_TRANSCODE` — включает обязательный прогон через `ffmpeg`.
- `RUTUBE_VISIBILITY` — целевая видимость.
- `TAGS_FROM_YT`, `TITLE_PREFIX/TITLE_SUFFIX`, лимиты по длинам.

## Полезные команды
- `make worker` — локальный запуск RQ worker.
- `make scheduler` — запуск RSS-поллера.
- `python scripts/init_websub.py` — повторная подписка (идемпотентно).
- `curl http://localhost:8080/api/published?limit=20` — последние публикации.

## Обновление селекторов RuTube
1. Запустите `make auth` и зайдите в RuTube Studio.
2. Откройте инструменты разработчика, найдите актуальные селекторы.
3. Обновите константы `TITLE_SELECTORS`, `DESCRIPTION_SELECTORS`, `TAGS_SELECTORS`, `PREVIEW_SELECTORS`, `VISIBILITY_LABELS`.
4. Добавьте описание изменений в README (при необходимости).

## Примечания
- База SQLite и cookies хранятся в volume/директории хоста (`./data`, `./auth`).
- Cookies не логируются, файл `auth/rutube_cookies.json` используется во всех контейнерах.
- При сетевых проблемах пайплайн выполняет ретраи и пишет JSON-логи (через structlog).
- Для продакшна рекомендуется вынести Redis/БД наружу и использовать менеджер секретов.
