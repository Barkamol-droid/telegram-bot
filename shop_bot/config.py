import os
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
]
DB_PATH = os.getenv("DB_PATH", "shop.db")
# PostgreSQL ulanish manzili (masalan Railway Postgres). Berilsa, SQLite o'rniga ishlatiladi
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
CURRENCY = {"uz": "so'm", "ru": "сум", "tg": "сум", "kk": "сум"}

SHOP_NAME = os.getenv("SHOP_NAME", "Azure Jewelry")
# Kanal (@ bilan yoki to'liq havola). Bo'sh qoldirilsa, kanal tugmasi chiqmaydi
CHANNEL = os.getenv("CHANNEL", "@azure_jewelry").strip()


def _env_text(name: str, lang: str) -> str | None:
    """Matnni .env dan olish: avval NAME_RU kabi tilga xos, bo'lmasa umumiy NAME."""
    value = os.getenv(f"{name}_{lang.upper()}") or os.getenv(name)
    return value.replace("\\n", "\n") if value else None


# Vaqt mintaqasi (aksiya boshlanishi/tugashi va buyurtma vaqti shu bo'yicha)
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Tashkent"))


def now() -> datetime:
    return datetime.now(TIMEZONE)


# Birinchi ishga tushirishda yaratiladigan kategoriyalar (uz, ru, tg, kk)
DEFAULT_CATEGORIES = [
    {"uz": "💍 Uzuklar", "ru": "💍 Кольца", "tg": "💍 Ангуштаринҳо", "kk": "💍 Сақиналар"},
    {"uz": "✨ Sirg'alar", "ru": "✨ Серьги", "tg": "✨ Гӯшворҳо", "kk": "✨ Сырғалар"},
    {"uz": "📿 Zanjirlar", "ru": "📿 Цепочки", "tg": "📿 Занҷирҳо", "kk": "📿 Шынжырлар"},
    {"uz": "💎 Bilakuzuklar", "ru": "💎 Браслеты", "tg": "💎 Дастпонаҳо", "kk": "💎 Білезіктер"},
    {"uz": "🌸 Kulonlar", "ru": "🌸 Кулоны", "tg": "🌸 Овезаҳо", "kk": "🌸 Кулондар"},
    {"uz": "🎁 To'plamlar", "ru": "🎁 Комплекты", "tg": "🎁 Маҷмӯаҳо", "kk": "🎁 Жиынтықтар"},
]


def channel_url() -> str | None:
    if not CHANNEL:
        return None
    if CHANNEL.startswith("http"):
        return CHANNEL
    return "https://t.me/" + CHANNEL.lstrip("@")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def fmt_price(amount: int, lang: str = "uz") -> str:
    return f"{int(amount):,}".replace(",", " ") + " " + CURRENCY.get(lang, CURRENCY["uz"])
