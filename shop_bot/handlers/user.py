"""Mijozlar uchun handlerlar: katalog, aksiya, savat, buyurtma berish (4 tilda)."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InputMediaPhoto, Message

import colors as color_mod
import db
import keyboards as kb
from config import SHOP_NAME, SHOP_PHONE, _env_text, all_admin_ids, fmt_phone, is_admin
from db import product_sizes
from services import finish_order
from i18n import all_texts, loc, t
from states import OrderForm

router = Router()
log = logging.getLogger(__name__)


async def show(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None):
    """Inline xabarni yangilaydi. Rasmli xabarni matnga o'zgartirib bo'lmagani uchun
    kerak bo'lsa eski xabarni o'chirib, yangisini yuboradi."""
    msg = callback.message
    if msg.photo or msg.video:
        try:
            await msg.delete()
        except TelegramBadRequest:
            pass
        await msg.answer(text, reply_markup=markup)
    else:
        try:
            await msg.edit_text(text, reply_markup=markup)
        except TelegramBadRequest:
            pass
    await callback.answer()


async def promo_with_banner(lang: str) -> tuple[dict | None, str]:
    promo = await db.get_promo()
    category = await db.get_category(promo["category_id"]) if promo and promo.get("category_id") else None
    return promo, kb.promo_banner(promo, lang, category)


async def categories_view(lang: str) -> tuple[str, InlineKeyboardMarkup | None]:
    categories = await db.get_categories()
    if not categories:
        return t("no_products", lang), None
    _, banner = await promo_with_banner(lang)
    text = t("choose_category", lang)
    if banner:
        text = f"{banner}\n\n{text}"
    return text, kb.categories_kb(categories, lang)


# ---------------- Katalog ----------------
@router.message(F.text.in_(all_texts("btn_catalog")))
async def catalog(message: Message, lang: str):
    shop_kb = kb.open_shop_kb(lang)
    if shop_kb:
        await message.answer(t("open_shop_hint", lang), reply_markup=shop_kb)
    text, markup = await categories_view(lang)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "cats")
async def cb_categories(callback: CallbackQuery, lang: str):
    text, markup = await categories_view(lang)
    await show(callback, text, markup)


@router.callback_query(F.data == "shop")
async def cb_shop(callback: CallbackQuery, lang: str):
    """E'lon/banner ostidagi «Xarid qilish» tugmasi — e'lonni o'chirmasdan katalogni yangi xabarda ochadi."""
    text, markup = await categories_view(lang)
    await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery, lang: str):
    category_id = int(callback.data.split(":")[1])
    category = await db.get_category(category_id)
    if not category:
        await callback.answer(t("not_found_category", lang), show_alert=True)
        return
    promo = await db.get_promo()
    products = await db.get_products(category_id)
    title = f"<b>{escape(loc(category, 'name', lang))}</b>\n\n"
    if not products:
        await show(callback, title + t("category_empty", lang), kb.products_kb([], lang, promo))
        return
    await show(callback, title + t("choose_product", lang), kb.products_kb(products, lang, promo))


@router.callback_query(F.data.startswith("prod:"))
async def cb_product(callback: CallbackQuery, lang: str):
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    promo = await db.get_promo()
    sizes = product_sizes(product)
    colors = color_mod.product_colors(product)
    text = kb.product_text(product, lang, promo, sizes, colors)
    # Rasm bo'lsa — rasm kartasi (bir nechta bo'lsa ⬅️ ➡️ galereya, video bo'lsa «Videoni ko'rish» tugmasi);
    # faqat video bo'lsa — video kartasi
    photos = db.product_photos(product)
    has_video_button = bool(product.get("video_id") and photos)
    markup = kb.product_kb(product["id"], product["category_id"], lang, sizes=sizes, has_video=has_video_button,
                           colors=colors, gallery=(0, len(photos)) if photos else None,
                           sold_out=db.product_stock(product) == 0)
    if photos or product.get("video_id"):
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        if photos:
            await callback.message.answer_photo(photos[0], caption=text, reply_markup=markup)
        else:
            await callback.message.answer_video(product["video_id"], caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await show(callback, text, markup)


@router.callback_query(F.data.startswith("pg:"))
async def cb_gallery(callback: CallbackQuery, lang: str):
    """Galereya: ⬅️ ➡️ bosilganda rasm almashadi, tanlangan rang/o'lcham/miqdor saqlanadi."""
    _, product_id, index = callback.data.split(":")
    product = await db.get_product(int(product_id))
    photos = db.product_photos(product) if product else []
    if not photos:
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    index = int(index) % len(photos)
    rows = [list(row) for row in (callback.message.reply_markup.inline_keyboard if callback.message.reply_markup else [])]
    new_row = kb.gallery_row(product["id"], index, len(photos))
    for i, row in enumerate(rows):
        if any((b.callback_data or "").startswith("pg:") for b in row):
            rows[i] = new_row
            break
    else:
        rows.insert(0, new_row)
    promo = await db.get_promo()
    caption = kb.product_text(product, lang, promo, product_sizes(product), color_mod.product_colors(product))
    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(media=photos[index], caption=caption),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("pvid:"))
async def cb_product_video(callback: CallbackQuery, lang: str):
    product = await db.get_product(int(callback.data.split(":")[1]))
    if not product or not product.get("video_id"):
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    await callback.message.answer_video(product["video_id"], caption=f"🎬 {escape(loc(product, 'name', lang))}")
    await callback.answer()


def _color_by_index(colors: list[str], ci: str) -> str:
    """Rang raqamidan rangni olish (noto'g'ri bo'lsa — bo'sh)."""
    return colors[int(ci)] if ci.isdigit() and int(ci) < len(colors) else ""


async def _update_card(callback: CallbackQuery, lang: str, product_id: int, qty: int, size: str, ci: str = "",
                       notice: str | None = None):
    if qty < 1 or qty > 99:
        await callback.answer(t("qty_range", lang))
        return
    product = await db.get_product(product_id)
    if not product:
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    stock = db.product_stock(product)
    if stock is not None and qty > max(stock, 1):
        in_cart = await db.cart_product_qty(callback.from_user.id, product_id)
        await callback.answer(t("stock_limit", lang, n=stock, c=in_cart), show_alert=True)
        return
    sizes = product_sizes(product)
    colors = color_mod.product_colors(product)
    if size and size not in sizes:
        size = ""
    if not _color_by_index(colors, ci):
        ci = ""
    photos = db.product_photos(product)
    has_video_button = bool(product.get("video_id") and photos)
    gallery = kb.gallery_state(callback.message.reply_markup) if len(photos) > 1 else None
    if gallery and gallery[1] != len(photos):
        gallery = (0, len(photos))
    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.product_kb(product_id, product["category_id"], lang, qty, sizes, size, has_video_button,
                                       colors, ci, gallery, sold_out=stock == 0)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(notice)


@router.callback_query(F.data.startswith("qty:"))
async def cb_qty(callback: CallbackQuery, lang: str):
    parts = callback.data.split(":") + ["", ""]
    await _update_card(callback, lang, int(parts[1]), int(parts[2]), parts[3], parts[4])


@router.callback_query(F.data.startswith("sz:"))
async def cb_size(callback: CallbackQuery, lang: str):
    parts = callback.data.split(":") + [""]
    _, product_id, size, qty, ci = parts[:5]
    await _update_card(callback, lang, int(product_id), int(qty), size, ci, t("size_selected", lang, size=size))


@router.callback_query(F.data.startswith("cl:"))
async def cb_color(callback: CallbackQuery, lang: str):
    parts = callback.data.split(":") + [""]
    _, product_id, ci, qty, size = parts[:5]
    product = await db.get_product(int(product_id))
    color = _color_by_index(color_mod.product_colors(product), ci) if product else ""
    notice = t("color_selected", lang, color=color_mod.name(color, lang)) if color else None
    await _update_card(callback, lang, int(product_id), int(qty), size, ci, notice)


@router.callback_query(F.data.startswith("add:"))
async def cb_add_to_cart(callback: CallbackQuery, lang: str):
    parts = callback.data.split(":") + ["", ""]
    product_id, qty, size, ci = int(parts[1]), int(parts[2]), parts[3], parts[4]
    product = await db.get_product(product_id)
    if not product:
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    colors = color_mod.product_colors(product)
    color = _color_by_index(colors, ci)
    if colors and not color:
        await callback.answer(t("choose_color_first", lang), show_alert=True)
        return
    sizes = product_sizes(product)
    if sizes and size not in sizes:
        await callback.answer(t("choose_size_first", lang), show_alert=True)
        return
    if not sizes:
        size = ""
    stock = db.product_stock(product)
    if stock is not None:
        in_cart = await db.cart_product_qty(callback.from_user.id, product["id"])
        if stock == 0:
            await callback.answer(t("out_of_stock", lang), show_alert=True)
            return
        if in_cart + qty > stock:
            await callback.answer(t("stock_limit", lang, n=stock, c=in_cart), show_alert=True)
            return
    await db.cart_add(callback.from_user.id, product["id"], qty, size, color)
    await callback.answer(
        t("added", lang, name=loc(product, "name", lang), size=kb.variant_label(size, color, lang), qty=qty),
        show_alert=True,
    )


# ---------------- Aksiya ----------------
@router.message(F.text.in_(all_texts("btn_promo")))
async def promo_info(message: Message, lang: str):
    _, banner = await promo_with_banner(lang)
    if banner:
        await message.answer(banner + f"\n\n{t('promo_footer', lang)}", reply_markup=kb.shop_now_kb(lang))
    else:
        await message.answer(t("no_promo", lang), reply_markup=kb.channel_kb(lang))


# ---------------- Savat ----------------
async def _cart_view(user_id: int, lang: str):
    preview = await db.order_preview(user_id)
    items = preview["items"]
    if not items:
        return t("cart_empty", lang), None
    text = kb.cart_text(items, lang)
    if preview["stock_issues"]:
        text += "\n\n" + kb.stock_issues_text(preview["stock_issues"], lang)
    return text, kb.cart_kb(items, lang)


@router.message(F.text.in_(all_texts("btn_cart")))
async def cart(message: Message, lang: str):
    text, markup = await _cart_view(message.from_user.id, lang)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "cart")
async def cb_cart(callback: CallbackQuery, lang: str):
    text, markup = await _cart_view(callback.from_user.id, lang)
    await show(callback, text, markup)


@router.callback_query(F.data.startswith("cart_del:"))
async def cb_cart_del(callback: CallbackQuery, lang: str):
    """cart_del:<n> — savatdagi n-chi qatorni o'chirish (ro'yxat tartibi bo'yicha)."""
    index = callback.data.split(":")[1]
    items = await db.cart_get(callback.from_user.id)
    if index.isdigit() and int(index) < len(items):
        item = items[int(index)]
        await db.cart_remove(callback.from_user.id, item["product_id"], item["size"], item["color"])
    text, markup = await _cart_view(callback.from_user.id, lang)
    await show(callback, text, markup)


@router.callback_query(F.data == "cart_clear")
async def cb_cart_clear(callback: CallbackQuery, lang: str):
    await db.cart_clear(callback.from_user.id)
    await show(callback, t("cart_cleared", lang))


# ---------------- Buyurtma berish ----------------
@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, state: FSMContext, lang: str):
    preview = await db.order_preview(callback.from_user.id)
    if not preview["items"]:
        await callback.answer(t("cart_empty", lang), show_alert=True)
        return
    if preview["stock_issues"]:
        await callback.answer()
        await callback.message.answer(kb.stock_issues_text(preview["stock_issues"], lang))
        return
    await state.set_state(OrderForm.name)
    await callback.message.answer(t("ask_name", lang), reply_markup=kb.cancel_kb(lang))
    await callback.answer()


@router.message(OrderForm.name, F.text)
async def order_name(message: Message, state: FSMContext, lang: str):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 64:
        await message.answer(t("bad_name", lang))
        return
    await state.update_data(full_name=name)
    await state.set_state(OrderForm.phone)
    await message.answer(t("ask_phone", lang), reply_markup=kb.phone_kb(lang))


@router.message(OrderForm.phone, F.contact)
async def order_phone_contact(message: Message, state: FSMContext, lang: str):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer(t("own_phone", lang))
        return
    await _set_phone(message, state, lang, message.contact.phone_number)


@router.message(OrderForm.phone, F.text)
async def order_phone_text(message: Message, state: FSMContext, lang: str):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if not 9 <= len(digits) <= 15:
        await message.answer(t("bad_phone", lang))
        return
    await _set_phone(message, state, lang, message.text.strip())


async def _set_phone(message: Message, state: FSMContext, lang: str, phone: str):
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.address)
    await message.answer(t("ask_address", lang), reply_markup=kb.location_kb(lang))


@router.message(OrderForm.address, F.location)
async def order_address_location(message: Message, state: FSMContext, lang: str):
    await state.update_data(address=None, latitude=message.location.latitude, longitude=message.location.longitude)
    await _ask_comment(message, state, lang)


@router.message(OrderForm.address, F.text)
async def order_address_text(message: Message, state: FSMContext, lang: str):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer(t("address_short", lang))
        return
    await state.update_data(address=address, latitude=None, longitude=None)
    await _ask_comment(message, state, lang)


async def _ask_comment(message: Message, state: FSMContext, lang: str):
    await state.set_state(OrderForm.comment)
    await message.answer(t("ask_comment", lang, skip=t("btn_skip", lang)), reply_markup=kb.skip_cancel_kb(lang))


@router.message(OrderForm.comment, F.text)
async def order_comment(message: Message, state: FSMContext, lang: str):
    comment = None if message.text in all_texts("btn_skip") else message.text.strip()[:500]
    await state.update_data(comment=comment)
    await message.answer(t("data_received", lang), reply_markup=kb.main_menu(lang, is_admin(message.from_user.id)))
    # Brilliantlar bo'lsa — ishlatishni taklif qilamiz
    preview = await db.order_preview(message.from_user.id, use_bonus=True)
    if preview["bonus_used"] > 0:
        await state.set_state(OrderForm.bonus)
        await message.answer(
            t("ask_use_bonus", lang, n=preview["balance"], value=kb.bonus_value(preview["balance"], lang),
              use=preview["bonus_used"], disc=kb.fmt_price(preview["bonus_discount"], lang)),
            reply_markup=kb.use_bonus_kb(lang),
        )
        return
    await state.update_data(use_bonus=False)
    await _ask_confirm(message, state, lang, message.from_user.id)


@router.callback_query(OrderForm.bonus, F.data.startswith("bonus_use:"))
async def cb_use_bonus(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.update_data(use_bonus=callback.data.endswith(":1"))
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.answer()
    await _ask_confirm(callback.message, state, lang, callback.from_user.id)


async def _ask_confirm(message: Message, state: FSMContext, lang: str, user_id: int, notice: str = ""):
    data = await state.get_data()
    preview = await db.order_preview(user_id, use_bonus=data.get("use_bonus", False))
    if not preview["items"]:
        await state.clear()
        await message.answer(t("cart_empty", lang), reply_markup=kb.main_menu(lang, is_admin(user_id)))
        return
    await state.update_data(expected_total=preview["total"])
    await state.set_state(OrderForm.confirm)
    address = escape(data["address"]) if data.get("address") else t("location_sent", lang)
    text = (
        (f"{notice}\n\n" if notice else "")
        + kb.checkout_summary(preview, lang)
        + f"\n\n👤 {escape(data['full_name'])}\n📞 {escape(data['phone'])}\n📍 {address}"
        + (f"\n💬 {escape(data['comment'])}" if data.get("comment") else "")
        + f"\n\n{t('confirm_q', lang)}"
    )
    await message.answer(text, reply_markup=kb.confirm_kb(lang))


@router.callback_query(OrderForm.confirm, F.data == "order_cancel")
async def cb_order_cancel(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await show(callback, t("order_cancelled", lang))


@router.callback_query(OrderForm.confirm, F.data == "order_confirm")
async def cb_order_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, lang: str):
    data = await state.get_data()
    user_id = callback.from_user.id

    # Tasdiqlash oynasi ochilgandan beri summa o'zgargan bo'lsa (aksiya tugagan, brilliant sarflangan) — qayta so'raymiz
    preview = await db.order_preview(user_id, use_bonus=data.get("use_bonus", False))
    if preview["items"] and preview["total"] != data.get("expected_total"):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        await callback.answer()
        await _ask_confirm(callback.message, state, lang, user_id, notice=t("prices_changed", lang))
        return

    await state.clear()
    try:
        order_id = await db.create_order(
            user_id, data["full_name"], data["phone"], data.get("address"),
            data.get("latitude"), data.get("longitude"), data.get("comment"), lang,
            use_bonus=data.get("use_bonus", False),
        )
    except db.OutOfStock as e:
        await show(callback, kb.stock_issues_text(e.items, lang))
        return
    if not order_id:
        await show(callback, t("cart_empty", lang))
        return

    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    await show(
        callback,
        f"{t('order_accepted', lang)}\n\n{kb.order_text(order, items, lang)}\n\n{t('order_thanks', lang)}",
    )
    await finish_order(bot, order_id, lang, send_summary=False)


@router.callback_query(F.data.in_({"order_confirm", "order_cancel"}))
async def cb_order_expired(callback: CallbackQuery, lang: str):
    await callback.answer(t("order_expired", lang), show_alert=True)


# ---------------- Buyurtmalarim / Ma'lumot ----------------
@router.message(F.text.in_(all_texts("btn_orders")))
async def my_orders(message: Message, lang: str):
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer(t("no_orders", lang))
        return
    lines = [t("my_orders", lang) + "\n"]
    for o in orders:
        lines.append(
            f"#{o['id']} • {o['created_at']} • {kb.fmt_price(o['total'], lang)}\n"
            f"    {kb.status_label(o['status'], lang)} • {kb.payment_label(o, lang)}"
        )
    await message.answer("\n".join(lines), reply_markup=kb.unpaid_orders_kb(orders, lang))


@router.message(F.text.in_(all_texts("btn_about")))
async def about(message: Message, lang: str):
    await message.answer(_env_text("ABOUT_TEXT", lang) or t("about", lang, shop=escape(SHOP_NAME)))


@router.message(F.text.in_(all_texts("btn_channel")))
async def channel(message: Message, lang: str):
    markup = kb.channel_kb(lang)
    if markup:
        await message.answer(t("channel_text", lang), reply_markup=markup)


@router.message(F.text.in_(all_texts("btn_contact")))
async def contact(message: Message, lang: str):
    await message.answer(_env_text("CONTACT_TEXT", lang) or t("contact_default", lang, phone=fmt_phone(SHOP_PHONE)))


@router.message()
async def fallback(message: Message, lang: str):
    await message.answer(t("use_menu", lang), reply_markup=kb.main_menu(lang, is_admin(message.from_user.id)))
