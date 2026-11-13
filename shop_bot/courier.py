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


class CourierText(StatesGroup):
    problem = State()   # «Boshqa sabab» matni
    message = State()   # adminga xabar


BTN_CANCEL = "❌ Bekor qilish"
PROBLEM_REASONS = {
    "noanswer": "📵 Mijoz javob bermayapti",
    "refused": "🙅 Mijoz qabul qilishdan bosh tortdi",
    "address": "📍 Manzil noto'g'ri / topilmadi",
}


def step_kb(order: dict) -> InlineKeyboardMarkup | None:
    """Buyurtma bosqichiga mos kuryer tugmalari."""
    oid, status = order["id"], order.get("delivery_status")
    msg = ("💬 Adminga yozish", f"c_msg:{oid}")
    if status == "assigned":
        return _kb(("🚚 Yo'ldaman", f"c_way:{oid}"), ("⚠️ Muammo", f"c_prob:{oid}"), msg, ("↩️ Voz kechish", f"c_rel:{oid}"))
    if status == "on_way":
        return _kb(("✅ Topshirdim", f"c_done:{oid}"), ("⚠️ Muammo", f"c_prob:{oid}"), msg)
    if status == "problem":
        return _kb(msg)
    if status == "returning":
        return _kb(("🏪 Do'konga topshirdim", f"c_ret:{oid}"), msg)
    return None


def text_entry_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


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
async def dispatch_order(order_id: int, exclude: int | None = None) -> int:
    """Yangi buyurtmani barcha faol kuryerlarga yuboradi (exclude — bu kuryerga yubormaslik).
    Qaytaradi: nechta kuryerga yetdi."""
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
        if courier["id"] == exclude:
            continue
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
    """Admin buyurtmani bekor qilganda: kuryer xabarlaridan manzil olib tashlanadi.
    Buyurtma kuryerda bo'lsa — mahsulotni do'konga qaytarish so'raladi («🏪 Do'konga topshirdim»)."""
    if not enabled():
        return
    order = await db.get_order(order_id)
    if not order:
        return
    await _delete_location(order)
    returning = await db.set_returning(order_id)
    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    for courier_id, message_id in db.courier_messages(order).items():
        is_holder = courier_id == order.get("courier_id")
        text = (closed_text(order, items, f"❌ <b>Buyurtma #{order_id} bekor qilindi</b> — 🏪 mahsulotni do'konga qaytaring")
                if is_holder and returning else f"❌ Buyurtma #{order_id} bekor qilindi.")
        try:
            await COURIER_BOT.edit_message_text(chat_id=courier_id, message_id=message_id, text=text,
                                                reply_markup=step_kb(order) if is_holder and returning else None)
        except Exception:
            pass
        if is_holder:
            try:
                await COURIER_BOT.send_message(
                    courier_id,
                    f"❌ Buyurtma #{order_id} bekor qilindi. 🏪 Mahsulotni do'konga qaytaring va «🏪 Do'konga topshirdim» ni bosing."
                    if returning else f"❌ Buyurtma #{order_id} bekor qilindi — yetkazish shart emas.",
                    reply_markup=step_kb(order) if returning else None,
                )
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
            reply_markup=step_kb(order),
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
    order = await db.get_order(order_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=step_kb(order))
    except TelegramBadRequest:
        pass
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
        items = await db.get_order_items(order["id"])
        if order["delivery_status"] == "returning":
            text = closed_text(order, items, f"🏪 <b>Buyurtma #{order['id']} bekor qilingan — mahsulotni do'konga qaytaring</b>")
        else:
            text = order_text(order, items, full=True)
            if order["delivery_status"] == "problem":
                text = "⏳ <b>Admin qarorini kuting</b>\n\n" + text
        await message.answer(text, reply_markup=step_kb(order))


# ---------------- Voz kechish ----------------
@router.callback_query(F.data.startswith("c_rel:"))
async def release_ask(callback: CallbackQuery):
    if not await _active_courier(callback):
        return
    order_id = int(callback.data.split(":")[1])
    await callback.answer()
    try:
        await callback.message.edit_reply_markup(reply_markup=_kb(
            ("✅ Ha, voz kechaman", f"c_relok:{order_id}"), ("⬅️ Yo'q, davom etaman", f"c_back:{order_id}")))
    except TelegramBadRequest:
        pass


@router.callback_query(F.data.startswith("c_back:"))
async def back_to_steps(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    order = await db.get_order(int(callback.data.split(":")[1]))
    await callback.answer()
    if order and order.get("courier_id") == callback.from_user.id:
        try:
            await callback.message.edit_reply_markup(reply_markup=step_kb(order))
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.startswith("c_relok:"))
async def release_confirm(callback: CallbackQuery):
    courier = await _active_courier(callback)
    if not courier:
        return
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order(order_id)
    if not order or not await db.release_order(order_id, courier["id"]):
        await callback.answer("Voz kechib bo'lmaydi: yo'lga chiqqansiz yoki buyurtma holati o'zgargan. "
                              "«⚠️ Muammo» yoki «💬 Adminga yozish» dan foydalaning.", show_alert=True)
        return
    await _delete_location(order)
    await callback.answer("↩️ Voz kechdingiz")
    try:
        await callback.message.edit_text(
            closed_text(order, await db.get_order_items(order_id),
                        f"↩️ <b>Siz buyurtma #{order_id} dan voz kechdingiz.</b> Mahsulot sizda bo'lsa, do'konga qaytaring."),
            reply_markup=None,
        )
    except TelegramBadRequest:
        pass
    sent = await dispatch_order(order_id, exclude=courier["id"])
    await _notify_admins(f"↩️ Kuryer <b>{escape(courier['full_name'] or '')}</b> buyurtma #{order_id} dan voz kechdi. "
                         f"Buyurtma qayta {sent} ta kuryerga yuborildi.")


# ---------------- Muammo (manzilda) ----------------
@router.callback_query(F.data.startswith("c_prob:"))
async def problem_ask(callback: CallbackQuery):
    if not await _active_courier(callback):
        return
    order_id = int(callback.data.split(":")[1])
    await callback.answer()
    buttons = [(text, f"cpr:{order_id}:{code}") for code, text in PROBLEM_REASONS.items()]
    buttons += [("✍️ Boshqa sabab", f"cpr:{order_id}:other"), ("⬅️ Orqaga", f"c_back:{order_id}")]
    try:
        await callback.message.edit_reply_markup(reply_markup=_kb(*buttons))
    except TelegramBadRequest:
        pass


async def _submit_problem(message: Message, courier: dict, order_id: int, reason: str, source_message: Message | None):
    if not await db.report_problem(order_id, courier["id"], reason):
        await message.answer("Bu buyurtma bo'yicha muammo yuborib bo'lmaydi (holati o'zgargan).")
        return
    order = await db.get_order(order_id)
    if source_message:
        try:
            await source_message.edit_reply_markup(reply_markup=step_kb(order))
        except TelegramBadRequest:
            pass
    await message.answer("⏳ Adminga yuborildi. Qarorini kuting — javob shu yerga keladi.", reply_markup=courier_menu())
    items = await db.get_order_items(order_id)
    await _notify_admins(
        f"⚠️ <b>Yetkazishda muammo — buyurtma #{order_id}</b>\n\n"
        f"Sabab: <b>{escape(reason)}</b>\n"
        f"🛵 Kuryer: {escape(courier['full_name'] or '')}, {escape(fmt_phone(courier['phone'] or ''))}\n\n"
        + kb.order_text(order, items, "uz", for_admin=True),
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish va qaytarish", callback_data=f"cpa:{order_id}:cancel")],
            [InlineKeyboardButton(text="🔁 Qayta urinsin", callback_data=f"cpa:{order_id}:retry"),
             InlineKeyboardButton(text="🔄 Boshqa kuryerga", callback_data=f"cpa:{order_id}:reassign")],
            [InlineKeyboardButton(text="↩️ Kuryerga javob", callback_data=f"crep:{courier['id']}:{order_id}")],
        ]),
    )


@router.callback_query(F.data.startswith("cpr:"))
async def problem_reason(callback: CallbackQuery, state: FSMContext):
    courier = await _active_courier(callback)
    if not courier:
        return
    _, order_id, code = callback.data.split(":")
    await callback.answer()
    if code == "other":
        await state.set_state(CourierText.problem)
        await state.update_data(order_id=int(order_id), source_message_id=callback.message.message_id)
        await callback.message.answer("✍️ Muammoni qisqacha yozing:", reply_markup=text_entry_kb())
        return
    await _submit_problem(callback.message, courier, int(order_id), PROBLEM_REASONS.get(code, code), callback.message)


@router.message(F.text == BTN_CANCEL)
async def cancel_text(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=courier_menu())


@router.message(CourierText.problem, F.text)
async def problem_text(message: Message, state: FSMContext):
    courier = await db.get_courier(message.from_user.id)
    data = await state.get_data()
    await state.clear()
    if not courier or courier["status"] != "active":
        await message.answer("Siz faol kuryer emassiz.")
        return
    await _submit_problem(message, courier, data["order_id"], message.text.strip()[:400], None)


# ---------------- Adminga xabar ----------------
@router.callback_query(F.data.startswith("c_msg:"))
async def message_ask(callback: CallbackQuery, state: FSMContext):
    if not await _active_courier(callback):
        return
    await state.set_state(CourierText.message)
    await state.update_data(order_id=int(callback.data.split(":")[1]))
    await callback.message.answer("💬 Adminga xabaringizni yozing:", reply_markup=text_entry_kb())
    await callback.answer()


@router.message(CourierText.message, F.text)
async def message_send(message: Message, state: FSMContext):
    courier = await db.get_courier(message.from_user.id)
    order_id = (await state.get_data()).get("order_id")
    await state.clear()
    if not courier or courier["status"] != "active":
        await message.answer("Siz faol kuryer emassiz.")
        return
    await _notify_admins(
        f"💬 <b>Kuryerdan xabar</b> (buyurtma #{order_id})\n"
        f"🛵 {escape(courier['full_name'] or '')}, {escape(fmt_phone(courier['phone'] or ''))}\n\n{escape(message.text[:2000])}",
        InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="↩️ Javob berish", callback_data=f"crep:{courier['id']}:{order_id}")
        ]]),
    )
    await message.answer("✅ Xabar adminga yuborildi. Javob shu yerga keladi.", reply_markup=courier_menu())


# ---------------- Do'konga qaytarish ----------------
@router.callback_query(F.data.startswith("c_ret:"))
async def returned(callback: CallbackQuery):
    courier = await _active_courier(callback)
    if not courier:
        return
    order_id = int(callback.data.split(":")[1])
    if not await db.mark_returned(order_id, courier["id"]):
        await callback.answer("Bu amalni bajarib bo'lmaydi.", show_alert=True)
        return
    order = await db.get_order(order_id)
    await callback.answer("✅ Rahmat!")
    try:
        await callback.message.edit_text(
            closed_text(order, await db.get_order_items(order_id), f"🏪 <b>Buyurtma #{order_id} do'konga qaytarildi</b>"),
            reply_markup=None,
        )
    except TelegramBadRequest:
        pass
    await _notify_admins(f"🏪 Buyurtma #{order_id} mahsulotlari do'konga qaytarildi (kuryer: {escape(courier['full_name'] or '')}).")


# ---------------- Admin qarorlari (asosiy botdan chaqiriladi) ----------------
async def problem_retry(order_id: int) -> bool:
    if not await db.resolve_problem_retry(order_id):
        return False
    order = await db.get_order(order_id)
    try:
        await COURIER_BOT.send_message(
            order["courier_id"],
            f"🔁 <b>Admin: buyurtma #{order_id} ni yetkazishni davom ettiring.</b>\n\n"
            + order_text(order, await db.get_order_items(order_id), full=True),
            reply_markup=step_kb(order),
        )
    except Exception as e:
        log.warning("Kuryerga yuborilmadi: %s", e)
    return True


async def problem_reassign(order_id: int) -> int | None:
    """Buyurtmani joriy kuryerdan olib, boshqa kuryerlarga qayta yuboradi. Qaytaradi: nechta kuryerga yuborildi."""
    order = await db.get_order(order_id)
    if not order:
        return None
    await _delete_location(order)
    old = await db.admin_release_order(order_id)
    if old is None and order.get("courier_id") is not None:
        return None
    items = await db.get_order_items(order_id)
    if old:
        for courier_id, message_id in db.courier_messages(order).items():
            if courier_id == old:
                try:
                    await COURIER_BOT.edit_message_text(
                        chat_id=courier_id, message_id=message_id, reply_markup=None,
                        text=closed_text(order, items, f"🔄 <b>Buyurtma #{order_id} boshqa kuryerga berildi.</b> "
                                                       "Mahsulot sizda bo'lsa, do'konga qaytaring."))
                except Exception:
                    pass
        try:
            await COURIER_BOT.send_message(old, f"🔄 Admin buyurtma #{order_id} ni boshqa kuryerga berdi.")
        except Exception:
            pass
    return await dispatch_order(order_id, exclude=old)


async def reply_to_courier(courier_id: int, order_id: str, text: str) -> bool:
    try:
        await COURIER_BOT.send_message(courier_id, f"💬 <b>Admin</b> (buyurtma #{order_id}):\n{escape(text)}",
                                       reply_markup=courier_menu())
        return True
    except Exception as e:
        log.warning("Kuryerga (%s) javob yuborilmadi: %s", courier_id, e)
        return False


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
