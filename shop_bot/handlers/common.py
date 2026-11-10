"""Har qanday holatda ishlaydigan umumiy handlerlar: /start, til tanlash, bekor qilish."""
from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, MenuButtonWebApp, Message, WebAppInfo

import db
import keyboards as kb
from config import WEBAPP_URL, is_admin
from i18n import LANGS, all_texts, remember_lang, t

router = Router()


async def send_welcome(message: Message, first_name: str, user_id: int, lang: str):
    await message.answer(kb.welcome_text(first_name, lang), reply_markup=kb.main_menu(lang, is_admin(user_id)))
    if WEBAPP_URL:
        # Chat menyusidagi «🛍 Do'kon» tugmasi — foydalanuvchi tilida
        try:
            await message.bot.set_chat_menu_button(
                chat_id=user_id,
                menu_button=MenuButtonWebApp(text=t("menu_shop", lang), web_app=WebAppInfo(url=WEBAPP_URL)),
            )
        except Exception:
            pass
        await message.answer(t("open_shop_hint", lang), reply_markup=kb.open_shop_kb(lang))
    promo = await db.get_promo()
    category = await db.get_category(promo["category_id"]) if promo and promo.get("category_id") else None
    banner = kb.promo_banner(promo, lang, category)
    if banner:
        await message.answer(banner, reply_markup=kb.shop_now_kb(lang))


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, lang: str):
    await state.clear()
    user = message.from_user
    await db.add_user(user.id, user.full_name, user.username)
    if not await db.get_user_lang(user.id):
        # Yangi foydalanuvchi — avval til tanlaydi
        await message.answer(t("choose_lang", lang), reply_markup=kb.lang_kb())
        return
    await send_welcome(message, user.first_name, user.id, lang)


@router.message(F.text.in_(all_texts("btn_lang")))
async def choose_lang(message: Message, lang: str):
    await message.answer(t("choose_lang", lang), reply_markup=kb.lang_kb())


@router.callback_query(F.data.startswith("setlang:"))
async def set_lang(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split(":")[1]
    if lang not in LANGS:
        await callback.answer()
        return
    await state.clear()
    user = callback.from_user
    await db.add_user(user.id, user.full_name, user.username)
    await db.set_user_lang(user.id, lang)
    remember_lang(user.id, lang)
    try:
        await callback.message.edit_text(t("lang_set", lang))
    except Exception:
        pass
    await send_welcome(callback.message, user.first_name, user.id, lang)
    await callback.answer()


@router.message(F.text.in_(all_texts("btn_cancel")))
async def cancel(message: Message, state: FSMContext, lang: str):
    await state.clear()
    await message.answer(t("cancelled", lang), reply_markup=kb.main_menu(lang, is_admin(message.from_user.id)))


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
