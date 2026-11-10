"""Do'kon bot — ishga tushirish fayli."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

import db
from config import ADMIN_IDS, BOT_TOKEN, payment_providers
from handlers import admin, common, payment, user
from i18n import LangMiddleware


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    if not BOT_TOKEN:
        sys.exit("❗️ BOT_TOKEN topilmadi. .env faylini yarating (.env.example ga qarang).")
    providers = payment_providers()
    logging.info("Onlayn to'lov: %s", ", ".join(providers) if providers else "o'chirilgan (faqat naqd)")
    if not ADMIN_IDS:
        logging.warning("ADMIN_IDS bo'sh — buyurtmalar hech kimga yuborilmaydi!")

    await db.init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    # Tartib muhim: common (start/bekor qilish) -> admin -> user
    # Har bir xabar/tugma bosilishiga foydalanuvchi tilini (lang) qo'shadi
    dp.message.middleware(LangMiddleware())
    dp.callback_query.middleware(LangMiddleware())
    dp.pre_checkout_query.middleware(LangMiddleware())
    # Tartib muhim: payment — user dan oldin (user oxirida hamma xabarni ushlovchi handler bor)
    dp.include_routers(common.router, admin.router, payment.router, user.router)

    await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish")])
    for code, description in {"ru": "Запустить бота", "kk": "Ботты іске қосу"}.items():
        await bot.set_my_commands([BotCommand(command="start", description=description)], language_code=code)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Bot ishga tushdi")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code not in (None, 0):
            raise
