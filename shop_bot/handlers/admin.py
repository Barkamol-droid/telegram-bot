"""Admin panel: kategoriya/mahsulot boshqaruvi, buyurtmalar, statistika, xabar yuborish."""
import asyncio
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

import db
import keyboards as kb
from config import fmt_price, is_admin
from states import AddCategory, AddProduct, Broadcast

log = logging.getLogger(__name__)


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        return event.from_user is not None and is_admin(event.from_user.id)


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def edit(callback: CallbackQuery, text: str, markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


# ---------------- Menyu ----------------
@router.message(Command("admin"))
@router.message(F.text == kb.BTN_ADMIN)
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit(callback, "⚙️ <b>Admin panel</b>", kb.admin_menu_kb())


# ---------------- Kategoriya qo'shish ----------------
@router.callback_query(F.data == "adm:add_cat")
async def cb_add_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategory.name)
    await callback.message.answer("Yangi kategoriya nomini kiriting:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(AddCategory.name, F.text)
async def add_category_name(message: Message, state: FSMContext):
    name = message.text.strip()[:64]
    await db.add_category(name)
    await state.clear()
    await message.answer(f"✅ «{escape(name)}» kategoriyasi qo'shildi.", reply_markup=kb.main_menu(True))
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu_kb())


# ---------------- Kategoriyani o'chirish ----------------
@router.callback_query(F.data == "adm:del_cat")
async def cb_del_category(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Kategoriyalar yo'q", show_alert=True)
        return
    await edit(
        callback,
        "Qaysi kategoriyani o'chirasiz?\n⚠️ Undagi barcha mahsulotlar ham o'chiriladi.",
        kb.categories_kb(categories, prefix="dc"),
    )


@router.callback_query(F.data.startswith("dc:"))
async def cb_del_category_do(callback: CallbackQuery):
    category_id = int(callback.data.split(":")[1])
    category = await db.get_category(category_id)
    if category:
        await db.delete_category(category_id)
        await callback.answer(f"🗑 «{category['name']}» o'chirildi", show_alert=True)
    await edit(callback, "⚙️ <b>Admin panel</b>", kb.admin_menu_kb())


# ---------------- Mahsulot qo'shish ----------------
@router.callback_query(F.data == "adm:add_prod")
async def cb_add_product(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Avval kategoriya qo'shing!", show_alert=True)
        return
    await edit(callback, "Mahsulot qaysi kategoriyaga qo'shilsin?", kb.categories_kb(categories, prefix="apc"))


@router.callback_query(F.data.startswith("apc:"))
async def cb_add_product_category(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data.split(":")[1]))
    await state.set_state(AddProduct.name)
    await callback.message.answer("Mahsulot nomini kiriting:", reply_markup=kb.cancel_kb())
    await callback.answer()


@router.message(AddProduct.name, F.text)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip()[:100])
    await state.set_state(AddProduct.description)
    await message.answer("Mahsulot tavsifini kiriting:", reply_markup=kb.skip_cancel_kb())


@router.message(AddProduct.description, F.text)
async def add_product_description(message: Message, state: FSMContext):
    description = None if message.text == kb.BTN_SKIP else message.text.strip()[:900]
    await state.update_data(description=description)
    await state.set_state(AddProduct.price)
    await message.answer("Narxini kiriting (faqat raqam, so'mda). Masalan: 25000", reply_markup=kb.cancel_kb())


@router.message(AddProduct.price, F.text)
async def add_product_price(message: Message, state: FSMContext):
    raw = message.text.replace(" ", "").replace(",", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("❗️ Narx musbat butun son bo'lishi kerak. Masalan: 25000")
        return
    await state.update_data(price=int(raw))
    await state.set_state(AddProduct.photo)
    await message.answer("Mahsulot rasmini yuboring:", reply_markup=kb.skip_cancel_kb())


@router.message(AddProduct.photo, F.photo)
@router.message(AddProduct.photo, F.text == kb.BTN_SKIP)
async def add_product_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id if message.photo else None
    data = await state.get_data()
    await state.clear()
    if not await db.get_category(data["category_id"]):
        await message.answer("❗️ Kategoriya o'chirilgan. Qaytadan urinib ko'ring.", reply_markup=kb.main_menu(True))
        return
    await db.add_product(data["category_id"], data["name"], data["description"], data["price"], photo_id)
    await message.answer(
        f"✅ Mahsulot qo'shildi: <b>{escape(data['name'])}</b> — {fmt_price(data['price'])}",
        reply_markup=kb.main_menu(True),
    )
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu_kb())


@router.message(AddProduct.photo)
async def add_product_photo_invalid(message: Message):
    await message.answer("Iltimos, rasm yuboring yoki «O'tkazib yuborish» tugmasini bosing.")


# ---------------- Mahsulotni o'chirish ----------------
@router.callback_query(F.data == "adm:del_prod")
async def cb_del_product(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Kategoriyalar yo'q", show_alert=True)
        return
    await edit(callback, "Kategoriyani tanlang:", kb.categories_kb(categories, prefix="dpc"))


@router.callback_query(F.data.startswith("dpc:"))
async def cb_del_product_category(callback: CallbackQuery):
    products = await db.get_products(int(callback.data.split(":")[1]))
    if not products:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return
    await edit(callback, "Qaysi mahsulotni o'chirasiz?", kb.admin_products_delete_kb(products))


@router.callback_query(F.data.startswith("dp:"))
async def cb_del_product_do(callback: CallbackQuery):
    product = await db.get_product(int(callback.data.split(":")[1]))
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await db.delete_product(product["id"])
    await callback.answer(f"🗑 «{product['name']}» o'chirildi")
    products = await db.get_products(product["category_id"])
    if products:
        await edit(callback, "Qaysi mahsulotni o'chirasiz?", kb.admin_products_delete_kb(products))
    else:
        await edit(callback, "⚙️ <b>Admin panel</b>", kb.admin_menu_kb())


# ---------------- Buyurtmalar ----------------
@router.callback_query(F.data == "adm:orders")
async def cb_orders(callback: CallbackQuery):
    orders = await db.get_recent_orders()
    if not orders:
        await callback.answer("Hali buyurtmalar yo'q", show_alert=True)
        return
    lines = ["📋 <b>Oxirgi buyurtmalar:</b>\n"]
    for o in orders:
        lines.append(
            f"#{o['id']} • {escape(o['full_name'] or '')} • {escape(o['phone'] or '')}\n"
            f"    {fmt_price(o['total'])} • {kb.STATUS_LABELS.get(o['status'], o['status'])} • {o['created_at']}"
        )
    lines.append("\nBatafsil: /order <code>raqam</code>")
    await edit(callback, "\n".join(lines), kb.admin_menu_kb())


@router.message(Command("order"))
async def cmd_order(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("#").isdigit():
        await message.answer("Foydalanish: /order 12")
        return
    order_id = int(parts[1].lstrip("#"))
    order = await db.get_order(order_id)
    if not order:
        await message.answer("Buyurtma topilmadi.")
        return
    items = await db.get_order_items(order_id)
    await message.answer(kb.order_text(order, items, for_admin=True), reply_markup=kb.admin_order_kb(order_id))
    if order["latitude"] is not None:
        await message.answer_location(order["latitude"], order["longitude"])


@router.callback_query(F.data.startswith("status:"))
async def cb_order_status(callback: CallbackQuery, bot: Bot):
    _, order_id, status = callback.data.split(":")
    order_id = int(order_id)
    if status not in kb.STATUS_LABELS:
        await callback.answer()
        return
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    if order["status"] == status:
        await callback.answer("Holat allaqachon shunday")
        return
    await db.set_order_status(order_id, status)
    order["status"] = status
    items = await db.get_order_items(order_id)
    try:
        await callback.message.edit_text(
            kb.order_text(order, items, for_admin=True), reply_markup=kb.admin_order_kb(order_id)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(f"Holat o'zgardi: {kb.STATUS_LABELS[status]}")
    try:
        await bot.send_message(
            order["user_id"],
            f"🔔 Buyurtma #{order_id} holati o'zgardi: <b>{kb.STATUS_LABELS[status]}</b>",
        )
    except Exception as e:
        log.warning("Mijozga (%s) xabar yuborilmadi: %s", order["user_id"], e)


# ---------------- Statistika ----------------
@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    s = await db.get_stats()
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n"
        f"🛍 Faol mahsulotlar: <b>{s['products']}</b>\n"
        f"📦 Jami buyurtmalar: <b>{s['orders']}</b>\n"
        f"🆕 Yangi buyurtmalar: <b>{s['new_orders']}</b>\n"
        f"💰 Tushum (yetkazilgan): <b>{fmt_price(s['revenue'])}</b>"
    )
    await edit(callback, text, kb.admin_menu_kb())


# ---------------- Xabar yuborish (rassilka) ----------------
@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.message)
    await callback.message.answer(
        "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring (matn, rasm, video — istalgan):",
        reply_markup=kb.cancel_kb(),
    )
    await callback.answer()


@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    await message.answer(f"⏳ {len(user_ids)} ta foydalanuvchiga yuborilmoqda...", reply_markup=kb.main_menu(True))
    ok = fail = 0
    for uid in user_ids:
        try:
            await message.copy_to(uid)
            ok += 1
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            try:
                await message.copy_to(uid)
                ok += 1
            except Exception:
                fail += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)  # Telegram limitlaridan oshmaslik uchun
    await message.answer(f"✅ Yuborildi: {ok}\n❌ Yuborilmadi: {fail}")
