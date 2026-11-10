"""💎 Brilliant (bonus) bo'limi: balans, tarix va do'stga sovg'a qilish."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
import keyboards as kb
from config import BONUS_STEP, fmt_price, is_admin
from i18n import DEFAULT_LANG, all_texts, t
from states import BonusSend

router = Router()
log = logging.getLogger(__name__)


async def bonus_overview(user_id: int, lang: str) -> tuple[str, object]:
    balance = await db.get_bonus(user_id)
    text = t("bonus_info", lang, n=balance, value=kb.bonus_value(balance, lang),
             step=fmt_price(BONUS_STEP, lang), one=kb.bonus_value(1, lang))
    history = await db.bonus_history(user_id)
    if history:
        lines = [f"\n\n{t('bonus_history', lang)}"]
        for tx in history:
            sign = "+" if tx["amount"] > 0 else ""
            order = f" #{tx['order_id']}" if tx.get("order_id") else ""
            lines.append(f"{sign}{tx['amount']} 💎 — {t('btx_' + tx['kind'], lang)}{order} • {tx['created_at'][:10]}")
        text += "\n".join(lines)
    return text, kb.bonus_menu_kb(lang, balance > 0)


@router.message(F.text.in_(all_texts("btn_bonus")))
async def my_bonus(message: Message, lang: str):
    text, markup = await bonus_overview(message.from_user.id, lang)
    await message.answer(text, reply_markup=markup)


# ---------------- Do'stga yuborish ----------------
@router.callback_query(F.data == "bsend")
async def cb_send_start(callback: CallbackQuery, state: FSMContext, lang: str):
    if await db.get_bonus(callback.from_user.id) <= 0:
        await callback.answer(t("no_bonus", lang, step=fmt_price(BONUS_STEP, lang)), show_alert=True)
        return
    await state.set_state(BonusSend.recipient)
    await callback.message.answer(t("ask_recipient", lang), reply_markup=kb.pick_contact_kb(lang))
    await callback.answer()


@router.message(BonusSend.recipient, F.users_shared)
async def send_pick_recipient(message: Message, state: FSMContext, lang: str):
    shared = message.users_shared.users[0]
    if shared.user_id == message.from_user.id:
        await message.answer(t("self_send", lang))
        return
    name = " ".join(x for x in [shared.first_name, shared.last_name] if x) or shared.username or str(shared.user_id)
    balance = await db.get_bonus(message.from_user.id)
    await state.update_data(to_id=shared.user_id, to_name=name, to_username=shared.username)
    await state.set_state(BonusSend.amount)
    await message.answer(t("ask_bonus_amount", lang, name=escape(name), n=balance), reply_markup=kb.cancel_kb(lang))


@router.message(BonusSend.recipient)
async def send_recipient_hint(message: Message, lang: str):
    await message.answer(t("recipient_hint", lang), reply_markup=kb.pick_contact_kb(lang))


@router.message(BonusSend.amount, F.text)
async def send_amount(message: Message, state: FSMContext, lang: str):
    balance = await db.get_bonus(message.from_user.id)
    raw = message.text.strip()
    if not raw.isdigit() or not 1 <= int(raw) <= balance:
        await message.answer(t("bad_bonus_amount", lang, n=balance))
        return
    data = await state.get_data()
    await state.update_data(amount=int(raw))
    await message.answer(
        t("confirm_send", lang, name=escape(data["to_name"]), n=int(raw), value=kb.bonus_value(int(raw), lang)),
        reply_markup=kb.confirm_send_kb(lang),
    )


@router.callback_query(BonusSend.amount, F.data == "bsend_no")
async def cb_send_cancel(callback: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    try:
        await callback.message.edit_text(t("cancelled", lang))
    except TelegramBadRequest:
        pass
    await callback.message.answer("💎", reply_markup=kb.main_menu(lang, is_admin(callback.from_user.id)))
    await callback.answer()


@router.callback_query(BonusSend.amount, F.data == "bsend_ok")
async def cb_send_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, lang: str):
    data = await state.get_data()
    await state.clear()
    sender = callback.from_user
    if "amount" not in data:
        await callback.answer()
        return
    await db.ensure_user(data["to_id"], data["to_name"], data.get("to_username"))
    left = await db.transfer_bonus(sender.id, data["to_id"], data["amount"])
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    menu = kb.main_menu(lang, is_admin(sender.id))
    if left is None:
        await callback.message.answer(t("send_failed", lang), reply_markup=menu)
        await callback.answer()
        return
    await callback.message.answer(
        t("sent_ok", lang, name=escape(data["to_name"]), n=data["amount"], left=left), reply_markup=menu
    )
    await callback.answer()
    # Qabul qiluvchiga o'z tilida xabar
    to_lang = await db.get_user_lang(data["to_id"]) or DEFAULT_LANG
    total = await db.get_bonus(data["to_id"])
    try:
        await bot.send_message(
            data["to_id"],
            t("bonus_received", to_lang, name=escape(sender.full_name), n=data["amount"],
              value=kb.bonus_value(data["amount"], to_lang), total=total),
        )
    except Exception:
        me = await bot.me()
        await callback.message.answer(t("sent_not_started", lang, link=f"https://t.me/{me.username}"))
