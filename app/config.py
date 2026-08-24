import os

# Путь к базе. В проде задаётся через .env (см. README).
DB_PATH = os.environ.get("DATABASE_PATH", "app.db")

# Ключ для изменяющих запросов.
API_KEY = os.environ.get("API_KEY", "dev-key")

# Через сколько минут без heartbeat устройство считается офлайн.
OFFLINE_AFTER_MIN = int(os.environ.get("OFFLINE_AFTER_MIN", "30"))
