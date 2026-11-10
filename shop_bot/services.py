"""Bot chati va sayt (Mini App) uchun umumiy amallar."""
import logging

from aiogram import Bot

import db
import keyboards as kb
from config import all_admin_ids, payment_providers
from i18n import t

log = logging.getLogger(__name__)


async def finish_order(bot: Bot, order_id: int, lang: str, send_summary: bool = True):
    """Buyurtma yaratilgandan keyin: mijozga xulosa va to'lov usullari, adminlarga xabar."""
    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    user_id = order["user_id"]
    try:
        if send_summary:
            await bot.send_message(
                user_id,
                f"{t('order_accepted', lang)}\n\n{kb.order_text(order, items, lang)}\n\n{t('order_thanks', lang)}",
            )
        if order["payment_method"] == "bonus":
            await bot.send_message(user_id, t("paid_by_bonus", lang))
        elif payment_providers() and order.get("payment_status") != "paid":
            await bot.send_message(user_id, t("choose_payment", lang), reply_markup=kb.payment_kb(order_id, lang))
    except Exception as e:
        log.warning("Mijozga (%s) buyurtma xabari yuborilmadi: %s", user_id, e)

    # Adminlarga xabar (o'zbek tilida)
    admin_text = "🔔 <b>Yangi buyurtma!</b>\n\n" + kb.order_text(order, items, "uz", for_admin=True)
    for admin_id in all_admin_ids():
        try:
            await bot.send_message(admin_id, admin_text, reply_markup=kb.admin_order_kb(order_id))
            if order["latitude"] is not None:
                await bot.send_location(admin_id, order["latitude"], order["longitude"])
        except Exception as e:  # admin botni bloklagan bo'lishi mumkin
            log.warning("Adminga (%s) xabar yuborilmadi: %s", admin_id, e)
