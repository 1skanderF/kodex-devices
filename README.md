# kodex-devices

Внутренний сервис учёта устройств на объектах и обращений по ним. Версия 0.3.1.

## Что делает

- справочник устройств (`/devices`): серийный номер, объект, модель, дата установки, когда устройство последний раз выходило на связь;
- обращения по устройствам (`/tickets`): создание, список, закрытие;
- отчёты: сводка по объектам (`/report/summary`), устройства не на связи (`/report/offline`).

Устройства (камеры распознавания, шлагбаумы, весы) раз в несколько минут выгружают heartbeat-файлы (JSON).
На сервере их по расписанию импортирует `scripts/import_heartbeats.py` — он переносит записи в базу
и обновляет `last_seen`. Все времена в базе хранятся в UTC без смещения (`YYYY-MM-DDTHH:MM:SS`).

## Запуск

Нужен только Python 3.11+ (Docker не нужен).

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.init_db            # создаст app.db с тестовыми данными (снимок на 21.08.2026)
uvicorn app.main:app --reload        # http://127.0.0.1:8000/docs
```

Импорт heartbeat-файла вручную:

```bash
python -m scripts.import_heartbeats data/heartbeats_2026-08-21.json
```

Пересоздать базу с нуля: `python -m scripts.init_db --force`.

## API

| Метод и путь | Что делает |
|---|---|
| `GET /health` | проверка, что сервис жив |
| `GET /devices?site=...` | список устройств, опционально по объекту |
| `GET /devices/{id}` | карточка устройства с числом открытых обращений |
| `GET /tickets?status=open\|closed&limit=50` | список обращений |
| `POST /tickets` | создать обращение: `{"serial": "SN-0401", "title": "...", "description": "..."}` |
| `PATCH /tickets/{id}/close` | закрыть обращение |
| `GET /report/summary` | сводка: устройства по объектам с числом открытых обращений |
| `GET /report/offline?minutes=30` | устройства, от которых не было heartbeat дольше N минут |

`POST` и `PATCH` требуют заголовок `X-Api-Key` (для разработки — `dev-key`).

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DATABASE_PATH` | путь к файлу SQLite | `app.db` в рабочей директории |
| `API_KEY` | ключ для `POST`/`PATCH` | `dev-key` |
| `OFFLINE_AFTER_MIN` | через сколько минут без heartbeat устройство считается офлайн | `30` |
