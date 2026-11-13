"""Do'kon bot — ishga tushirish fayli."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo

import db
import courier
from config import ADMIN_IDS, BOT_TOKEN, COURIER_BOT_TOKEN, PORT, WEBAPP_URL, payment_providers
from handlers import admin, bonus, common, payment, user
from i18n import LangMiddleware
from webapp.server import start_web_server


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
    dp.include_routers(common.router, admin.router, payment.router, bonus.router, user.router)

    await bot.set_my_commands([BotCommand(command="start", description="Botni ishga tushirish")])
    for code, description in {"ru": "Запустить бота", "kk": "Ботты іске қосу"}.items():
        await bot.set_my_commands([BotCommand(command="start", description=description)], language_code=code)
    # Sayt ko'rinishi (Mini App) uchun veb-server — bot bilan bitta jarayonda
    runner = await start_web_server(bot, PORT)
    if WEBAPP_URL:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="🛍 Shop", web_app=WebAppInfo(url=WEBAPP_URL)))
        logging.info("Sayt manzili: %s", WEBAPP_URL)
    else:
        logging.warning("WEBAPP_URL yo'q — sayt tugmalari ko'rsatilmaydi (Railway'da «Generate Domain» qiling)")
    await bot.delete_webhook(drop_pending_updates=True)

    # Kuryer boti (ixtiyoriy) — alohida bot, bitta jarayonda
    courier_bot = None
    pollers = [dp.start_polling(bot)]
    if COURIER_BOT_TOKEN:
        courier_bot = Bot(COURIER_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        courier_dp = Dispatcher(storage=MemoryStorage())
        courier_dp.include_router(courier.router)
        await courier_bot.delete_webhook(drop_pending_updates=True)
        await courier_bot.set_my_commands([BotCommand(command="start", description="Kuryer menyusi")])
        pollers.append(courier_dp.start_polling(courier_bot, handle_signals=False))
        logging.info("Kuryer boti ishga tushdi: @%s", (await courier_bot.me()).username)
    else:
        logging.info("Kuryer boti o'chirilgan (COURIER_BOT_TOKEN yo'q)")
    courier.setup(bot, courier_bot)

    logging.info("Bot ishga tushdi")
    try:
        await asyncio.gather(*pollers)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit) as e:
        if isinstance(e, SystemExit) and e.code not in (None, 0):
            raise
