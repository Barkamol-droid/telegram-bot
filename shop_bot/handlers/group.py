"""Xodimlar guruhi: buyurtma xabarlari va boshqaruv tugmalari guruhda ishlaydi.

- /ulash — (faqat admin) shu guruhni buyurtmalar guruhi qilish; /uzish — uzish.
- Guruh oddiy guruhdan supergroup'ga o'tsa — yangi ID avtomatik saqlanadi.
- Guruhdagi boshqa xabarlarga bot javob bermaydi (suhbatga aralashmaydi).
- Guruh a'zolari (operatorlar) buyurtma tugmalarini bosa oladi; qolgan tugmalar — faqat admin.
"""
from aiogram import F, Router
from aiogram.filters import BaseFilter, Command
from aiogram.types import CallbackQuery, Message

import db
from config import is_admin

GROUP_TYPES = {"group", "supergroup"}
# Guruhdagi istalgan a'zo bosishi mumkin bo'lgan tugmalar (buyurtma bilan ishlash)
STAFF_CALLBACKS = ("status:", "cfee:", "cpa:", "crep:")

router = Router()
router.message.filter(F.chat.type.in_(GROUP_TYPES))


class ForbiddenInGroup(BaseFilter):
    """Guruhda admin bo'lmagan a'zo — operatorlarga ruxsat etilmagan tugmani bosdi."""

    async def __call__(self, callback: CallbackQuery) -> bool:
        message = callback.message
        if not message or message.chat.type not in GROUP_TYPES or is_admin(callback.from_user.id):
            return False
        return not (callback.data or "").startswith(STAFF_CALLBACKS)


@router.message(Command("ulash", "bind"))
async def bind(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("⛔️ Guruhni faqat admin ulay oladi.")
        return
    await db.set_staff_group(message.chat.id)
    await message.reply(
        "✅ <b>Guruh ulandi!</b>\n\nEndi yangi buyurtmalar, to'lovlar va kuryer xabarlari shu guruhga keladi.\n"
        "• Buyurtma tugmalarini (qabul qilish, yetkazildi, bekor qilish, kuryer haqi) guruhdagi har bir a'zo bosa oladi.\n"
        "• Summa yoki javob kiritish shaxsiy chatda so'raladi — buning uchun botga shaxsiy chatda /start bosilgan bo'lsin.\n"
        "• Uzish: /uzish"
    )


@router.message(Command("uzish", "unbind"))
async def unbind(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("⛔️ Faqat admin uza oladi.")
        return
    if await db.get_staff_group() == message.chat.id:
        await db.set_staff_group(None)
        await message.reply("✅ Guruh uzildi. Xabarlar endi adminlarning shaxsiy chatiga boradi.")
    else:
        await message.reply("Bu guruh ulanmagan.")


@router.message(F.migrate_to_chat_id)
async def migrated(message: Message):
    """Guruh supergroup'ga aylanganda Telegram uning ID sini o'zgartiradi — yangisini saqlaymiz."""
    if await db.get_staff_group() == message.chat.id:
        await db.set_staff_group(message.migrate_to_chat_id)


@router.message()
async def ignore_group_messages(message: Message):
    """Guruhdagi oddiy suhbatga bot javob bermaydi."""
    return


@router.callback_query(ForbiddenInGroup())
async def forbidden(callback: CallbackQuery):
    await callback.answer("⛔️ Bu amal faqat admin uchun.", show_alert=True)
