import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = [
    int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()
]
DB_PATH = os.getenv("DB_PATH", "shop.db")
CONTACT_TEXT = os.getenv(
    "CONTACT_TEXT", "📞 Biz bilan bog'lanish uchun adminga yozing."
).replace("\\n", "\n")
CURRENCY = "so'm"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def fmt_price(amount: int) -> str:
    return f"{amount:,}".replace(",", " ") + f" {CURRENCY}"
