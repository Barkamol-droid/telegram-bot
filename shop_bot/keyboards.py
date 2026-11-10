"""Bot klaviaturalari va umumiy matnlar."""
from html import escape

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import SHOP_NAME, channel_url, fmt_price

# ---- Asosiy menyu tugmalari matni ----
BTN_CATALOG = "🛍 Katalog"
BTN_CART = "🛒 Savat"
BTN_ORDERS = "📦 Buyurtmalarim"
BTN_CONTACT = "☎️ Aloqa"
BTN_CHANNEL = "📢 Kanalimiz"
BTN_ABOUT = "💎 Biz haqimizda"
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
        [KeyboardButton(text=BTN_ORDERS), KeyboardButton(text=BTN_ABOUT)],
        [KeyboardButton(text=BTN_CHANNEL) if channel_url() else None, KeyboardButton(text=BTN_CONTACT)],
    ]
    rows[-1] = [b for b in rows[-1] if b]
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
def channel_kb() -> InlineKeyboardMarkup | None:
    url = channel_url()
    if not url:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📢 Kanalga o'tish", url=url)]])


def welcome_text(first_name: str) -> str:
    return (
        f"Assalomu alaykum, <b>{escape(first_name)}</b>! 👋\n\n"
        f"💎 <b>{escape(SHOP_NAME)}</b> zargarlik do'koniga xush kelibsiz!\n\n"
        "Bu yerda siz uzuk, sirg'a, zanjir, bilakuzuk va boshqa nafis taqinchoqlarni "
        "ko'rib, bir necha bosishda buyurtma berishingiz mumkin.\n\n"
        "👇 Boshlash uchun «🛍 Katalog» tugmasini bosing."
    )


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


def product_kb(product_id: int, category_id: int, qty: int = 1,
               sizes: list[str] | None = None, size: str = "") -> InlineKeyboardMarkup:
    """Mahsulot kartasi. sizes bo'lsa — o'lcham tanlash tugmalari chiqadi.
    Callback formatlari: sz:<id>:<o'lcham>:<miqdor>, qty:<id>:<miqdor>:<o'lcham>, add:<id>:<miqdor>:<o'lcham>"""
    rows = []
    if sizes:
        size_buttons = [
            InlineKeyboardButton(
                text=f"✅ {s}" if s == size else s,
                callback_data=f"sz:{product_id}:{s}:{qty}",
            )
            for s in sizes
        ]
        rows += [size_buttons[i:i + 4] for i in range(0, len(size_buttons), 4)]
    rows.append([
        InlineKeyboardButton(text="➖", callback_data=f"qty:{product_id}:{qty - 1}:{size}"),
        InlineKeyboardButton(text=f"{qty} dona", callback_data="noop"),
        InlineKeyboardButton(text="➕", callback_data=f"qty:{product_id}:{qty + 1}:{size}"),
    ])
    rows.append([InlineKeyboardButton(text="🛒 Savatga qo'shish", callback_data=f"add:{product_id}:{qty}:{size}")])
    rows.append([
        InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"cat:{category_id}"),
        InlineKeyboardButton(text="🛒 Savat", callback_data="cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_text(p, sizes: list[str] | None = None) -> str:
    text = f"💎 <b>{escape(p['name'])}</b>\n\n"
    if p.get("description"):
        text += f"{escape(p['description'])}\n\n"
    if sizes:
        text += f"📏 O'lchamlar: {escape(', '.join(sizes))}\n"
        text += "👇 Kerakli o'lchamni tanlang\n\n"
    text += f"💰 Narxi: <b>{fmt_price(p['price'])}</b>"
    return text


def size_label(size: str | None) -> str:
    return f" (o'lcham: {escape(size)})" if size else ""


# ---------------- Savat ----------------
def cart_kb(items) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in items:
        label = f"{i['name']} ({i['size']})" if i["size"] else i["name"]
        kb.button(text=f"❌ {label}", callback_data=f"cart_del:{i['product_id']}:{i['size']}")
    kb.button(text="🧹 Savatni tozalash", callback_data="cart_clear")
    kb.button(text="✅ Buyurtma berish", callback_data="checkout")
    kb.adjust(1)
    return kb.as_markup()


def cart_text(items) -> str:
    lines = ["🛒 <b>Savatingiz:</b>\n"]
    for n, i in enumerate(items, 1):
        lines.append(
            f"{n}. {escape(i['name'])}{size_label(i['size'])}\n"
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
    if order.get("comment"):
        lines.append(f"💬 Izoh: {escape(order['comment'])}")
    lines.append(f"🕒 {order['created_at']}")
    lines.append("")
    for i in items:
        lines.append(f"• {escape(i['name'])}{size_label(i.get('size'))} — {i['qty']} x {fmt_price(i['price'])}")
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
