"""Bot chati va sayt (Mini App) uchun umumiy amallar."""
import logging
from html import escape

from aiogram import Bot

import db
import keyboards as kb
from config import all_admin_ids, payment_providers
from i18n import t

log = logging.getLogger(__name__)


async def notify_staff(bot: Bot, text: str, markup=None, location: tuple[float, float] | None = None) -> str:
    """Xodimlarga xabar: guruh ulangan bo'lsa — guruhga, aks holda (yoki guruhga yetmasa) — har bir adminga.
    Qaytaradi: "group" yoki "admins"."""
    group = await db.get_staff_group()
    if group:
        try:
            await bot.send_message(group, text, reply_markup=markup)
            if location:
                await bot.send_location(group, *location)
            return "group"
        except Exception as e:  # bot guruhdan chiqarilgan bo'lishi mumkin — adminlarga yuboramiz
            log.warning("Xodimlar guruhiga (%s) yuborilmadi, adminlarga yuborilmoqda: %s", group, e)
    for admin_id in all_admin_ids():
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
            if location:
                await bot.send_location(admin_id, *location)
        except Exception as e:  # admin botni bloklagan bo'lishi mumkin
            log.warning("Adminga (%s) xabar yuborilmadi: %s", admin_id, e)
    return "admins"


async def finish_order(bot: Bot, order_id: int, lang: str, send_summary: bool = True) -> bool:
    """Buyurtma yaratilgandan keyin: mijozga xulosa va to'lov usullari, adminlarga xabar.
    Qaytaradi: mijozga Telegram'da xabar yetib bordimi."""
    notified = False
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
        notified = True
    except Exception as e:
        log.warning("Mijozga (%s) buyurtma xabari yuborilmadi: %s", user_id, e)

    # Adminlarga xabar (o'zbek tilida) + kam qolgan mahsulotlar haqida ogohlantirish
    admin_text = "🔔 <b>Yangi buyurtma!</b>\n\n" + kb.order_text(order, items, "uz", for_admin=True)
    low = await db.low_stock_products([i["product_id"] for i in items])
    if low:
        admin_text += "\n\n" + "\n".join(
            f"❌ «{escape(p['name'])}» tugadi!" if p["stock"] <= 0 else f"⚠️ «{escape(p['name'])}» dan {p['stock']} ta qoldi"
            for p in low
        ) + "\n<i>Qoldiqni: ✏️ Mahsulotni tahrirlash → 📦 Soni</i>"
    location = (order["latitude"], order["longitude"]) if order["latitude"] is not None else None
    await notify_staff(bot, admin_text, kb.admin_order_kb(order_id), location)
    # Kuryer boti yoqilgan bo'lsa — buyurtmani kuryerlarga tarqatish
    try:
        import courier
        await courier.dispatch_order(order_id)
    except Exception as e:
        log.warning("Buyurtma #%s kuryerlarga yuborilmadi: %s", order_id, e)
    return notified
