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


# Bot orqali qo'shilgan adminlar (bazadan yuklanadi, db.init_db / db.add_admin yangilaydi)
EXTRA_ADMINS: set[int] = set()

# Onlayn to'lov: BotFather → Payments bo'limidan olingan provider tokenlar.
# Berilmasa, shu to'lov usuli ko'rsatilmaydi (faqat naqd to'lov qoladi).
PAYMENT_TOKENS = {
    "click": os.getenv("CLICK_TOKEN", "").strip(),
    "payme": os.getenv("PAYME_TOKEN", "").strip(),
}
PAYMENT_NAMES = {"click": "Click", "payme": "Payme"}


def payment_providers() -> list[str]:
    """Sozlangan onlayn to'lov tizimlari (tartib: Click, Payme)."""
    return [name for name, token in PAYMENT_TOKENS.items() if token]


def is_test_token(provider: str) -> bool:
    return ":TEST:" in PAYMENT_TOKENS.get(provider, "")


# Bonus (💎 brilliant): har BONUS_STEP so'm xarid uchun 1 ta, 1 ta = BONUS_VALUE so'm chegirma
BONUS_STEP = int(os.getenv("BONUS_STEP", "100000"))
BONUS_VALUE = int(os.getenv("BONUS_VALUE", "1000"))

# Sayt ko'rinishi (Telegram Mini App). Railway'da «Generate Domain» qilinganda RAILWAY_PUBLIC_DOMAIN
# avtomatik paydo bo'ladi; boshqa hostingda WEBAPP_URL ni qo'lda bering (https:// bilan).
PORT = int(os.getenv("PORT", "8080"))
_public_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
WEBAPP_URL = (os.getenv("WEBAPP_URL", "").strip() or (f"https://{_public_domain}" if _public_domain else "")).rstrip("/")
# Bot API orqali yuklab olinadigan fayl chegarasi (videolar saytda shu hajmgacha ko'rinadi)
MAX_WEB_MEDIA_BYTES = 20 * 1024 * 1024

# Kuryer boti (ixtiyoriy): BotFather'da alohida bot ochib, tokenini shu yerga bering
COURIER_BOT_TOKEN = os.getenv("COURIER_BOT_TOKEN", "").strip()

# Aloqa telefoni («☎️ Aloqa» tugmasida ko'rsatiladi)
SHOP_PHONE = os.getenv("SHOP_PHONE", "+998900441678").strip()


def is_owner(user_id: int) -> bool:
    """Bosh admin (ADMIN_IDS da ko'rsatilgan) — adminlarni qo'sha/o'chira oladi."""
    return user_id in ADMIN_IDS


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS or user_id in EXTRA_ADMINS


def all_admin_ids() -> list[int]:
    return list(dict.fromkeys([*ADMIN_IDS, *sorted(EXTRA_ADMINS)]))


def fmt_phone(phone: str) -> str:
    """+998900441678 -> +998 90 044 16 78"""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 12 and digits.startswith("998"):
        d = digits
        return f"+{d[:3]} {d[3:5]} {d[5:8]} {d[8:10]} {d[10:]}"
    return phone


def fmt_price(amount: int, lang: str = "uz") -> str:
    return f"{int(amount):,}".replace(",", " ") + " " + CURRENCY.get(lang, CURRENCY["uz"])
