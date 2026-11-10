"""Har qanday holatda ishlaydigan umumiy handlerlar."""
from html import escape

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import db
from config import is_admin
from keyboards import BTN_CANCEL, main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    await db.add_user(user.id, user.full_name, user.username)
    await message.answer(
        f"Assalomu alaykum, <b>{escape(user.first_name)}</b>! 👋\n\n"
        "Do'konimizga xush kelibsiz. Quyidagi menyudan kerakli bo'limni tanlang.",
        reply_markup=main_menu(is_admin(user.id)),
    )


@router.message(F.text == BTN_CANCEL)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu(is_admin(message.from_user.id)))


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
