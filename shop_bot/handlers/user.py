"""Mijozlar uchun handlerlar: katalog, savat, buyurtma berish."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

import db
import keyboards as kb
from config import ABOUT_TEXT, ADMIN_IDS, CONTACT_TEXT, fmt_price, is_admin
from db import product_sizes
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


# ---------------- Katalog ----------------
@router.message(F.text == kb.BTN_CATALOG)
async def catalog(message: Message):
    categories = await db.get_categories()
    if not categories:
        await message.answer("Hozircha mahsulotlar mavjud emas. Keyinroq urinib ko'ring 🙂")
        return
    await message.answer("📂 Kategoriyani tanlang:", reply_markup=kb.categories_kb(categories))


@router.callback_query(F.data == "cats")
async def cb_categories(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await show(callback, "Hozircha mahsulotlar mavjud emas.")
        return
    await show(callback, "📂 Kategoriyani tanlang:", kb.categories_kb(categories))


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery):
    category_id = int(callback.data.split(":")[1])
    category = await db.get_category(category_id)
    if not category:
        await callback.answer("Kategoriya topilmadi", show_alert=True)
        return
    products = await db.get_products(category_id)
    if not products:
        await show(callback, f"<b>{escape(category['name'])}</b>\n\nBu kategoriyada hozircha mahsulot yo'q.",
                   kb.products_kb([]))
        return
    await show(callback, f"<b>{escape(category['name'])}</b>\n\nMahsulotni tanlang:", kb.products_kb(products))


@router.callback_query(F.data.startswith("prod:"))
async def cb_product(callback: CallbackQuery):
    product_id = int(callback.data.split(":")[1])
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    sizes = product_sizes(product)
    text = kb.product_text(product, sizes)
    markup = kb.product_kb(product["id"], product["category_id"], sizes=sizes)
    if product["photo_id"]:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer_photo(product["photo_id"], caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await show(callback, text, markup)


async def _update_card(callback: CallbackQuery, product_id: int, qty: int, size: str):
    if qty < 1 or qty > 99:
        await callback.answer("Miqdor 1 dan 99 gacha bo'lishi kerak")
        return
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    sizes = product_sizes(product)
    if size and size not in sizes:
        size = ""
    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.product_kb(product_id, product["category_id"], qty, sizes, size)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(f"O'lcham: {size}" if size else None)


@router.callback_query(F.data.startswith("qty:"))
async def cb_qty(callback: CallbackQuery):
    parts = callback.data.split(":")
    size = parts[3] if len(parts) > 3 else ""
    await _update_card(callback, int(parts[1]), int(parts[2]), size)


@router.callback_query(F.data.startswith("sz:"))
async def cb_size(callback: CallbackQuery):
    _, product_id, size, qty = callback.data.split(":")
    await _update_card(callback, int(product_id), int(qty), size)


@router.callback_query(F.data.startswith("add:"))
async def cb_add_to_cart(callback: CallbackQuery):
    parts = callback.data.split(":")
    product_id, qty = int(parts[1]), int(parts[2])
    size = parts[3] if len(parts) > 3 else ""
    product = await db.get_product(product_id)
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    sizes = product_sizes(product)
    if sizes and size not in sizes:
        await callback.answer("📏 Avval o'lchamni tanlang!", show_alert=True)
        return
    if not sizes:
        size = ""
    await db.cart_add(callback.from_user.id, product["id"], qty, size)
    size_info = f", o'lcham {size}" if size else ""
    await callback.answer(f"✅ {product['name']} ({qty} dona{size_info}) savatga qo'shildi!", show_alert=True)


# ---------------- Savat ----------------
async def _cart_view(user_id: int):
    items = await db.cart_get(user_id)
    if not items:
        return "🛒 Savatingiz bo'sh.", None
    return kb.cart_text(items), kb.cart_kb(items)


@router.message(F.text == kb.BTN_CART)
async def cart(message: Message):
    text, markup = await _cart_view(message.from_user.id)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data == "cart")
async def cb_cart(callback: CallbackQuery):
    text, markup = await _cart_view(callback.from_user.id)
    await show(callback, text, markup)


@router.callback_query(F.data.startswith("cart_del:"))
async def cb_cart_del(callback: CallbackQuery):
    parts = callback.data.split(":")
    size = parts[2] if len(parts) > 2 else ""
    await db.cart_remove(callback.from_user.id, int(parts[1]), size)
    text, markup = await _cart_view(callback.from_user.id)
    await show(callback, text, markup)


@router.callback_query(F.data == "cart_clear")
async def cb_cart_clear(callback: CallbackQuery):
    await db.cart_clear(callback.from_user.id)
    await show(callback, "🛒 Savatingiz tozalandi.")


# ---------------- Buyurtma berish ----------------
@router.callback_query(F.data == "checkout")
async def cb_checkout(callback: CallbackQuery, state: FSMContext):
    if not await db.cart_get(callback.from_user.id):
        await callback.answer("Savatingiz bo'sh", show_alert=True)
        return
    await state.set_state(OrderForm.name)
    await callback.message.answer("👤 Ismingizni kiriting:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(OrderForm.name, F.text)
async def order_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2 or len(name) > 64:
        await message.answer("Iltimos, ismingizni to'g'ri kiriting (2-64 belgi).")
        return
    await state.update_data(full_name=name)
    await state.set_state(OrderForm.phone)
    await message.answer(
        "📞 Telefon raqamingizni yuboring (tugmani bosing yoki +998901234567 ko'rinishida yozing):",
        reply_markup=kb.phone_kb(),
    )


@router.message(OrderForm.phone, F.contact)
async def order_phone_contact(message: Message, state: FSMContext):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Iltimos, o'zingizning raqamingizni yuboring.")
        return
    await _set_phone(message, state, message.contact.phone_number)


@router.message(OrderForm.phone, F.text)
async def order_phone_text(message: Message, state: FSMContext):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if not 9 <= len(digits) <= 15:
        await message.answer("Telefon raqam noto'g'ri. Masalan: +998901234567")
        return
    await _set_phone(message, state, message.text.strip())


async def _set_phone(message: Message, state: FSMContext, phone: str):
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.address)
    await message.answer(
        "📍 Yetkazib berish manzilini yozing yoki joylashuvni yuboring:",
        reply_markup=kb.location_kb(),
    )


@router.message(OrderForm.address, F.location)
async def order_address_location(message: Message, state: FSMContext):
    await state.update_data(
        address=None, latitude=message.location.latitude, longitude=message.location.longitude
    )
    await _ask_comment(message, state)


@router.message(OrderForm.address, F.text)
async def order_address_text(message: Message, state: FSMContext):
    address = message.text.strip()
    if len(address) < 5:
        await message.answer("Manzilni batafsilroq yozing.")
        return
    await state.update_data(address=address, latitude=None, longitude=None)
    await _ask_comment(message, state)


async def _ask_comment(message: Message, state: FSMContext):
    await state.set_state(OrderForm.comment)
    await message.answer(
        "💬 Qo'shimcha izoh qoldiring (masalan: sovg'a uchun qadoqlash, otkritkaga yozuv, "
        "qulay vaqt) yoki «O'tkazib yuborish» tugmasini bosing:",
        reply_markup=kb.skip_cancel_kb(),
    )


@router.message(OrderForm.comment, F.text)
async def order_comment(message: Message, state: FSMContext):
    comment = None if message.text == kb.BTN_SKIP else message.text.strip()[:500]
    await state.update_data(comment=comment)
    await _ask_confirm(message, state)


async def _ask_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    items = await db.cart_get(message.from_user.id)
    if not items:
        await state.clear()
        await message.answer("Savatingiz bo'sh.", reply_markup=kb.main_menu(is_admin(message.from_user.id)))
        return
    await state.set_state(OrderForm.confirm)
    address = escape(data["address"]) if data.get("address") else "Joylashuv yuborilgan"
    text = (
        kb.cart_text(items)
        + f"\n\n👤 {escape(data['full_name'])}\n📞 {escape(data['phone'])}\n📍 {address}"
        + (f"\n💬 {escape(data['comment'])}" if data.get("comment") else "")
        + "\n\nBuyurtmani tasdiqlaysizmi?"
    )
    await message.answer("Ma'lumotlar qabul qilindi ✅", reply_markup=kb.main_menu(is_admin(message.from_user.id)))
    await message.answer(text, reply_markup=kb.confirm_kb())


@router.callback_query(OrderForm.confirm, F.data == "order_cancel")
async def cb_order_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show(callback, "Buyurtma bekor qilindi. Mahsulotlar savatingizda qoldi.")


@router.callback_query(OrderForm.confirm, F.data == "order_confirm")
async def cb_order_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    order_id = await db.create_order(
        callback.from_user.id,
        data["full_name"],
        data["phone"],
        data.get("address"),
        data.get("latitude"),
        data.get("longitude"),
        data.get("comment"),
    )
    if not order_id:
        await show(callback, "Savatingiz bo'sh.")
        return

    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    await show(
        callback,
        f"✅ Buyurtmangiz qabul qilindi!\n\n{kb.order_text(order, items)}\n\n"
        "Tez orada operatorimiz siz bilan bog'lanadi. Xaridingiz uchun rahmat! 💎",
    )

    # Adminlarga xabar
    admin_text = "🔔 <b>Yangi buyurtma!</b>\n\n" + kb.order_text(order, items, for_admin=True)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=kb.admin_order_kb(order_id))
            if order["latitude"] is not None:
                await bot.send_location(admin_id, order["latitude"], order["longitude"])
        except Exception as e:  # admin botni bloklagan bo'lishi mumkin
            log.warning("Adminga (%s) xabar yuborilmadi: %s", admin_id, e)


@router.callback_query(F.data.in_({"order_confirm", "order_cancel"}))
async def cb_order_expired(callback: CallbackQuery):
    await callback.answer("Bu buyurtma eskirgan. Iltimos, savatdan qaytadan rasmiylashtiring.", show_alert=True)


# ---------------- Buyurtmalarim / Aloqa ----------------
@router.message(F.text == kb.BTN_ORDERS)
async def my_orders(message: Message):
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("Sizda hali buyurtmalar yo'q.")
        return
    lines = ["📦 <b>Oxirgi buyurtmalaringiz:</b>\n"]
    for o in orders:
        lines.append(
            f"#{o['id']} • {o['created_at']} • {fmt_price(o['total'])}\n"
            f"    {kb.STATUS_LABELS.get(o['status'], o['status'])}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text == kb.BTN_ABOUT)
async def about(message: Message):
    await message.answer(ABOUT_TEXT)


@router.message(F.text == kb.BTN_CHANNEL)
async def channel(message: Message):
    markup = kb.channel_kb()
    if markup:
        await message.answer("📢 Yangi kolleksiyalar va aksiyalardan xabardor bo'lish uchun kanalimizga obuna bo'ling!",
                             reply_markup=markup)


@router.message(F.text == kb.BTN_CONTACT)
async def contact(message: Message):
    await message.answer(CONTACT_TEXT)


@router.message()
async def fallback(message: Message):
    await message.answer(
        "Iltimos, quyidagi menyudan foydalaning 👇",
        reply_markup=kb.main_menu(is_admin(message.from_user.id)),
    )
