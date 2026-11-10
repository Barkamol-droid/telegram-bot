"""Bot klaviaturalari va umumiy matnlar."""
from html import escape

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import fmt_price

# ---- Asosiy menyu tugmalari matni ----
BTN_CATALOG = "🛍 Katalog"
BTN_CART = "🛒 Savat"
BTN_ORDERS = "📦 Buyurtmalarim"
BTN_CONTACT = "☎️ Aloqa"
BTN_ADMIN = "⚙️ Admin panel"
BTN_CANCEL = "❌ Bekor qilish"
BTN_SKIP = "⏭ O'tkazib yuborish"

STATUS_LABELS = {
    "new": "🆕 Yangi",
    "accepted": "✅ Qabul qilindi",
    "delivered": "🚚 Yetkazildi",
    "cancelled": "❌ Bekor qilindi",
}


def main_menu(admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_CATALOG), KeyboardButton(text=BTN_CART)],
        [KeyboardButton(text=BTN_ORDERS), KeyboardButton(text=BTN_CONTACT)],
    ]
    if admin:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


def skip_cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)], [KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Joylashuvni yuborish", request_location=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


# ---------------- Katalog ----------------
def categories_kb(categories, prefix: str = "cat") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=c["name"], callback_data=f"{prefix}:{c['id']}")
    kb.adjust(2)
    return kb.as_markup()


def products_kb(products) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=f"{p['name']} — {fmt_price(p['price'])}", callback_data=f"prod:{p['id']}")
    kb.button(text="⬅️ Kategoriyalar", callback_data="cats")
    kb.adjust(1)
    return kb.as_markup()


def product_kb(product_id: int, category_id: int, qty: int = 1) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"qty:{product_id}:{qty - 1}"),
            InlineKeyboardButton(text=str(qty), callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"qty:{product_id}:{qty + 1}"),
        ],
        [InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add:{product_id}:{qty}")],
        [
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"cat:{category_id}"),
            InlineKeyboardButton(text="🛒 Savat", callback_data="cart"),
        ],
    ])


def product_text(p) -> str:
    text = f"<b>{escape(p['name'])}</b>\n\n"
    if p.get("description"):
        text += f"{escape(p['description'])}\n\n"
    text += f"💰 Narxi: <b>{fmt_price(p['price'])}</b>"
    return text


# ---------------- Savat ----------------
def cart_kb(items) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in items:
        kb.button(text=f"❌ {i['name']}", callback_data=f"cart_del:{i['product_id']}")
    kb.button(text="🧹 Savatni tozalash", callback_data="cart_clear")
    kb.button(text="✅ Buyurtma berish", callback_data="checkout")
    kb.adjust(1)
    return kb.as_markup()


def cart_text(items) -> str:
    lines = ["🛒 <b>Savatingiz:</b>\n"]
    for n, i in enumerate(items, 1):
        lines.append(
            f"{n}. {escape(i['name'])}\n"
            f"    {i['qty']} x {fmt_price(i['price'])} = <b>{fmt_price(i['subtotal'])}</b>"
        )
    total = sum(i["subtotal"] for i in items)
    lines.append(f"\n💰 Jami: <b>{fmt_price(total)}</b>")
    return "\n".join(lines)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="order_confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order_cancel"),
    ]])


# ---------------- Buyurtma ----------------
def order_text(order, items, for_admin: bool = False) -> str:
    lines = [f"🧾 <b>Buyurtma #{order['id']}</b>"]
    if for_admin:
        lines.append(f"👤 {escape(order['full_name'] or '')} (ID: <code>{order['user_id']}</code>)")
        lines.append(f"📞 {escape(order['phone'] or '')}")
    if order.get("address"):
        lines.append(f"📍 {escape(order['address'])}")
    elif order.get("latitude") is not None:
        lines.append("📍 Joylashuv yuborilgan")
    lines.append(f"🕒 {order['created_at']}")
    lines.append("")
    for i in items:
        lines.append(f"• {escape(i['name'])} — {i['qty']} x {fmt_price(i['price'])}")
    lines.append(f"\n💰 Jami: <b>{fmt_price(order['total'])}</b>")
    lines.append(f"📌 Holati: {STATUS_LABELS.get(order['status'], order['status'])}")
    return "\n".join(lines)


def admin_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"status:{order_id}:accepted"),
            InlineKeyboardButton(text="🚚 Yetkazildi", callback_data=f"status:{order_id}:delivered"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"status:{order_id}:cancelled")],
    ])


# ---------------- Admin ----------------
def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Kategoriya qo'shish", callback_data="adm:add_cat")
    kb.button(text="➕ Mahsulot qo'shish", callback_data="adm:add_prod")
    kb.button(text="🗑 Kategoriyani o'chirish", callback_data="adm:del_cat")
    kb.button(text="🗑 Mahsulotni o'chirish", callback_data="adm:del_prod")
    kb.button(text="📋 Buyurtmalar", callback_data="adm:orders")
    kb.button(text="📊 Statistika", callback_data="adm:stats")
    kb.button(text="📢 Xabar yuborish", callback_data="adm:broadcast")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def admin_products_delete_kb(products) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=f"🗑 {p['name']}", callback_data=f"dp:{p['id']}")
    kb.button(text="⬅️ Admin panel", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()
