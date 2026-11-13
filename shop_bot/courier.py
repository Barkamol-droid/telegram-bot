"""Kuryer boti: buyurtmalarni kuryerlarga tarqatish va yetkazib berish bosqichlari.

Ish tartibi:
1. Kuryer kuryer botiga /start bosadi va telefon raqamini yuboradi → adminga (asosiy botda) tasdiqlash so'rovi.
2. Yangi buyurtma barcha faol kuryerlarga boradi (mijoz ismi/telefoni hali ko'rsatilmaydi).
3. «📦 Oldim» — birinchi bosgan kuryer oladi; boshqalarda «🔒 Boshqa kuryer oldi».
   Olgan kuryerga mijoz ismi, telefoni va lokatsiyasi ko'rsatiladi.
4. «🚚 Yo'ldaman» → mijozga «yo'lda» xabari (kuryer ismi va telefoni bilan).
5. «✅ Topshirdim» → buyurtma «Yetkazildi», mijozga xabar va brilliantlar.
Admin har bosqichdan xabardor bo'ladi. Kuryer boti o'zbek tilida; mijozga xabarlar — mijoz tilida.
"""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

import colors as color_mod
import db
import keyboards as kb
from config import all_admin_ids, fmt_phone, fmt_price, now
from i18n import DEFAULT_LANG, t

log = logging.getLogger(__name__)
router = Router()

MAIN_BOT: Bot | None = None      # asosiy do'kon boti (mijoz va adminlarga xabar uchun)
COURIER_BOT: Bot | None = None   # kuryer boti

BTN_ACTIVE = "📋 Faol buyurtmalarim"
BTN_EARNINGS = "💰 Hisobim"


def setup(main_bot: Bot, courier_bot: Bot | None):
    global MAIN_BOT, COURIER_BOT
    MAIN_BOT, COURIER_BOT = main_bot, courier_bot


def enabled() -> bool:
    return COURIER_BOT is not None


class CourierReg(StatesGroup):
    phone = State()


def courier_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_ACTIVE), KeyboardButton(text=BTN_EARNINGS)]],
                               resize_keyboard=True)


# ---------------- Matnlar ----------------
def _variant(item: dict) -> str:
    parts = []
    if item.get("size"):
        parts.append(f"o'lcham {item['size']}")
    if item.get("color"):
        parts.append(color_mod.name(item["color"], "uz"))
    return f" ({', '.join(parts)})" if parts else ""


def order_text(order: dict, items: list[dict], full: bool) -> str:
    """Kuryer uchun buyurtma matni. full=False — buyurtma olinmaguncha mijoz ma'lumoti yashiriladi."""
    lines = [f"🧾 <b>Buyurtma #{order['id']}</b>"]
    if full:
        lines.append(f"👤 {escape(order['full_name'] or '')}")
        lines.append(f"📞 {escape(order['phone'] or '')}")
    if order.get("address"):
        lines.append(f"📍 {escape(order['address'])}")
    elif order.get("latitude") is not None:
        lines.append("📍 Lokatsiya yuborilgan" + ("" if full else " (olgandan keyin ko'rinadi)"))
    if order.get("comment"):
        lines.append(f"💬 {escape(order['comment'])}")
    lines.append("")
    for i in items:
        lines.append(f"• {escape(i['name'])}{escape(_variant(i))} — {i['qty']} dona")
    lines.append(f"\n💰 Jami: <b>{fmt_price(order['total'])}</b>")
    if order.get("payment_status") == "paid":
        lines.append("✅ To'langan — mijozdan pul olinmaydi")
    else:
        lines.append(f"💵 Mijozdan olinadi: <b>{fmt_price(order['total'])}</b>")
    if order.get("courier_fee") is not None:
        lines.append(f"🛵 Yetkazish haqi: <b>{fmt_price(order['courier_fee'])}</b>")
    return "\n".join(lines)


def closed_text(order: dict, items: list[dict], title: str) -> str:
    """Yakunlangan buyurtma — mijozning manzili, ismi, telefoni va izohisiz (maxfiylik uchun)."""
    lines = [title, ""]
    for i in items:
        lines.append(f"• {escape(i['name'])}{escape(_variant(i))} — {i['qty']} dona")
    if order.get("courier_fee") is not None:
        lines.append(f"\n🛵 Haqingiz: <b>{fmt_price(order['courier_fee'])}</b>")
    return "\n".join(lines)


async def _delete_location(order: dict):
    if order.get("courier_loc_msg") and order.get("courier_id"):
        try:
            await COURIER_BOT.delete_message(order["courier_id"], order["courier_loc_msg"])
        except Exception:
            pass
        await db.set_courier_location_message(order["id"], None)


def _kb(*buttons: tuple[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=txt, callback_data=data)] for txt, data in buttons])


async def _notify_admins(text: str, markup=None):
    for admin_id in all_admin_ids():
        try:
            await MAIN_BOT.send_message(admin_id, text, reply_markup=markup)
        except Exception as e:
            log.warning("Adminga (%s) xabar yuborilmadi: %s", admin_id, e)


async def _notify_customer(order: dict, text: str):
    try:
        await MAIN_BOT.send_message(order["user_id"], text)
    except Exception as e:
        log.warning("Mijozga (%s) xabar yuborilmadi: %s", order["user_id"], e)


def _customer_lang(order: dict) -> str:
    return order.get("lang") or DEFAULT_LANG


# ---------------- Buyurtmani kuryerlarga tarqatish ----------------
async def dispatch_order(order_id: int) -> int:
    """Yangi buyurtmani barcha faol kuryerlarga yuboradi. Qaytaradi: nechta kuryerga yetdi."""
    if not enabled():
        return 0
    order = await db.get_order(order_id)
    if order.get("courier_fee") is None:
        await db.set_order_courier_fee(order_id, await db.get_default_courier_fee())
        order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    text = "🆕 <b>Yangi buyurtma!</b>\n\n" + order_text(order, items, full=False)
    markup = _kb(("📦 Oldim", f"c_take:{order_id}"))
    sent: dict[int, int] = {}
    for courier in await db.get_couriers("active"):
        try:
            msg = await COURIER_BOT.send_message(courier["id"], text, reply_markup=markup)
            sent[courier["id"]] = msg.message_id
        except Exception as e:
            log.warning("Kuryerga (%s) yuborilmadi: %s", courier["id"], e)
    await db.save_courier_messages(order_id, sent)
    if not sent:
        await _notify_admins(f"⚠️ Buyurtma #{order_id}: faol kuryer topilmadi — buyurtma hech bir kuryerga yuborilmadi.")
    return len(sent)


async def notify_cancel(order_id: int):
    """Admin buyurtmani bekor qilganda: kuryer xabarlaridan manzil va tugmalar olib tashlanadi."""
    if not enabled():
        return
    order = await db.get_order(order_id)
    if not order:
        return
    await _delete_location(order)
    for courier_id, message_id in db.courier_messages(order).items():
        try:
            await COURIER_BOT.edit_message_text(chat_id=courier_id, message_id=message_id,
                                                text=f"❌ Buyurtma #{order_id} bekor qilindi.", reply_markup=None)
        except Exception:
            pass
        if courier_id == order.get("courier_id"):
            try:
                await COURIER_BOT.send_message(courier_id, f"❌ Buyurtma #{order_id} bekor qilindi — yetkazish shart emas.")
            except Exception:
                pass


async def fee_changed(order_id: int):
    """Admin kuryer haqini o'zgartirganda: hali olinmagan bo'lsa — takliflarni yangilash, olingan bo'lsa — kuryerga xabar."""
    if not enabled():
        return
    order = await db.get_order(order_id)
    if not order or order["status"] == "cancelled":
        return
    if order.get("courier_id"):
        if order.get("delivery_status") != "delivered":
            try:
                await COURIER_BOT.send_message(
                    order["courier_id"], f"💰 Buyurtma #{order_id} uchun yetkazish haqi: <b>{fmt_price(order['courier_fee'])}</b>"
                )
            except Exception:
                pass
        return
    items = await db.get_order_items(order_id)
    text = "🆕 <b>Yangi buyurtma!</b>\n\n" + order_text(order, items, full=False)
    for courier_id, message_id in db.courier_messages(order).items():
        try:
            await COURIER_BOT.edit_message_text(chat_id=courier_id, message_id=message_id, text=text,
                                                reply_markup=_kb(("📦 Oldim", f"c_take:{order_id}")))
        except Exception:
            pass


# ---------------- Ro'yxatdan o'tish ----------------
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    courier = await db.get_courier(message.from_user.id)
    if courier and courier["status"] == "active":
        await message.answer(f"👋 Salom, {escape(courier['full_name'] or '')}! Yangi buyurtmalar shu yerga keladi.",
                             reply_markup=courier_menu())
        return
    if courier and courier["status"] == "blocked":
        await message.answer("⛔️ Sizning kuryer hisobingiz o'chirilgan. Do'kon bilan bog'laning.")
        return
    if courier and courier["status"] == "pending":
        await message.answer("⏳ Arizangiz ko'rib chiqilmoqda. Tasdiqlangach xabar beramiz.")
        return
    await state.set_state(CourierReg.phone)
    await message.answer(
        "🛵 Kuryer sifatida ro'yxatdan o'tish uchun telefon raqamingizni yuboring 👇",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]], resize_keyboard=True
        ),
    )


@router.message(CourierReg.phone, F.contact)
async def reg_phone(message: Message, state: FSMContext):
    if message.contact.user_id and message.contact.user_id != message.from_user.id:
        await message.answer("Iltimos, o'zingizning raqamingizni yuboring.")
        return
    await state.clear()
    user = message.from_user
    phone = message.contact.phone_number
    phone = phone if phone.startswith("+") else "+" + phone
    status = await db.courier_request(user.id, user.full_name, phone, user.username)
    if status == "active":
        await message.answer("✅ Siz allaqachon kuryersiz.", reply_markup=courier_menu())
        return
    await message.answer("✅ Ariza yuborildi! Admin tasdiqlagach, buyurtmalar shu yerga keladi.",
                         reply_markup=courier_menu())
    await _notify_admins(
        f"🛵 <b>Yangi kuryer arizasi</b>\n\n👤 {escape(user.full_name)}\n📞 {escape(fmt_phone(phone))}"
        + (f"\n@{escape(user.username)}" if user.username else ""),
        InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"cr_ok:{user.id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"cr_no:{user.id}"),
        ]]),
    )


@router.message(CourierReg.phone)
async def reg_phone_invalid(message: Message):
    await message.answer("Iltimos, «📱 Raqamni yuborish» tugmasini bosing.")


async def _active_courier(callback: CallbackQuery) -> dict | None:
    courier = await db.get_courier(callback.from_user.id)
    if not courier or courier["status"] != "active":
        await callback.answer("Siz faol kuryer emassiz.", show_alert=True)
        return None
    return courier


# ---------------- Yetkazib berish bosqichlari ----------------
@router.callback_query(F.data.startswith("c_take:"))
async def take(callback: CallbackQuery):
    courier = await _active_courier(callback)
    if not courier:
        return
    order_id = int(callback.data.split(":")[1])
    if not await db.claim_order(order_id, courier["id"]):
        order = await db.get_order(order_id)
        reason = "❌ Buyurtma bekor qilingan." if order and order["status"] == "cancelled" else "🔒 Bu buyurtmani boshqa kuryer oldi."
        await callback.answer(reason, show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        return
    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    await callback.answer("✅ Buyurtma sizga biriktirildi")
    try:
        await callback.message.edit_text(
            "📦 <b>Siz oldingiz</b>\n\n" + order_text(order, items, full=True),
            reply_markup=_kb(("🚚 Yo'ldaman", f"c_way:{order_id}")),
        )
    except TelegramBadRequest:
        pass
    if order.get("latitude") is not None:
        try:
            location_msg = await callback.message.answer_location(order["latitude"], order["longitude"])
            await db.set_courier_location_message(order_id, location_msg.message_id)
        except TelegramBadRequest:
            pass
    # Boshqa kuryerlardagi xabarni yopish
    for courier_id, message_id in db.courier_messages(order).items():
        if courier_id == courier["id"]:
            continue
        try:
            await COURIER_BOT.edit_message_text(
                chat_id=courier_id, message_id=message_id,
                text=f"🔒 Buyurtma #{order_id} boshqa kuryerga biriktirildi.", reply_markup=None,
            )
        except Exception:
            pass
    lang = _customer_lang(order)
    await _notify_customer(order, t("courier_assigned", lang, id=order_id))
    await _notify_admins(f"🛵 Buyurtma #{order_id}: kuryer <b>{escape(courier['full_name'] or '')}</b> "
                         f"({escape(fmt_phone(courier['phone'] or ''))}) buyurtmani oldi.")


@router.callback_query(F.data.startswith("c_way:"))
async def on_way(callback: CallbackQuery):
    courier = await _active_courier(callback)
    if not courier:
        return
    order_id = int(callback.data.split(":")[1])
    if not await db.set_delivery_status(order_id, courier["id"], "on_way"):
        await callback.answer("Bu amalni bajarib bo'lmaydi (buyurtma holati o'zgargan).", show_alert=True)
        return
    await callback.answer("🚚 Yo'ldasiz")
    try:
        await callback.message.edit_reply_markup(reply_markup=_kb(("✅ Topshirdim", f"c_done:{order_id}")))
    except TelegramBadRequest:
        pass
    order = await db.get_order(order_id)
    lang = _customer_lang(order)
    await _notify_customer(order, t("courier_on_way", lang, id=order_id, name=escape(courier["full_name"] or ""),
                                    phone=escape(fmt_phone(courier["phone"] or ""))))
    await _notify_admins(f"🚚 Buyurtma #{order_id} yo'lda (kuryer: {escape(courier['full_name'] or '')}).")


@router.callback_query(F.data.startswith("c_done:"))
async def done(callback: CallbackQuery):
    courier = await _active_courier(callback)
    if not courier:
        return
    order_id = int(callback.data.split(":")[1])
    if not await db.set_delivery_status(order_id, courier["id"], "delivered"):
        await callback.answer("Bu amalni bajarib bo'lmaydi (buyurtma holati o'zgargan).", show_alert=True)
        return
    await callback.answer("✅ Rahmat! Buyurtma topshirildi.")
    order = await db.get_order(order_id)
    # Maxfiylik: topshirilgandan keyin mijoz manzili, ismi va telefoni kuryer chatidan o'chiriladi
    try:
        await callback.message.edit_text(
            closed_text(order, await db.get_order_items(order_id), f"✅ <b>Buyurtma #{order_id} topshirildi</b>"),
            reply_markup=None,
        )
    except TelegramBadRequest:
        pass
    await _delete_location(order)
    lang = _customer_lang(order)
    text = t("courier_delivered", lang, id=order_id)
    awarded = await db.award_order_bonus(order_id)
    if awarded:
        text += "\n\n" + t("bonus_earned_msg", lang, id=order_id, n=awarded["amount"], total=awarded["balance"],
                            value=kb.bonus_value(awarded["balance"], lang))
    await _notify_customer(order, text)
    paid = "to'langan" if order.get("payment_status") == "paid" else f"naqd {fmt_price(order['total'])} olindi"
    await _notify_admins(f"✅ Buyurtma #{order_id} topshirildi (kuryer: {escape(courier['full_name'] or '')}, {paid}).")


@router.message(F.text == BTN_ACTIVE)
async def active_orders(message: Message):
    courier = await db.get_courier(message.from_user.id)
    if not courier or courier["status"] != "active":
        await message.answer("Siz faol kuryer emassiz. /start")
        return
    orders = await db.courier_active_orders(courier["id"])
    if not orders:
        await message.answer("Hozir faol buyurtmangiz yo'q. Yangi buyurtmalar kelganda xabar beramiz.")
        return
    for order in orders:
        step = ("✅ Topshirdim", f"c_done:{order['id']}") if order["delivery_status"] == "on_way" \
            else ("🚚 Yo'ldaman", f"c_way:{order['id']}")
        await message.answer(order_text(order, await db.get_order_items(order["id"]), full=True), reply_markup=_kb(step))


@router.message(F.text == BTN_EARNINGS)
async def earnings(message: Message):
    courier = await db.get_courier(message.from_user.id)
    if not courier or courier["status"] != "active":
        await message.answer("Siz faol kuryer emassiz. /start")
        return
    today = await db.courier_earnings(courier["id"], now().strftime("%Y-%m-%d 00:00"))
    month = await db.courier_earnings(courier["id"], now().strftime("%Y-%m-01 00:00"))
    await message.answer(
        "💰 <b>Hisobingiz</b>\n\n"
        f"📅 Bugun: {today['count']} ta yetkazish — <b>{fmt_price(today['sum'])}</b>\n"
        f"🗓 Shu oy: {month['count']} ta yetkazish — <b>{fmt_price(month['sum'])}</b>",
        reply_markup=courier_menu(),
    )


@router.message()
async def fallback(message: Message):
    await message.answer("Buyurtmalar shu yerga avtomatik keladi. /start", reply_markup=courier_menu())
