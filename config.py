# config.py
import os

PORT = int(os.environ.get("ARMORY_PORT", "8080"))

CACHE_DIR = ".armory_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Вайтлист доменов для прокси (SSRF-защита)
ALLOWED_HOSTS = {
    "armorywowforever.com",
    "www.armorywowforever.com",
    "nether.wowhead.com",
    "www.wowhead.com",
    "ru.wowhead.com",
}

# Жёсткий лимит на размер ответа прокси (байт)
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB

# Таймаут запроса к внешнему хосту (сек)
UPSTREAM_TIMEOUT = 12

# Сколько секунд считать кэш «свежим» на сервере (0 = бессрочно)
CACHE_TTL_SECONDS = 0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}

# === НАСТРОЙКИ ПЕРСОНАЖЕЙ ПО УМОЛЧАНИЮ ===
# Эти имена будут подставляться в поля, если в браузере ничего не сохранено.
# Оставьте пустую строку "", если поле должно быть пустым.
DEFAULT_CHARACTERS = [
    "Зарен-Сильф",
    "Конфетка-Светка",
    "Григар-Морвейн",
    "Shwarz-Mansurow",
    "Скамск-Анрон",
    "Герыч-Херыч"
]

# Источник тултипов по умолчанию
DEFAULT_SOURCE = "forever_ru"

# Позиция дока "right" или 'left'
DEFAULT_DOCK_POS = "right"  