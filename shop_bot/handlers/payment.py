"""Onlayn to'lov: Click va Payme (Telegram Payments orqali) hamda naqd to'lov.

Ishlash tartibi:
1. Buyurtma yaratilgach, mijozga to'lov usullari ko'rsatiladi (offer_payment).
2. Click/Payme tanlansa — Telegram ichida to'lov oynasi (invoice) yuboriladi.
3. To'lovdan oldin Telegram tekshiruv so'raydi (pre_checkout_query) — buyurtma, summa va holat tekshiriladi.
4. To'lov muvaffaqiyatli bo'lsa (successful_payment) — buyurtma «to'langan» deb belgilanadi,
   mijoz va adminlarga xabar boradi.
"""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

import db
import keyboards as kb
from config import (
    PAYMENT_NAMES, PAYMENT_TOKENS, SHOP_NAME, SHOP_PHONE, all_admin_ids, fmt_phone, fmt_price,
    is_test_token, payment_providers,
)
from i18n import loc, t

router = Router()
log = logging.getLogger(__name__)
CURRENCY = "UZS"


async def notify_admins(bot: Bot, text: str):
    for admin_id in all_admin_ids():
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            log.warning("Adminga (%s) xabar yuborilmadi: %s", admin_id, e)


def _order_payable(order, user_id: int) -> bool:
    return (
        order is not None
        and order["user_id"] == user_id
        and order.get("payment_status") != "paid"
        and order["status"] not in ("cancelled", "delivered")
    )


@router.callback_query(F.data.startswith("paymenu:"))
async def cb_payment_menu(callback: CallbackQuery, lang: str):
    order_id = int(callback.data.split(":")[1])
    order = await db.get_order(order_id)
    if not _order_payable(order, callback.from_user.id):
        await callback.answer(t("pay_unavailable", lang), show_alert=True)
        return
    await callback.message.answer(
        f"{t('invoice_title', lang, id=order_id)} — <b>{fmt_price(order['total'], lang)}</b>\n\n{t('choose_payment', lang)}",
        reply_markup=kb.payment_kb(order_id, lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:"))
async def cb_pay(callback: CallbackQuery, bot: Bot, lang: str):
    _, order_id, method = callback.data.split(":")
    order_id = int(order_id)
    order = await db.get_order(order_id)
    if not _order_payable(order, callback.from_user.id):
        await callback.answer(t("pay_unavailable", lang), show_alert=True)
        return

    if method == "cash":
        await db.set_payment_method(order_id, "cash")
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
        await callback.message.answer(t("pay_cash_ok", lang, id=order_id))
        await callback.answer()
        await notify_admins(bot, f"💵 Buyurtma #{order_id}: mijoz <b>naqd to'lov</b>ni tanladi "
                                 f"({fmt_price(order['total'])}).")
        return

    if method not in payment_providers():
        await callback.answer(t("pay_unavailable", lang), show_alert=True)
        return

    items = await db.get_order_items(order_id)
    names = ", ".join(loc(i, "name", lang) for i in items)
    description = t("invoice_desc", lang, shop=SHOP_NAME, items=names)
    if len(description) > 250:
        description = description[:247] + "..."
    title = t("invoice_title", lang, id=order_id)
    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=title,
            description=description,
            payload=f"order:{order_id}:{method}",
            provider_token=PAYMENT_TOKENS[method],
            currency=CURRENCY,
            prices=[LabeledPrice(label=title, amount=int(order["total"]) * 100)],  # tiyinda
        )
    except TelegramBadRequest as e:
        log.warning("Invoice yuborilmadi (#%s, %s): %s", order_id, method, e)
        await callback.message.answer(
            t("pay_failed", lang, phone=fmt_phone(SHOP_PHONE)),
            reply_markup=kb.payment_kb(order_id, lang),
        )
        await callback.answer()
        return
    await callback.message.answer(t("pay_hint", lang, provider=PAYMENT_NAMES[method]))
    await callback.answer()


def _parse_payload(payload: str) -> tuple[int, str] | None:
    try:
        prefix, order_id, method = payload.split(":")
        if prefix != "order" or method not in PAYMENT_NAMES:
            return None
        return int(order_id), method
    except ValueError:
        return None


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery, lang: str):
    """Telegram to'lovdan oldin so'raydi: buyurtma hali to'lash mumkinmi va summa to'g'rimi."""
    parsed = _parse_payload(query.invoice_payload)
    order = await db.get_order(parsed[0]) if parsed else None
    ok = (
        _order_payable(order, query.from_user.id)
        and query.currency == CURRENCY
        and query.total_amount == int(order["total"]) * 100
    )
    if ok:
        await query.answer(ok=True)
    else:
        await query.answer(ok=False, error_message=t("pay_unavailable", lang))


@router.message(F.successful_payment)
async def successful_payment(message: Message, bot: Bot, lang: str):
    payment = message.successful_payment
    parsed = _parse_payload(payment.invoice_payload)
    if not parsed:
        log.error("Noma'lum to'lov payload: %s", payment.invoice_payload)
        return
    order_id, method = parsed
    is_new = await db.mark_paid(
        order_id, method, payment.telegram_payment_charge_id, payment.provider_payment_charge_id
    )
    if not is_new:
        return  # takroriy xabar
    amount = fmt_price(payment.total_amount // 100, lang)
    await message.answer(t("pay_ok", lang, id=order_id, amount=amount, provider=PAYMENT_NAMES[method]))
    order = await db.get_order(order_id)
    test = " 🧪 <i>(TEST to'lov — haqiqiy pul emas)</i>" if is_test_token(method) else ""
    await notify_admins(
        bot,
        f"✅ <b>Buyurtma #{order_id} to'landi!</b>{test}\n\n"
        f"💳 {PAYMENT_NAMES[method]}: <b>{fmt_price(payment.total_amount // 100)}</b>\n"
        f"👤 {escape(order['full_name'] or '')} • {escape(order['phone'] or '')}\n"
        f"🧾 Telegram ID: <code>{escape(payment.telegram_payment_charge_id)}</code>\n"
        f"🧾 {PAYMENT_NAMES[method]} ID: <code>{escape(payment.provider_payment_charge_id)}</code>\n\n"
        f"Batafsil: /order {order_id}",
    )
