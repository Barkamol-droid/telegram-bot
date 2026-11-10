import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
]
DB_PATH = os.getenv("DB_PATH", "shop.db")
# PostgreSQL ulanish manzili (masalan Railway Postgres). Berilsa, SQLite o'rniga ishlatiladi
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
CONTACT_TEXT = os.getenv(
    "CONTACT_TEXT", "📞 Biz bilan bog'lanish uchun adminga yozing."
).replace("\\n", "\n")
CURRENCY = "so'm"

SHOP_NAME = os.getenv("SHOP_NAME", "Azure Jewelry")
# Kanal (@ bilan yoki to'liq havola). Bo'sh qoldirilsa, kanal tugmasi chiqmaydi
CHANNEL = os.getenv("CHANNEL", "@azure_jewelry").strip()
ABOUT_TEXT = os.getenv(
    "ABOUT_TEXT",
    f"💎 <b>{SHOP_NAME}</b>\n\n"
    "Biz sifatli va nafis zargarlik buyumlarini taklif qilamiz.\n\n"
    "✨ Har bir mahsulot sifat nazoratidan o'tgan\n"
    "🎁 Sovg'a uchun chiroyli qadoqlash\n"
    "🚚 Shahar bo'ylab yetkazib berish\n"
    "💍 Uzuklar uchun o'lcham tanlash imkoniyati",
).replace("\\n", "\n")
# Birinchi ishga tushirishda yaratiladigan kategoriyalar
DEFAULT_CATEGORIES = ["💍 Uzuklar", "✨ Sirg'alar", "📿 Zanjirlar", "💎 Bilakuzuklar", "🌸 Kulonlar", "🎁 To'plamlar"]


def channel_url() -> str | None:
    if not CHANNEL:
        return None
    if CHANNEL.startswith("http"):
        return CHANNEL
    return "https://t.me/" + CHANNEL.lstrip("@")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def fmt_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + f" {CURRENCY}"
