"""Bot klaviaturalari va matn shablonlari (4 tilda)."""
from html import escape

from aiogram.types import (
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestUsers,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

import pricing
from config import BONUS_VALUE, PAYMENT_NAMES, SHOP_NAME, WEBAPP_URL, channel_url, fmt_price, now, payment_providers
from i18n import LANG_NAMES, fmt_duration, loc, t

BTN_ADMIN = "⚙️ Admin panel"
STATUSES = ["new", "accepted", "delivered", "cancelled"]


def status_label(status: str, lang: str = "uz") -> str:
    return t(f"status_{status}", lang) if status in STATUSES else status


# ---------------- Asosiy menyu va oddiy tugmalar ----------------
def main_menu(lang: str, admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=t("btn_catalog", lang)), KeyboardButton(text=t("btn_cart", lang))],
        [KeyboardButton(text=t("btn_promo", lang)), KeyboardButton(text=t("btn_bonus", lang))],
        [KeyboardButton(text=t("btn_orders", lang)), KeyboardButton(text=t("btn_about", lang))],
        [KeyboardButton(text=t("btn_contact", lang)), KeyboardButton(text=t("btn_lang", lang))],
    ]
    if channel_url():
        rows.append([KeyboardButton(text=t("btn_channel", lang))])
    if admin:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def cancel_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t("btn_cancel", lang))]], resize_keyboard=True)


def skip_cancel_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("btn_skip", lang))], [KeyboardButton(text=t("btn_cancel", lang))]],
        resize_keyboard=True,
    )


def phone_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_phone", lang), request_contact=True)],
            [KeyboardButton(text=t("btn_cancel", lang))],
        ],
        resize_keyboard=True,
    )


def location_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_location", lang), request_location=True)],
            [KeyboardButton(text=t("btn_cancel", lang))],
        ],
        resize_keyboard=True,
    )


def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, name in LANG_NAMES.items():
        kb.button(text=name, callback_data=f"setlang:{code}")
    kb.adjust(2)
    return kb.as_markup()


def channel_kb(lang: str) -> InlineKeyboardMarkup | None:
    url = channel_url()
    if not url:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_open_channel", lang), url=url)]])


def shop_now_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_shop_now", lang), callback_data="shop")]])


def welcome_text(first_name: str, lang: str) -> str:
    return t("welcome", lang, name=escape(first_name or ""), shop=escape(SHOP_NAME), catalog=t("btn_catalog", lang))


# ---------------- Aksiya banneri ----------------
def promo_banner(promo: dict | None, lang: str, category: dict | None = None, footer: bool = False) -> str:
    """Faol yoki yaqinlashayotgan aksiya haqida matn. Aksiya bo'lmasa — bo'sh qator."""
    if not promo or pricing.is_finished(promo):
        return ""
    title = t("promo_title_1111" if promo.get("kind") == "1111" else "promo_title_custom", lang)
    if promo.get("category_id") and category:
        scope = t("promo_cat", lang, p=promo["percent"], cat=escape(loc(category, "name", lang)))
    else:
        scope = t("promo_all", lang, p=promo["percent"])
    period = f"📅 {promo['_start']:%d.%m %H:%M} — {promo['_end']:%d.%m %H:%M}"
    if pricing.is_running(promo):
        timer = t("promo_ends_in", lang, left=fmt_duration((promo["_end"] - now()).total_seconds(), lang))
    else:
        timer = t("promo_starts_in", lang, left=fmt_duration((promo["_start"] - now()).total_seconds(), lang))
    text = f"<b>{title}</b>\n{scope}\n{period}\n{timer}"
    if footer:
        text += f"\n\n{t('promo_footer', lang)}"
    return text


# ---------------- Katalog ----------------
def categories_kb(categories, lang: str = "uz", prefix: str = "cat") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in categories:
        kb.button(text=loc(c, "name", lang), callback_data=f"{prefix}:{c['id']}")
    kb.adjust(2)
    return kb.as_markup()


def products_kb(products, lang: str, promo: dict | None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        final, old, percent = pricing.price_info(int(p["price"]), p["category_id"], promo)
        label = f"{loc(p, 'name', lang)} — {fmt_price(final, lang)}"
        if percent:
            label += f" 🔥-{percent}%"
        kb.button(text=label, callback_data=f"prod:{p['id']}")
    kb.button(text=t("btn_back_cats", lang), callback_data="cats")
    kb.adjust(1)
    return kb.as_markup()


def open_shop_kb(lang: str, path: str = "") -> InlineKeyboardMarkup | None:
    """Saytni (Mini App) ochish tugmasi. WEBAPP_URL sozlanmagan bo'lsa — None."""
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_open_shop", lang), web_app=WebAppInfo(url=f"{WEBAPP_URL}/{path}"))
    ]])


def product_kb(product_id: int, category_id: int, lang: str, qty: int = 1,
               sizes: list[str] | None = None, size: str = "", has_video: bool = False) -> InlineKeyboardMarkup:
    """Mahsulot kartasi. sizes bo'lsa — o'lcham tanlash tugmalari chiqadi.
    Callback formatlari: sz:<id>:<o'lcham>:<miqdor>, qty:<id>:<miqdor>:<o'lcham>, add:<id>:<miqdor>:<o'lcham>"""
    rows = []
    if sizes:
        size_buttons = [
            InlineKeyboardButton(text=f"✅ {s}" if s == size else s, callback_data=f"sz:{product_id}:{s}:{qty}")
            for s in sizes
        ]
        rows += [size_buttons[i:i + 4] for i in range(0, len(size_buttons), 4)]
    rows.append([
        InlineKeyboardButton(text="➖", callback_data=f"qty:{product_id}:{qty - 1}:{size}"),
        InlineKeyboardButton(text=f"{qty} {t('pcs', lang)}", callback_data="noop"),
        InlineKeyboardButton(text="➕", callback_data=f"qty:{product_id}:{qty + 1}:{size}"),
    ])
    rows.append([InlineKeyboardButton(text=t("btn_add_cart", lang), callback_data=f"add:{product_id}:{qty}:{size}")])
    if has_video:
        rows.append([InlineKeyboardButton(text=t("btn_video", lang), callback_data=f"pvid:{product_id}")])
    rows.append([
        InlineKeyboardButton(text=t("btn_back", lang), callback_data=f"cat:{category_id}"),
        InlineKeyboardButton(text=t("btn_cart", lang), callback_data="cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def price_line(final: int, old: int | None, percent: int | None, lang: str) -> str:
    if old:
        return f"<s>{fmt_price(old, lang)}</s> <b>{fmt_price(final, lang)}</b> 🔥 -{percent}%"
    return f"<b>{fmt_price(final, lang)}</b>"


def product_text(p, lang: str, promo: dict | None, sizes: list[str] | None = None) -> str:
    text = f"💎 <b>{escape(loc(p, 'name', lang))}</b>\n\n"
    description = loc(p, "description", lang)
    if description:
        text += f"{escape(description)}\n\n"
    if sizes:
        text += f"{t('sizes', lang)}: {escape(', '.join(sizes))}\n{t('choose_size_hint', lang)}\n\n"
    final, old, percent = pricing.price_info(int(p["price"]), p["category_id"], promo)
    text += f"{t('price', lang)}: {price_line(final, old, percent, lang)}"
    if percent:
        left = fmt_duration((promo["_end"] - now()).total_seconds(), lang)
        text += f"\n{t('promo_ends_in', lang, left=left)}"
    return text


def size_label(size: str | None, lang: str) -> str:
    return t("size_label", lang, size=size) if size else ""


# ---------------- Savat ----------------
def cart_kb(items, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i in items:
        name = loc(i, "name", lang)
        label = f"{name} ({i['size']})" if i["size"] else name
        kb.button(text=f"❌ {label}", callback_data=f"cart_del:{i['product_id']}:{i['size']}")
    kb.button(text=t("btn_clear_cart", lang), callback_data="cart_clear")
    kb.button(text=t("btn_checkout", lang), callback_data="checkout")
    kb.adjust(1)
    return kb.as_markup()


def cart_text(items, lang: str) -> str:
    lines = [t("cart_title", lang) + "\n"]
    for n, i in enumerate(items, 1):
        name = escape(loc(i, "name", lang) + size_label(i["size"], lang))
        unit = price_line(i["price"], i.get("old_price"), i.get("percent"), lang)
        lines.append(f"{n}. {name}\n    {i['qty']} x {unit} = <b>{fmt_price(i['subtotal'], lang)}</b>")
    total = sum(i["subtotal"] for i in items)
    saved = sum(i.get("saved", 0) for i in items)
    if saved:
        lines.append(f"\n{t('saved', lang)}: <b>{fmt_price(saved, lang)}</b>")
    lines.append(("" if saved else "\n") + f"{t('total', lang)}: <b>{fmt_price(total, lang)}</b>")
    return "\n".join(lines)


def checkout_summary(p: dict, lang: str) -> str:
    """Savat + brilliant chegirmasi + yakuniy summa + olinadigan bonus."""
    text = cart_text(p["items"], lang)
    if p["bonus_used"]:
        text += (f"\n{t('bonus_discount_line', lang, n=p['bonus_used'])}: -{fmt_price(p['bonus_discount'], lang)}"
                 f"\n{t('to_pay', lang)}: <b>{fmt_price(p['total'], lang)}</b>")
    if p["bonus_earned"]:
        text += f"\n{t('bonus_will_earn', lang, n=p['bonus_earned'])}"
    return text


def bonus_value(n: int, lang: str) -> str:
    return fmt_price(n * BONUS_VALUE, lang)


def use_bonus_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_use_bonus", lang), callback_data="bonus_use:1")],
        [InlineKeyboardButton(text=t("btn_keep_bonus", lang), callback_data="bonus_use:0")],
    ])


def bonus_menu_kb(lang: str, has_bonus: bool) -> InlineKeyboardMarkup | None:
    if not has_bonus:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_send_bonus", lang), callback_data="bsend")]])


def pick_contact_kb(lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text=t("btn_pick_contact", lang),
                request_users=KeyboardButtonRequestUsers(
                    request_id=2, user_is_bot=False, max_quantity=1, request_name=True, request_username=True,
                ),
            )],
            [KeyboardButton(text=t("btn_cancel", lang))],
        ],
        resize_keyboard=True,
    )


def confirm_send_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_send", lang), callback_data="bsend_ok"),
        InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="bsend_no"),
    ]])


def confirm_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_confirm", lang), callback_data="order_confirm"),
        InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="order_cancel"),
    ]])


# ---------------- Buyurtma ----------------
def order_text(order, items, lang: str = "uz", for_admin: bool = False) -> str:
    lines = [t("order", lang, id=order["id"])]
    if for_admin:
        lines.append(f"👤 {escape(order['full_name'] or '')} (ID: <code>{order['user_id']}</code>)")
        lines.append(f"📞 {escape(order['phone'] or '')}")
        if order.get("lang"):
            lines.append(f"🌐 {LANG_NAMES.get(order['lang'], order['lang'])}")
    if order.get("address"):
        lines.append(f"📍 {escape(order['address'])}")
    elif order.get("latitude") is not None:
        lines.append(f"📍 {t('location_sent', lang)}")
    if order.get("comment"):
        lines.append(f"{t('comment', lang)}: {escape(order['comment'])}")
    lines.append(f"🕒 {order['created_at']}")
    lines.append("")
    for i in items:
        name = escape(loc(i, "name", lang) + size_label(i.get("size"), lang))
        lines.append(f"• {name} — {i['qty']} x {fmt_price(i['price'], lang)}")
    extra = []
    if order.get("discount"):
        extra.append(f"{t('discount', lang)}: -{fmt_price(order['discount'], lang)}")
    if order.get("bonus_used"):
        extra.append(f"{t('bonus_discount_line', lang, n=order['bonus_used'])}: -{fmt_price(order['bonus_discount'], lang)}")
    if extra:
        lines.append("\n" + "\n".join(extra))
    lines.append(("" if extra else "\n") + f"{t('total', lang)}: <b>{fmt_price(order['total'], lang)}</b>")
    if order.get("bonus_awarded") and order.get("bonus_earned"):
        lines.append(t("bonus_got", lang, n=order["bonus_earned"]))
    elif order.get("bonus_earned") and order.get("status") != "cancelled":
        lines.append(t("bonus_will_earn", lang, n=order["bonus_earned"]))
    lines.append(f"{t('status', lang)}: {status_label(order['status'], lang)}")
    lines.append(f"{t('payment', lang)}: {payment_label(order, lang)}")
    return "\n".join(lines)


# ---------------- To'lov ----------------
def payment_label(order, lang: str = "uz") -> str:
    if order.get("payment_status") == "paid":
        method = {**PAYMENT_NAMES, "bonus": "💎"}.get(order.get("payment_method"), order.get("payment_method") or "")
        return t("pay_status_paid", lang, method=method)
    if order.get("payment_method") == "cash":
        return t("pay_status_cash", lang)
    return t("pay_status_unpaid", lang)


def can_pay_online(order) -> bool:
    return (
        bool(payment_providers())
        and order.get("payment_status") != "paid"
        and order.get("status") not in ("cancelled", "delivered")
    )


def payment_kb(order_id: int, lang: str, include_cash: bool = True) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for provider in payment_providers():
        kb.button(text=f"💳 {PAYMENT_NAMES[provider]}", callback_data=f"pay:{order_id}:{provider}")
    if include_cash:
        kb.button(text=t("btn_pay_cash", lang), callback_data=f"pay:{order_id}:cash")
    kb.adjust(2, 1)
    return kb.as_markup()


def unpaid_orders_kb(orders, lang: str) -> InlineKeyboardMarkup | None:
    kb = InlineKeyboardBuilder()
    count = 0
    for o in orders:
        if can_pay_online(o) and count < 5:
            kb.button(text=t("btn_pay_order", lang, id=o["id"]), callback_data=f"paymenu:{o['id']}")
            count += 1
    kb.adjust(1)
    return kb.as_markup() if count else None


def admin_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"status:{order_id}:accepted"),
            InlineKeyboardButton(text="🚚 Yetkazildi", callback_data=f"status:{order_id}:delivered"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"status:{order_id}:cancelled")],
    ])


# ---------------- Admin (faqat o'zbek tilida) ----------------
def admin_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔥 Aksiya", callback_data="adm:promo")
    kb.button(text="➕ Kategoriya qo'shish", callback_data="adm:add_cat")
    kb.button(text="➕ Mahsulot qo'shish", callback_data="adm:add_prod")
    kb.button(text="🗑 Kategoriyani o'chirish", callback_data="adm:del_cat")
    kb.button(text="🗑 Mahsulotni o'chirish", callback_data="adm:del_prod")
    kb.button(text="📋 Buyurtmalar", callback_data="adm:orders")
    kb.button(text="📊 Statistika", callback_data="adm:stats")
    kb.button(text="📢 Xabar yuborish", callback_data="adm:broadcast")
    kb.button(text="👥 Adminlar", callback_data="adm:admins")
    kb.button(text="🎬 Rasm / video", callback_data="adm:media")
    kb.adjust(1, 2, 2, 2, 2, 1)
    return kb.as_markup()


def admin_products_delete_kb(products) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in products:
        kb.button(text=f"🗑 {p['name']}", callback_data=f"dp:{p['id']}")
    kb.button(text="⬅️ Admin panel", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def admins_kb(admins, can_manage: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if can_manage:
        kb.button(text="➕ Admin qo'shish", callback_data="ad_add")
        for a in admins:
            kb.button(text=f"🗑 {a['full_name'] or a['id']}", callback_data=f"ad_rm:{a['id']}")
    kb.button(text="⬅️ Admin panel", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def pick_admin_kb() -> ReplyKeyboardMarkup:
    """Telefon kontaktlaridan foydalanuvchi tanlash tugmasi (ID qidirish shart emas)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="👤 Kontaktlardan tanlash",
                request_users=KeyboardButtonRequestUsers(
                    request_id=1, user_is_bot=False, max_quantity=1, request_name=True, request_username=True,
                ),
            )],
            [KeyboardButton(text=t("btn_cancel", "uz"))],
        ],
        resize_keyboard=True,
    )


def admin_promo_kb(has_promo: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Yangi aksiya", callback_data="pr:new")
    if has_promo:
        kb.button(text="📢 Mijozlarga e'lon qilish", callback_data="pr:announce")
        kb.button(text="👁 Mijozlar qanday ko'radi", callback_data="pr:preview")
        kb.button(text="⛔️ Aksiyani to'xtatish", callback_data="pr:stop")
    kb.button(text="⬅️ Admin panel", callback_data="adm:menu")
    kb.adjust(1)
    return kb.as_markup()


def promo_scope_kb(categories) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🌍 Barcha mahsulotlar", callback_data="psc:all")
    for c in categories:
        kb.button(text=c["name"], callback_data=f"psc:{c['id']}")
    kb.adjust(1, 2)
    return kb.as_markup()


def promo_period_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📅 Faqat 11.11 kuni (00:00 – 23:59)", callback_data="pp:day")
    kb.button(text="⚡️ Hozirdan 11.11 oxirigacha", callback_data="pp:now")
    kb.button(text="✍️ Boshqa muddat", callback_data="pp:custom")
    kb.adjust(1)
    return kb.as_markup()


def promo_percent_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="11"), KeyboardButton(text="15"), KeyboardButton(text="20")],
            [KeyboardButton(text="25"), KeyboardButton(text="30"), KeyboardButton(text="50")],
            [KeyboardButton(text=t("btn_cancel", "uz"))],
        ],
        resize_keyboard=True,
    )
