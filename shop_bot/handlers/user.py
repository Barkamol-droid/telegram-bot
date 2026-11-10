"""Mijozlar uchun handlerlar: katalog, aksiya, savat, buyurtma berish (4 tilda)."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import db
import keyboards as kb
from config import SHOP_NAME, SHOP_PHONE, _env_text, all_admin_ids, fmt_phone, is_admin
from db import product_sizes
from handlers.payment import offer_payment
from i18n import all_texts, loc, t
from states import OrderForm

router = Router()
log = logging.getLogger(__name__)


async def show(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None):
    """Inline xabarni yangilaydi. Rasmli xabarni matnga o'zgartirib bo'lmagani uchun
    kerak bo'lsa eski xabarni o'chirib, yangisini yuboradi."""
    msg = callback.message
    if msg.photo:
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
    text = kb.product_text(product, lang, promo, sizes)
    markup = kb.product_kb(product["id"], product["category_id"], lang, sizes=sizes)
    if product["photo_id"]:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer_photo(product["photo_id"], caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await show(callback, text, markup)


async def _update_card(callback: CallbackQuery, lang: str, product_id: int, qty: int, size: str):
    if qty < 1 or qty > 99:
        await callback.answer(t("qty_range", lang))
        return
    product = await db.get_product(product_id)
    if not product:
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    sizes = product_sizes(product)
    if size and size not in sizes:
        size = ""
    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.product_kb(product_id, product["category_id"], lang, qty, sizes, size)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(t("size_selected", lang, size=size) if size else None)


@router.callback_query(F.data.startswith("qty:"))
async def cb_qty(callback: CallbackQuery, lang: str):
    parts = callback.data.split(":")
    size = parts[3] if len(parts) > 3 else ""
    await _update_card(callback, lang, int(parts[1]), int(parts[2]), size)


@router.callback_query(F.data.startswith("sz:"))
async def cb_size(callback: CallbackQuery, lang: str):
    _, product_id, size, qty = callback.data.split(":")
    await _update_card(callback, lang, int(product_id), int(qty), size)


@router.callback_query(F.data.startswith("add:"))
async def cb_add_to_cart(callback: CallbackQuery, lang: str):
    parts = callback.data.split(":")
    product_id, qty = int(parts[1]), int(parts[2])
    size = parts[3] if len(parts) > 3 else ""
    product = await db.get_product(product_id)
    if not product:
        await callback.answer(t("not_found_product", lang), show_alert=True)
        return
    sizes = product_sizes(product)
    if sizes and size not in sizes:
        await callback.answer(t("choose_size_first", lang), show_alert=True)
        return
    if not sizes:
        size = ""
    await db.cart_add(callback.from_user.id, product["id"], qty, size)
    await callback.answer(
        t("added", lang, name=loc(product, "name", lang), size=kb.size_label(size, lang), qty=qty),
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
    items = await db.cart_get(user_id)
    if not items:
        return t("cart_empty", lang), None
    return kb.cart_text(items, lang), kb.cart_kb(items, lang)


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
    parts = callback.data.split(":")
    size = parts[2] if len(parts) > 2 else ""
    await db.cart_remove(callback.from_user.id, int(parts[1]), size)
    text, markup = await _cart_view(callback.from_user.id, lang)
    await show(callback, text, markup)


@router.callback_query(F.data == "cart_clear")
async def cb_cart_clear(callback: CallbackQuery, lang: str):
    await db.cart_clear(callback.from_user.id)
    await show(callback, t("cart_cleared", lang))


# ---------------- Buyurtma berish ----------------
@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, state: FSMContext, lang: str):
    if not await db.cart_get(callback.from_user.id):
        await callback.answer(t("cart_empty", lang), show_alert=True)
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
    await _ask_confirm(message, state, lang, message.from_user.id)


async def _ask_confirm(message: Message, state: FSMContext, lang: str, user_id: int, notice: str = ""):
    data = await state.get_data()
    items = await db.cart_get(user_id)
    if not items:
        await state.clear()
        await message.answer(t("cart_empty", lang), reply_markup=kb.main_menu(lang, is_admin(user_id)))
        return
    total = sum(i["subtotal"] for i in items)
    await state.update_data(expected_total=total)
    await state.set_state(OrderForm.confirm)
    address = escape(data["address"]) if data.get("address") else t("location_sent", lang)
    text = (
        (f"{notice}\n\n" if notice else "")
        + kb.cart_text(items, lang)
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

    # Tasdiqlash oynasi ochilgandan beri narx o'zgargan bo'lsa (masalan, aksiya tugagan) — qayta so'raymiz
    items = await db.cart_get(user_id)
    if items and sum(i["subtotal"] for i in items) != data.get("expected_total"):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        await callback.answer()
        await _ask_confirm(callback.message, state, lang, user_id, notice=t("prices_changed", lang))
        return

    await state.clear()
    order_id = await db.create_order(
        user_id, data["full_name"], data["phone"], data.get("address"),
        data.get("latitude"), data.get("longitude"), data.get("comment"), lang,
    )
    if not order_id:
        await show(callback, t("cart_empty", lang))
        return

    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    await show(
        callback,
        f"{t('order_accepted', lang)}\n\n{kb.order_text(order, items, lang)}\n\n{t('order_thanks', lang)}",
    )
    await offer_payment(callback.message, order_id, lang)

    # Adminlarga xabar (o'zbek tilida)
    admin_text = "🔔 <b>Yangi buyurtma!</b>\n\n" + kb.order_text(order, items, "uz", for_admin=True)
    for admin_id in all_admin_ids():
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=kb.admin_order_kb(order_id))
            if order["latitude"] is not None:
                await bot.send_location(admin_id, order["latitude"], order["longitude"])
        except Exception as e:  # admin botni bloklagan bo'lishi mumkin
            log.warning("Adminga (%s) xabar yuborilmadi: %s", admin_id, e)


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
