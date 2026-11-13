"""Admin panel: aksiya, kategoriya/mahsulot boshqaruvi, buyurtmalar, statistika, xabar yuborish.

Admin panel o'zbek tilida. Mijozlarga boradigan xabarlar esa har birining o'z tilida yuboriladi.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import BaseFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

import colors as color_mod
import db
import keyboards as kb
import courier
import pricing
import translate
from config import (
    fmt_phone,
    ADMIN_IDS, BONUS_VALUE, MAX_WEB_MEDIA_BYTES, PAYMENT_NAMES, SHOP_NAME, WEBAPP_URL, TIMEZONE, fmt_price, is_admin, is_owner, is_test_token, now,
    payment_providers,
)
from i18n import DEFAULT_LANG, LANG_NAMES, all_texts, t
from states import AddCategory, AddProduct, AdminForm, Broadcast, EditColors, EditProduct, PromoForm

log = logging.getLogger(__name__)

MULTILANG_HINT = (
    "\n\n🌐 <i>O'zbekcha yozing — bot rus, tojik va qozoq tillariga avtomatik tarjima qiladi.</i>\n"
    "<i>Tarjimani o'zingiz bermoqchi bo'lsangiz, «|» bilan ajrating (o'zbek | rus | tojik | qozoq):</i>\n"
    "<code>{example}</code>"
)


async def translate_input(message: Message, text: str) -> tuple[str, str | None, str]:
    """Admin matnini tarjima qiladi; tarjima vaqtida «⏳» xabarini ko'rsatadi."""
    waiting = None
    if "|" not in text and translate.AUTO_TRANSLATE:
        waiting = await message.answer("⏳ Tarjima qilinmoqda...")
    try:
        return await translate.auto_i18n(text)
    finally:
        if waiting:
            try:
                await message.bot.delete_message(waiting.chat.id, waiting.message_id)
            except Exception:  # yordamchi xabar — o'chmasa ham ish davom etadi
                pass


class IsAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        return event.from_user is not None and is_admin(event.from_user.id)


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def edit(callback: CallbackQuery, text: str, markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


async def back_to_panel(message: Message, lang: str, text: str):
    await message.answer(text, reply_markup=kb.main_menu(lang, True))
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu_kb())


def is_skip(text: str | None) -> bool:
    return text in all_texts("btn_skip")


async def send_safely(coro_factory) -> bool:
    """Xabar yuborish; Telegram limiti bo'lsa kutib, qayta urinadi."""
    try:
        await coro_factory()
        return True
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        try:
            await coro_factory()
            return True
        except Exception:
            return False
    except Exception:
        return False


# ---------------- Menyu ----------------
@router.message(Command("admin"))
@router.message(F.text == kb.BTN_ADMIN)
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⚙️ <b>Admin panel</b>", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await edit(callback, "⚙️ <b>Admin panel</b>", kb.admin_menu_kb())


# ================= AKSIYA =================
def promo_admin_text(promo: dict | None, category: dict | None) -> str:
    if not promo:
        return "🔥 <b>Aksiya</b>\n\nHozir aksiya yo'q. «➕ Yangi aksiya» tugmasini bosing."
    if pricing.is_running(promo):
        state = "🟢 Faol"
    elif pricing.is_upcoming(promo):
        state = "🟡 Hali boshlanmagan"
    else:
        state = "🔴 Tugagan"
    scope = f"«{escape(category['name'])}» kategoriyasi" if category else "Barcha mahsulotlar"
    return (
        "🔥 <b>Aksiya</b>\n\n"
        f"Holati: {state}\n"
        f"Chegirma: <b>{promo['percent']}%</b>\n"
        f"Qamrov: {scope}\n"
        f"Boshlanishi: {promo['_start']:%d.%m.%Y %H:%M}\n"
        f"Tugashi: {promo['_end']:%d.%m.%Y %H:%M}\n"
        f"Vaqt mintaqasi: {TIMEZONE.key}"
    )


async def _promo_and_category():
    promo = await db.get_promo()
    category = await db.get_category(promo["category_id"]) if promo and promo.get("category_id") else None
    return promo, category


@router.callback_query(F.data == "adm:promo")
async def cb_promo(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    promo, category = await _promo_and_category()
    await edit(callback, promo_admin_text(promo, category), kb.admin_promo_kb(promo is not None))


@router.callback_query(F.data == "pr:new")
async def cb_promo_new(callback: CallbackQuery, state: FSMContext):
    await state.set_state(PromoForm.percent)
    await callback.message.answer(
        "1/3. Chegirma foizini tanlang yoki yozing (1 dan 90 gacha):", reply_markup=kb.promo_percent_kb()
    )
    await callback.answer()


@router.message(PromoForm.percent, F.text)
async def promo_percent(message: Message, state: FSMContext):
    raw = message.text.replace("%", "").strip()
    if not raw.isdigit() or not 1 <= int(raw) <= 90:
        await message.answer("❗️ 1 dan 90 gacha butun son kiriting. Masalan: 11")
        return
    await state.update_data(percent=int(raw))
    await state.set_state(None)
    categories = await db.get_categories()
    await message.answer(f"✅ Chegirma: {raw}%", reply_markup=kb.main_menu(DEFAULT_LANG, True))
    await message.answer("2/3. Aksiya qaysi mahsulotlarga amal qiladi?", reply_markup=kb.promo_scope_kb(categories))


@router.callback_query(F.data.startswith("psc:"))
async def cb_promo_scope(callback: CallbackQuery, state: FSMContext):
    value = callback.data.split(":")[1]
    if "percent" not in await state.get_data():
        await callback.answer("Qaytadan boshlang: 🔥 Aksiya → ➕ Yangi aksiya", show_alert=True)
        return
    await state.update_data(category_id=None if value == "all" else int(value))
    await edit(callback, "3/3. Aksiya muddatini tanlang:", kb.promo_period_kb())


def nov11_bounds() -> tuple[datetime, datetime]:
    """Eng yaqin 11-noyabr kuni: 00:00 dan 23:59:59 gacha (bot vaqt mintaqasida)."""
    current = now()
    year = current.year
    if current >= datetime(year, 11, 12, tzinfo=TIMEZONE):
        year += 1
    start = datetime(year, 11, 11, tzinfo=TIMEZONE)
    return start, start + timedelta(days=1)


async def _save_promo(event_message: Message, state: FSMContext, start: datetime, end: datetime, kind: str):
    data = await state.get_data()
    await state.clear()
    await db.set_promo(pricing.dump(data["percent"], start, end, data.get("category_id"), kind))
    promo, category = await _promo_and_category()
    await event_message.answer(
        "✅ <b>Aksiya saqlandi!</b>\n\n" + promo_admin_text(promo, category)
        + "\n\nEndi mijozlarga e'lon qilishingiz mumkin 👇",
        reply_markup=kb.admin_promo_kb(True),
    )


@router.callback_query(F.data.startswith("pp:"))
async def cb_promo_period(callback: CallbackQuery, state: FSMContext):
    choice = callback.data.split(":")[1]
    if "percent" not in await state.get_data():
        await callback.answer("Qaytadan boshlang: 🔥 Aksiya → ➕ Yangi aksiya", show_alert=True)
        return
    if choice == "custom":
        await state.set_state(PromoForm.custom_period)
        await callback.message.answer(
            "Muddatni quyidagi ko'rinishda yozing:\n"
            "<code>10.11.2026 18:00 - 12.11.2026 23:59</code>",
            reply_markup=kb.cancel_kb(DEFAULT_LANG),
        )
        await callback.answer()
        return
    start, end = nov11_bounds()
    if choice == "now":
        start = min(start, now())
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.answer()
    await _save_promo(callback.message, state, start, end, "1111")


@router.message(PromoForm.custom_period, F.text)
async def promo_custom_period(message: Message, state: FSMContext):
    try:
        left, right = [part.strip() for part in message.text.split(" - ")]
        start = datetime.strptime(left, "%d.%m.%Y %H:%M").replace(tzinfo=TIMEZONE)
        end = datetime.strptime(right, "%d.%m.%Y %H:%M").replace(tzinfo=TIMEZONE)
    except ValueError:
        await message.answer("❗️ Format noto'g'ri. Masalan:\n<code>10.11.2026 18:00 - 12.11.2026 23:59</code>")
        return
    if end <= start or end <= now():
        await message.answer("❗️ Tugash vaqti boshlanishidan keyin va kelajakda bo'lishi kerak.")
        return
    await message.answer("✅ Muddat qabul qilindi.", reply_markup=kb.main_menu(DEFAULT_LANG, True))
    is_1111 = start.month == 11 and start.day <= 11 <= end.day and end.month == 11
    await _save_promo(message, state, start, end, "1111" if is_1111 else "custom")


@router.callback_query(F.data == "pr:stop")
async def cb_promo_stop(callback: CallbackQuery):
    await db.set_promo(None)
    await callback.answer("⛔️ Aksiya to'xtatildi. Narxlar asl holiga qaytdi.", show_alert=True)
    await edit(callback, promo_admin_text(None, None), kb.admin_promo_kb(False))


@router.callback_query(F.data == "pr:preview")
async def cb_promo_preview(callback: CallbackQuery):
    promo, category = await _promo_and_category()
    if not promo:
        await callback.answer("Aksiya yo'q", show_alert=True)
        return
    for code, name in LANG_NAMES.items():
        banner = kb.promo_banner(promo, code, category, footer=True)
        if banner:
            await callback.message.answer(f"<i>{name}:</i>\n\n{banner}", reply_markup=kb.shop_now_kb(code))
    await callback.answer()


@router.callback_query(F.data == "pr:announce")
async def cb_promo_announce(callback: CallbackQuery):
    promo, category = await _promo_and_category()
    if not promo or pricing.is_finished(promo):
        await callback.answer("Faol yoki rejalashtirilgan aksiya yo'q", show_alert=True)
        return
    users = await db.get_users_with_lang()
    await callback.answer()
    await callback.message.answer(f"⏳ {len(users)} ta mijozga e'lon yuborilmoqda (har biriga o'z tilida)...")
    ok = fail = 0
    for u in users:
        lang = u["lang"] or DEFAULT_LANG
        text = kb.promo_banner(promo, lang, category, footer=True)
        sent = await send_safely(
            lambda: callback.bot.send_message(u["id"], text, reply_markup=kb.shop_now_kb(lang))
        )
        ok, fail = (ok + 1, fail) if sent else (ok, fail + 1)
        await asyncio.sleep(0.05)  # Telegram limitlaridan oshmaslik uchun
    await callback.message.answer(f"✅ E'lon yuborildi: {ok}\n❌ Yuborilmadi (botni bloklagan): {fail}")


# ================= ADMINLAR =================
async def admins_view(viewer_id: int):
    admins = await db.get_admins()
    lines = ["👥 <b>Adminlar</b>\n", "<b>Bosh admin(lar)</b> — Railway'dagi ADMIN_IDS:"]
    for owner_id in ADMIN_IDS:
        user = await db.get_user(owner_id)
        name = escape(user["full_name"]) if user and user.get("full_name") else "—"
        lines.append(f"    👑 {name} (<code>{owner_id}</code>)")
    lines.append("\n<b>Qo'shilgan adminlar:</b>")
    if admins:
        for a in admins:
            lines.append(f"    👤 {escape(a['full_name'] or '—')} (<code>{a['id']}</code>) • {a['created_at']}")
    else:
        lines.append("    hali yo'q")
    can_manage = is_owner(viewer_id)
    if not can_manage:
        lines.append("\n<i>Adminlarni faqat bosh admin qo'sha oladi.</i>")
    else:
        lines.append(
            "\n<i>Adminlar buyurtmalarni oladi, mahsulot va aksiyalarni boshqara oladi. "
            "O'chirish uchun ismi ustiga bosing.</i>"
        )
    return "\n".join(lines), kb.admins_kb(admins, can_manage)


@router.callback_query(F.data == "adm:admins")
async def cb_admins(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, markup = await admins_view(callback.from_user.id)
    await edit(callback, text, markup)


@router.callback_query(F.data == "ad_add")
async def cb_admin_add(callback: CallbackQuery, state: FSMContext):
    if not is_owner(callback.from_user.id):
        await callback.answer("Faqat bosh admin admin qo'sha oladi", show_alert=True)
        return
    await state.set_state(AdminForm.user)
    await callback.message.answer(
        "Yangi adminni tanlang:\n\n"
        "👇 «👤 Kontaktlardan tanlash» tugmasini bosing va kontaktlaringizdan odamni tanlang.\n\n"
        "<i>Yoki uning Telegram ID raqamini yozing (uni @userinfobot orqali bilish mumkin).</i>",
        reply_markup=kb.pick_admin_kb(),
    )
    await callback.answer()


async def _make_admin(message: Message, state: FSMContext, lang: str, user_id: int, name: str | None):
    await state.clear()
    if is_admin(user_id):
        await back_to_panel(message, lang, "ℹ️ Bu odam allaqachon admin.")
        return
    known = await db.get_user(user_id)
    name = name or (known["full_name"] if known else None) or str(user_id)
    await db.add_admin(user_id, name, message.from_user.id)
    new_lang = (known or {}).get("lang") or DEFAULT_LANG
    try:
        await message.bot.send_message(
            user_id, t("admin_appointed", new_lang, shop=escape(SHOP_NAME)),
            reply_markup=kb.main_menu(new_lang, True),
        )
        note = "U xabardor qilindi ✉️"
    except Exception:
        me = await message.bot.me()
        note = (
            "⚠️ U hali botga /start bosmagan, shuning uchun xabar yuborilmadi.\n"
            f"Unga bot havolasini yuboring: https://t.me/{me.username} — /start bosgach, "
            "«⚙️ Admin panel» tugmasi chiqadi."
        )
    await back_to_panel(message, lang, f"✅ <b>{escape(name)}</b> admin qilib qo'shildi!\n{note}")


@router.message(AdminForm.user, F.users_shared)
async def admin_add_shared(message: Message, state: FSMContext, lang: str):
    shared = message.users_shared.users[0]
    name = " ".join(x for x in [shared.first_name, shared.last_name] if x) or shared.username
    await _make_admin(message, state, lang, shared.user_id, name)


@router.message(AdminForm.user, F.text.regexp(r"^\s*\d{5,15}\s*$"))
async def admin_add_by_id(message: Message, state: FSMContext, lang: str):
    await _make_admin(message, state, lang, int(message.text.strip()), None)


@router.message(AdminForm.user)
async def admin_add_invalid(message: Message):
    await message.answer("«👤 Kontaktlardan tanlash» tugmasini bosing yoki ID raqamni yozing (faqat raqamlar).")


@router.callback_query(F.data.startswith("ad_rm:"))
async def cb_admin_remove(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("Faqat bosh admin adminlarni o'chira oladi", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await db.remove_admin(user_id)
    await callback.answer("🗑 Admin o'chirildi", show_alert=True)
    text, markup = await admins_view(callback.from_user.id)
    await edit(callback, text, markup)


# ================= KATEGORIYALAR =================
@router.callback_query(F.data == "adm:add_cat")
async def cb_add_category(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddCategory.name)
    await callback.message.answer(
        "Yangi kategoriya nomini kiriting:"
        + MULTILANG_HINT.format(example="🎀 Bolalar uchun | 🎀 Детское | 🎀 Барои кӯдакон | 🎀 Балаларға"),
        reply_markup=kb.cancel_kb(DEFAULT_LANG),
    )
    await callback.answer()


@router.message(AddCategory.name, F.text)
async def add_category_name(message: Message, state: FSMContext, lang: str):
    name, name_i18n, status = await translate_input(message, message.text.strip()[:200])
    await db.add_category(name[:64], name_i18n)
    await state.clear()
    await back_to_panel(message, lang, f"✅ «{escape(name)}» kategoriyasi qo'shildi." + translate.preview(name_i18n, status))


@router.callback_query(F.data == "adm:del_cat")
async def cb_del_category(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Kategoriyalar yo'q", show_alert=True)
        return
    await edit(
        callback,
        "Qaysi kategoriyani o'chirasiz?\n⚠️ Undagi barcha mahsulotlar ham o'chiriladi.",
        kb.categories_kb(categories, prefix="dc"),
    )


@router.callback_query(F.data.startswith("dc:"))
async def cb_del_category_do(callback: CallbackQuery):
    category_id = int(callback.data.split(":")[1])
    category = await db.get_category(category_id)
    if category:
        await db.delete_category(category_id)
        await callback.answer(f"🗑 «{category['name']}» o'chirildi", show_alert=True)
    await edit(callback, "⚙️ <b>Admin panel</b>", kb.admin_menu_kb())


# ================= MAHSULOTLAR =================
@router.callback_query(F.data == "adm:add_prod")
async def cb_add_product(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Avval kategoriya qo'shing!", show_alert=True)
        return
    await edit(callback, "Mahsulot qaysi kategoriyaga qo'shilsin?", kb.categories_kb(categories, prefix="apc"))


@router.callback_query(F.data.startswith("apc:"))
async def cb_add_product_category(callback: CallbackQuery, state: FSMContext):
    await state.update_data(category_id=int(callback.data.split(":")[1]))
    await state.set_state(AddProduct.name)
    await callback.message.answer(
        "Mahsulot nomini kiriting:"
        + MULTILANG_HINT.format(example="Oltin uzuk | Золотое кольцо | Ангуштарини тиллоӣ | Алтын сақина"),
        reply_markup=kb.cancel_kb(DEFAULT_LANG),
    )
    await callback.answer()


@router.message(AddProduct.name, F.text)
async def add_product_name(message: Message, state: FSMContext):
    name, name_i18n, status = await translate_input(message, message.text.strip()[:400])
    await state.update_data(name=name[:100], name_i18n=name_i18n)
    await state.set_state(AddProduct.description)
    await message.answer(
        f"✅ Nomi: <b>{escape(name)}</b>" + translate.preview(name_i18n, status) + "\n\n"
        "Mahsulot tavsifini kiriting (material, proba, tosh, vazn va h.k.)."
        + MULTILANG_HINT.format(
            example="585 proba, 2.1 g | 585 проба, 2,1 г | Пробаи 585, 2,1 г | 585 сынама, 2,1 г"
        ),
        reply_markup=kb.skip_cancel_kb(DEFAULT_LANG),
    )


@router.message(AddProduct.description, F.text)
async def add_product_description(message: Message, state: FSMContext):
    if is_skip(message.text):
        description, description_i18n = None, None
    else:
        description, description_i18n, status = await translate_input(message, message.text.strip()[:3000])
        description = description[:900]
    await state.update_data(description=description, description_i18n=description_i18n)
    await state.set_state(AddProduct.price)
    await message.answer(
        (("✅ Tavsif saqlandi." + translate.preview(description_i18n, status) + "\n\n") if description else "")
        + "Narxini kiriting (faqat raqam, so'mda). Masalan: 25000\n"
        "<i>Aksiya bo'lsa, chegirma avtomatik hisoblanadi — bu yerga asl narxni yozing.</i>",
        reply_markup=kb.cancel_kb(DEFAULT_LANG),
    )


@router.message(AddProduct.price, F.text)
async def add_product_price(message: Message, state: FSMContext):
    raw = message.text.replace(" ", "").replace(",", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("❗️ Narx musbat butun son bo'lishi kerak. Masalan: 25000")
        return
    await state.update_data(price=int(raw))
    await state.set_state(AddProduct.stock)
    await message.answer(STOCK_PROMPT, reply_markup=kb.skip_cancel_kb(DEFAULT_LANG))


STOCK_PROMPT = (
    "📦 Vitrinada <b>nechta bor</b>? Sonini yozing, masalan <code>5</code>.\n"
    "<i>Mijozlar «📦 Mavjud: 5 dona» ni ko'radi; buyurtma qilinganda soni avtomatik kamayadi, "
    "tugasa — «❌ Tugagan» bo'ladi.</i>\n\n"
    "Sonini hisoblamaslik uchun «O'tkazib yuborish» ni bosing."
)


def parse_stock(text: str) -> int | None | bool:
    """Son -> int; «O'tkazib yuborish» -> None (hisoblanmaydi); noto'g'ri -> False."""
    if is_skip(text):
        return None
    raw = text.replace(" ", "")
    if not raw.isdigit() or int(raw) > 100000:
        return False
    return int(raw)


def stock_label(stock: int | None) -> str:
    if stock is None:
        return "hisoblanmaydi"
    return "❌ tugagan (0)" if stock <= 0 else f"{stock} ta"


@router.message(AddProduct.stock, F.text)
async def add_product_stock(message: Message, state: FSMContext):
    stock = parse_stock(message.text)
    if stock is False:
        await message.answer("❗️ Son kiriting (0 yoki undan katta), masalan: 5")
        return
    await state.update_data(stock=stock)
    await state.set_state(AddProduct.sizes)
    await message.answer(
        f"✅ Soni: {stock_label(stock)}\n\n"
        "📏 Mahsulot o'lchamlarini vergul bilan kiriting.\n"
        "Masalan, uzuk uchun: <code>16, 16.5, 17, 17.5, 18, 18.5</code>\n"
        "Zanjir uchun: <code>40, 45, 50</code>\n\n"
        "O'lcham kerak bo'lmasa (sirg'a, kulon va h.k.) — «O'tkazib yuborish» ni bosing.",
        reply_markup=kb.skip_cancel_kb(DEFAULT_LANG),
    )


@router.message(AddProduct.sizes, F.text)
async def add_product_sizes(message: Message, state: FSMContext):
    sizes = []
    if not is_skip(message.text):
        for raw in message.text.replace(";", ",").split(","):
            size = raw.strip().replace(":", "")
            if size and size not in sizes:
                sizes.append(size)
        if not sizes or len(sizes) > 20 or any(len(x) > 8 for x in sizes):
            await message.answer(
                "❗️ Noto'g'ri format. O'lchamlarni vergul bilan yozing (ko'pi bilan 20 ta, "
                "har biri 8 belgigacha). Masalan: 16, 16.5, 17"
            )
            return
    await state.update_data(sizes=sizes, colors=[])
    await state.set_state(AddProduct.colors)
    await message.answer(COLORS_HELP, reply_markup=kb.skip_cancel_kb(DEFAULT_LANG))
    await message.answer("🎨 Ranglar:", reply_markup=kb.colors_select_kb([], "pc"))


COLORS_HELP = (
    "🎨 Mahsulot <b>ranglarini</b> belgilang (bir nechtasini tanlash mumkin), so'ng «✔️ Tayyor» ni bosing.\n\n"
    "Ro'yxatda yo'q rangni o'zbekcha yozib yuboring (vergul bilan bir nechta), masalan <code>Yashil</code> — "
    "bot uni boshqa tillarga o'zi tarjima qiladi.\n\n"
    "Rang kerak bo'lmasa — «O'tkazib yuborish»."
)


def _toggle_color(colors: list[str], callback_data: str) -> list[str]:
    """«pc:yg» — tayyor rangni yoqish/o'chirish; «pcx:2» — maxsus rangni olib tashlash."""
    key, value = callback_data.split(":", 1)
    colors = list(colors)
    if key.endswith("x"):
        if value.isdigit() and int(value) < len(colors):
            colors.pop(int(value))
    elif value in colors:
        colors.remove(value)
    elif len(colors) < color_mod.MAX_COLORS:
        colors.append(value)
    return colors


@router.callback_query(AddProduct.colors, F.data.startswith("pc:") | F.data.startswith("pcx:"))
async def cb_add_product_color(callback: CallbackQuery, state: FSMContext):
    colors = _toggle_color((await state.get_data()).get("colors", []), callback.data)
    await state.update_data(colors=colors)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb.colors_select_kb(colors, "pc"))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(AddProduct.colors, F.text)
async def add_product_colors_text(message: Message, state: FSMContext):
    if is_skip(message.text):
        await state.update_data(colors=[])
        await _ask_product_photo(message, state)
        return
    colors = (await state.get_data()).get("colors", [])
    for custom in color_mod.parse_custom(message.text):
        custom = await translate.auto_color(custom)
        if custom not in colors and len(colors) < color_mod.MAX_COLORS:
            colors.append(custom)
    await state.update_data(colors=colors)
    await message.answer("🎨 Ranglar:", reply_markup=kb.colors_select_kb(colors, "pc"))


@router.callback_query(AddProduct.colors, F.data == "pc_done")
async def cb_add_product_colors_done(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.answer()
    await _ask_product_photo(callback.message, state)


async def _ask_product_photo(message: Message, state: FSMContext):
    colors = (await state.get_data()).get("colors", [])
    if colors:
        await message.answer("✅ Ranglar: " + escape(", ".join(color_mod.label(c, "uz") for c in colors)))
    await state.set_state(AddProduct.photo)
    await state.update_data(photos=[], photo_items=None, photo_seq=0, photo_limit_warned=False)
    await message.answer(PHOTOS_HELP, reply_markup=photos_kb())


HAS, HAS_NOT = "bor ✅", "yo'q"
VIDEO_TOO_BIG = (
    "\n⚠️ Video hajmi 20 MB dan katta — botda ko'rinadi, lekin saytda ko'rinmaydi. "
    "Saytda ham chiqishi uchun qisqaroq (20 MB gacha) video yuboring."
)


def _video_from(message: Message) -> tuple[str, int] | None:
    """Xabardagi video (oddiy video yoki video-fayl) — (file_id, hajm)."""
    if message.video:
        return message.video.file_id, message.video.file_size or 0
    if message.document and (message.document.mime_type or "").startswith("video/"):
        return message.document.file_id, message.document.file_size or 0
    return None


# ---------------- Rasmlarni yig'ish (bir nechta / albom) ----------------
BTN_DONE = "✔️ Tayyor"
PHOTOS_HELP = (
    f"📸 Mahsulot <b>rasmlarini</b> yuboring — 1 tadan {db.MAX_PHOTOS} tagacha (albom qilib birdaniga ham bo'ladi).\n"
    "Birinchi rasm — asosiy rasm bo'ladi.\n\n"
    f"Hammasini yuborgach «{BTN_DONE}» ni bosing."
)
PHOTO_DEBOUNCE = 1.0  # albomdagi rasmlar kelib bo'lgach bitta xabar yuborish uchun kutish (soniya)
_photo_locks: dict[int, asyncio.Lock] = {}


def photos_kb() -> kb.ReplyKeyboardMarkup:
    return kb.ReplyKeyboardMarkup(
        keyboard=[[kb.KeyboardButton(text=BTN_DONE)], [kb.KeyboardButton(text=t("btn_skip", DEFAULT_LANG))],
                  [kb.KeyboardButton(text=t("btn_cancel", DEFAULT_LANG))]],
        resize_keyboard=True,
    )


async def collect_photo(message: Message, state: FSMContext):
    """Rasmni holatga qo'shadi. Albom rasmlari bir vaqtda kelgani uchun qulf ishlatiladi,
    javob esa oxirgi rasmdan keyin bir marta yuboriladi."""
    lock = _photo_locks.setdefault(message.from_user.id, asyncio.Lock())
    async with lock:
        data = await state.get_data()
        # [tartib, file_id]: avvaldan bor rasmlar manfiy tartib bilan oldinda turadi, yangilari — xabar raqami bo'yicha
        # (albom rasmlari bir vaqtda qayta ishlanadi, shuning uchun kelish tartibiga emas, message_id ga tayanamiz)
        items = data.get("photo_items")
        if items is None:
            items = [[i - len(data.get("photos", [])), f] for i, f in enumerate(data.get("photos", []))]
        if len(items) >= db.MAX_PHOTOS:
            if not data.get("photo_limit_warned"):
                await state.update_data(photo_limit_warned=True)
                await message.answer(f"❗️ Ko'pi bilan {db.MAX_PHOTOS} ta rasm. «{BTN_DONE}» ni bosing.")
            return
        items.append([message.message_id, message.photo[-1].file_id])
        items.sort(key=lambda item: item[0])
        photos = [f for _, f in items]
        seq = data.get("photo_seq", 0) + 1
        current_state = await state.get_state()
        await state.update_data(photos=photos, photo_items=items, photo_seq=seq)
    if PHOTO_DEBOUNCE:
        await asyncio.sleep(PHOTO_DEBOUNCE)
    data = await state.get_data()
    if data.get("photo_seq") == seq and await state.get_state() == current_state:
        await message.answer(
            f"🖼 {len(data.get('photos', []))} ta rasm qabul qilindi. Yana yuboring yoki «{BTN_DONE}» ni bosing.",
            reply_markup=photos_kb(),
        )


@router.message(AddProduct.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext):
    await collect_photo(message, state)


@router.message(AddProduct.photo, F.text.in_({BTN_DONE, *all_texts("btn_skip")}))
async def add_product_photos_done(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.text == BTN_DONE and not data.get("photos"):
        await message.answer("Hali rasm yuborilmadi. Rasm yuboring yoki «O'tkazib yuborish» ni bosing.")
        return
    if is_skip(message.text):
        await state.update_data(photos=[])
    await state.set_state(AddProduct.video)
    await message.answer(
        "🎬 Mahsulot videosini yuboring (ixtiyoriy).\n"
        "<i>Video mahsulotni har tomondan ko'rsatsa — mijozlar ko'proq ishonadi. "
        "Saytda ko'rinishi uchun 20 MB gacha bo'lsin.</i>",
        reply_markup=kb.skip_cancel_kb(DEFAULT_LANG),
    )


@router.message(AddProduct.photo)
async def add_product_photo_invalid(message: Message):
    await message.answer(f"Iltimos, rasm yuboring, «{BTN_DONE}» yoki «O'tkazib yuborish» tugmasini bosing.")


@router.message(AddProduct.video, F.video | F.document | F.text.in_(all_texts("btn_skip")))
async def add_product_video(message: Message, state: FSMContext, lang: str):
    video = _video_from(message)
    if not video and not is_skip(message.text):
        await message.answer("Iltimos, video yuboring yoki «O'tkazib yuborish» tugmasini bosing.")
        return
    video_id, video_size = video or (None, None)
    data = await state.get_data()
    photos = data.get("photos") or []
    await state.clear()
    if not await db.get_category(data["category_id"]):
        await message.answer("❗️ Kategoriya o'chirilgan. Qaytadan urinib ko'ring.", reply_markup=kb.main_menu(lang, True))
        return
    sizes = data.get("sizes") or []
    await db.add_product(
        data["category_id"], data["name"], data["description"], data["price"], None, sizes,
        data.get("name_i18n"), data.get("description_i18n"), video_id, video_size,
        color_mod.dump(data.get("colors") or []), photos, data.get("stock"),
    )
    info = f"✅ Mahsulot qo'shildi: <b>{escape(data['name'])}</b> — {fmt_price(data['price'])}"
    info += f"\n📦 Soni: {stock_label(data.get('stock'))}"
    if photos:
        info += f"\n🖼 Rasmlar: {len(photos)} ta"
    if video_id:
        info += "\n🎬 Video qo'shildi" + (VIDEO_TOO_BIG if video_size and video_size > MAX_WEB_MEDIA_BYTES else "")
    if sizes:
        info += f"\n📏 O'lchamlar: {escape(', '.join(sizes))}"
    if data.get("colors"):
        info += f"\n🎨 Ranglar: {escape(', '.join(color_mod.name(c, 'uz') for c in data['colors']))}"
    if data.get("name_i18n"):
        info += "\n🌐 Tarjimalar saqlandi"
    await back_to_panel(message, lang, info)


@router.message(AddProduct.video)
async def add_product_video_invalid(message: Message):
    await message.answer("Iltimos, video yuboring yoki «O'tkazib yuborish» tugmasini bosing.")


# ================= MAHSULOTNI TAHRIRLASH =================
TR_FLAGS = {code: name.split()[0] for code, name in LANG_NAMES.items()}


def parse_sizes(text: str) -> list[str] | None:
    """«16, 16.5, 17» -> ["16", "16.5", "17"]; noto'g'ri bo'lsa None."""
    sizes = []
    for raw in text.replace(";", ",").split(","):
        size = raw.strip().replace(":", "")
        if size and size not in sizes:
            sizes.append(size)
    if not sizes or len(sizes) > 20 or any(len(x) > 8 for x in sizes):
        return None
    return sizes


def _translations_lines(raw: str | None) -> str:
    if not raw:
        return ""
    try:
        data = json.loads(raw)
    except ValueError:
        return ""
    return "".join(f"\n      {TR_FLAGS[c]} {escape(data[c])}" for c in ("ru", "tg", "kk") if data.get(c))


async def product_edit_view(product_id: int):
    p = await db.get_product(product_id)
    if not p:
        return None, None
    category = await db.get_category(p["category_id"])
    sizes = db.product_sizes(p)
    colors = color_mod.product_colors(p)
    photos = db.product_photos(p)
    desc = p.get("description") or ""
    text = (
        f"✏️ <b>Mahsulotni tahrirlash</b> (#{p['id']})\n\n"
        f"📂 Kategoriya: {escape(category['name']) if category else '—'}\n"
        f"🏷 Nomi: <b>{escape(p['name'])}</b>{_translations_lines(p.get('name_i18n'))}\n"
        f"📝 Tavsif: {escape(desc[:200]) + ('…' if len(desc) > 200 else '') if desc else HAS_NOT}"
        f"{_translations_lines(p.get('description_i18n')) if desc else ''}\n"
        f"💰 Narx: <b>{fmt_price(p['price'])}</b>\n"
        f"📦 Soni: <b>{stock_label(db.product_stock(p))}</b>\n"
        f"📏 O'lchamlar: {escape(', '.join(sizes)) or HAS_NOT}\n"
        f"🎨 Ranglar: {escape(', '.join(color_mod.name(c, 'uz') for c in colors)) or HAS_NOT}\n"
        f"🖼 Rasmlar: {len(photos)} ta\n"
        f"🎬 Video: {HAS if p.get('video_id') else HAS_NOT}"
    )
    pid = p["id"]
    b = kb.InlineKeyboardBuilder()
    b.button(text="✏️ Nomi", callback_data=f"pe:n:{pid}")
    b.button(text="📝 Tavsif", callback_data=f"pe:d:{pid}")
    b.button(text="💰 Narx", callback_data=f"pe:p:{pid}")
    b.button(text="📦 Soni", callback_data=f"pe:q:{pid}")
    b.button(text="📏 O'lchamlar", callback_data=f"pe:s:{pid}")
    b.button(text="🎨 Ranglar", callback_data=f"ecs:{pid}")
    b.button(text="📂 Kategoriya", callback_data=f"pe:c:{pid}")
    b.button(text="🖼 Rasmlar", callback_data=f"pe:ph:{pid}")
    b.button(text="🎬 Video", callback_data=f"pe:v:{pid}")
    b.button(text="🌐 Tarjimani tuzatish", callback_data=f"pe:t:{pid}")
    b.button(text="👁 Mijoz ko'rinishi", callback_data=f"prod:{pid}")
    b.button(text="🗑 O'chirish", callback_data=f"dp:{pid}")
    b.button(text="⬅️ Orqaga", callback_data=f"mdc:{p['category_id']}")
    b.adjust(2, 2, 1, 2, 2, 1, 2, 1)
    return text, b.as_markup()


async def send_edit_view(message: Message, product_id: int, notice: str = ""):
    text, markup = await product_edit_view(product_id)
    if text:
        await message.answer((notice + "\n\n" if notice else "") + text, reply_markup=markup)


@router.callback_query(F.data == "adm:media")
@router.callback_query(F.data == "adm:edit")
async def cb_edit_choose_category(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Kategoriyalar yo'q", show_alert=True)
        return
    await edit(callback, "✏️ Qaysi kategoriyadagi mahsulotni tahrirlaysiz?", kb.categories_kb(categories, prefix="mdc"))


@router.callback_query(F.data.startswith("mdc:"))
async def cb_edit_choose_product(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    products = await db.get_products(int(callback.data.split(":")[1]))
    if not products:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return
    markup = kb.InlineKeyboardBuilder()
    for p in products:
        n = len(db.product_photos(p))
        icons = (f"🖼{n}" if n else "") + (" 🎬" if p.get("video_id") else "")
        stock = db.product_stock(p)
        if stock is not None:
            icons += " ❌0" if stock <= 0 else f" 📦{stock}"
        markup.button(text=f"{p['name']} — {fmt_price(p['price'])} {icons}".strip(), callback_data=f"mdp:{p['id']}")
    markup.button(text="⬅️ Admin panel", callback_data="adm:menu")
    markup.adjust(1)
    await edit(callback, "Mahsulotni tanlang:", markup.as_markup())


@router.callback_query(F.data.startswith("mdp:"))
async def cb_edit_product(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    text, markup = await product_edit_view(int(callback.data.split(":")[1]))
    if not text:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await edit(callback, text, markup)


EDIT_PROMPTS = {
    "n": "✏️ Yangi <b>nomni</b> yozing (o'zbekcha — boshqa tillarga avtomatik tarjima qilinadi):",
    "d": "📝 Yangi <b>tavsifni</b> yozing (o'zbekcha — avtomatik tarjima qilinadi).\nTavsifni o'chirish uchun «O'tkazib yuborish» ni bosing:",
    "p": "💰 Yangi <b>narxni</b> yozing (faqat raqam, so'mda). Masalan: 1500000",
    "q": STOCK_PROMPT.replace("Vitrinada <b>nechta bor</b>?", "Hozir vitrinada <b>nechta bor</b>?"),
    "s": "📏 Yangi <b>o'lchamlarni</b> vergul bilan yozing, masalan <code>16, 16.5, 17</code>.\n"
         "O'lchamlarni o'chirish uchun «O'tkazib yuborish» ni bosing:",
}


@router.callback_query(F.data.startswith("pe:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext):
    _, field, pid = callback.data.split(":")
    product = await db.get_product(int(pid))
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await callback.answer()
    if field in EDIT_PROMPTS:
        await state.set_state(EditProduct.text)
        await state.update_data(edit_product_id=product["id"], edit_field=field)
        markup = kb.skip_cancel_kb(DEFAULT_LANG) if field in ("d", "s", "q") else kb.cancel_kb(DEFAULT_LANG)
        await callback.message.answer(EDIT_PROMPTS[field], reply_markup=markup)
    elif field == "c":
        categories = await db.get_categories()
        b = kb.InlineKeyboardBuilder()
        for c in categories:
            mark = "✅ " if c["id"] == product["category_id"] else ""
            b.button(text=mark + c["name"], callback_data=f"pcat:{product['id']}:{c['id']}")
        b.button(text="⬅️ Orqaga", callback_data=f"mdp:{product['id']}")
        b.adjust(2)
        await edit(callback, "📂 Yangi kategoriyani tanlang:", b.as_markup())
    elif field == "ph":
        photos = db.product_photos(product)
        if photos:
            try:
                await callback.message.answer_media_group([kb.InputMediaPhoto(media=f) for f in photos])
            except Exception as e:  # faqat ko'rsatish uchun — xato bo'lsa ham davom etamiz
                log.warning("Rasmlar albomi ko'rsatilmadi: %s", e)
        b = kb.InlineKeyboardBuilder()
        if len(photos) < db.MAX_PHOTOS:
            b.button(text="➕ Rasm qo'shish", callback_data=f"peph:add:{product['id']}")
        b.button(text="🔄 Hammasini almashtirish", callback_data=f"peph:new:{product['id']}")
        if photos:
            b.button(text="🗑 Rasmlarni o'chirish", callback_data=f"peph:del:{product['id']}")
        b.button(text="⬅️ Orqaga", callback_data=f"mdp:{product['id']}")
        b.adjust(1)
        await callback.message.answer(f"🖼 Hozir {len(photos)} ta rasm (birinchisi — asosiy). Nima qilamiz?",
                                      reply_markup=b.as_markup())
    elif field == "v":
        await state.set_state(EditProduct.video)
        await state.update_data(edit_product_id=product["id"])
        markup = None
        if product.get("video_id"):
            markup = kb.InlineKeyboardMarkup(inline_keyboard=[[
                kb.InlineKeyboardButton(text="🗑 Videoni o'chirish", callback_data=f"mdelv:{product['id']}")
            ]])
        await callback.message.answer(
            f"🎬 Video: {HAS if product.get('video_id') else HAS_NOT}\n\nYangi videoni yuboring (20 MB gacha — saytda ham ko'rinadi):",
            reply_markup=markup,
        )
        await callback.message.answer("👇", reply_markup=kb.cancel_kb(DEFAULT_LANG))
    elif field == "t":
        b = kb.InlineKeyboardBuilder()
        for code in ("ru", "tg", "kk", "uz"):
            b.button(text=f"{TR_FLAGS[code]} Nomi", callback_data=f"petr:{code}:n:{product['id']}")
            if product.get("description"):
                b.button(text=f"{TR_FLAGS[code]} Tavsif", callback_data=f"petr:{code}:d:{product['id']}")
        b.button(text="⬅️ Orqaga", callback_data=f"mdp:{product['id']}")
        b.adjust(2 if product.get("description") else 1)
        await callback.message.answer("🌐 Qaysi tarjimani tuzatamiz?", reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("petr:"))
async def cb_edit_translation(callback: CallbackQuery, state: FSMContext):
    _, code, field, pid = callback.data.split(":")
    product = await db.get_product(int(pid))
    if not product or code not in LANG_NAMES:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    column = "name" if field == "n" else "description"
    current = loc_value(product, column, code)
    await state.set_state(EditProduct.text)
    await state.update_data(edit_product_id=product["id"], edit_field=f"tr:{code}:{column}")
    await callback.message.answer(
        f"{LANG_NAMES[code]} — {'nomi' if field == 'n' else 'tavsifi'}:\n<code>{escape(current or '')}</code>\n\n"
        "To'g'ri variantini yozing:",
        reply_markup=kb.cancel_kb(DEFAULT_LANG),
    )
    await callback.answer()


def loc_value(product: dict, column: str, code: str) -> str | None:
    raw = product.get(f"{column}_i18n")
    if raw:
        try:
            value = json.loads(raw).get(code)
            if value:
                return value
        except ValueError:
            pass
    return product.get(column)


@router.message(EditProduct.text, F.text)
async def edit_text_value(message: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    pid, field = data["edit_product_id"], data["edit_field"]
    product = await db.get_product(pid)
    if not product:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=kb.main_menu(lang, True))
        return
    text = message.text.strip()
    notice = "✅ Saqlandi."
    if field == "n":
        name, name_i18n, status = await translate_input(message, text[:400])
        await db.update_product(pid, name=name[:100], name_i18n=name_i18n)
        notice = f"✅ Nomi yangilandi: <b>{escape(name)}</b>" + translate.preview(name_i18n, status)
    elif field == "d":
        if is_skip(text):
            await db.update_product(pid, description=None, description_i18n=None)
            notice = "✅ Tavsif o'chirildi."
        else:
            desc, desc_i18n, status = await translate_input(message, text[:3000])
            await db.update_product(pid, description=desc[:900], description_i18n=desc_i18n)
            notice = "✅ Tavsif yangilandi." + translate.preview(desc_i18n, status)
    elif field == "p":
        raw = text.replace(" ", "").replace(",", "")
        if not raw.isdigit() or int(raw) <= 0:
            await message.answer("❗️ Narx musbat butun son bo'lishi kerak. Masalan: 1500000")
            return
        await db.update_product(pid, price=int(raw))
        notice = f"✅ Narx yangilandi: <b>{fmt_price(int(raw))}</b>"
    elif field == "q":
        stock = parse_stock(text)
        if stock is False:
            await message.answer("❗️ Son kiriting (0 yoki undan katta), masalan: 5")
            return
        await db.update_product(pid, stock=stock)
        notice = f"✅ Soni yangilandi: <b>{stock_label(stock)}</b>"
    elif field == "s":
        if is_skip(text):
            await db.update_product(pid, sizes=None)
            notice = "✅ O'lchamlar o'chirildi."
        else:
            sizes = parse_sizes(text)
            if sizes is None:
                await message.answer("❗️ Noto'g'ri format. Masalan: 16, 16.5, 17")
                return
            await db.update_product(pid, sizes=",".join(sizes))
            notice = f"✅ O'lchamlar: {escape(', '.join(sizes))}"
    elif field.startswith("tr:"):
        _, code, column = field.split(":")
        try:
            translations = json.loads(product.get(f"{column}_i18n") or "{}")
        except ValueError:
            translations = {}
        base = product.get(column) or ""
        translations = {c: translations.get(c) or base for c in LANG_NAMES}
        translations[code] = text[:900]
        fields = {f"{column}_i18n": json.dumps(translations, ensure_ascii=False)}
        if code == "uz":
            fields[column] = text[:100] if column == "name" else text[:900]
        await db.update_product(pid, **fields)
        notice = f"✅ {LANG_NAMES[code]} tarjimasi yangilandi: {escape(text)}"
    await state.clear()
    await message.answer(notice, reply_markup=kb.main_menu(lang, True))
    await send_edit_view(message, pid)


@router.callback_query(F.data.startswith("pcat:"))
async def cb_edit_category(callback: CallbackQuery):
    _, pid, cid = callback.data.split(":")
    if not await db.get_category(int(cid)):
        await callback.answer("Kategoriya topilmadi", show_alert=True)
        return
    await db.update_product(int(pid), category_id=int(cid))
    await callback.answer("✅ Kategoriya o'zgardi")
    text, markup = await product_edit_view(int(pid))
    await edit(callback, text, markup)


@router.callback_query(F.data.startswith("peph:"))
async def cb_edit_photos(callback: CallbackQuery, state: FSMContext, lang: str):
    _, mode, pid = callback.data.split(":")
    product = await db.get_product(int(pid))
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await callback.answer()
    if mode == "del":
        await db.set_product_photos(product["id"], [])
        await send_edit_view(callback.message, product["id"], "✅ Rasmlar o'chirildi.")
        return
    existing = db.product_photos(product) if mode == "add" else []
    await state.set_state(EditProduct.photos)
    await state.update_data(edit_product_id=product["id"], photos=existing, photo_items=None, photo_seq=0,
                            photo_limit_warned=False)
    free = db.MAX_PHOTOS - len(existing)
    await callback.message.answer(
        f"📸 Rasmlarni yuboring (yana {free} tagacha, albom qilib ham bo'ladi), so'ng «{BTN_DONE}» ni bosing.",
        reply_markup=photos_kb(),
    )


@router.message(EditProduct.photos, F.photo)
async def edit_photo_collect(message: Message, state: FSMContext):
    await collect_photo(message, state)


@router.message(EditProduct.photos, F.text.in_({BTN_DONE, *all_texts("btn_skip")}))
async def edit_photos_done(message: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    await state.clear()
    pid = data["edit_product_id"]
    if message.text == BTN_DONE:
        await db.set_product_photos(pid, data.get("photos") or [])
        notice = f"✅ Rasmlar saqlandi: {len(data.get('photos') or [])} ta"
    else:
        notice = "Rasmlar o'zgartirilmadi."
    await message.answer(notice, reply_markup=kb.main_menu(lang, True))
    await send_edit_view(message, pid)


@router.message(EditProduct.photos)
async def edit_photos_invalid(message: Message):
    await message.answer(f"Iltimos, rasm yuboring yoki «{BTN_DONE}» ni bosing.")


@router.message(EditProduct.video, F.video | F.document)
async def edit_video_upload(message: Message, state: FSMContext, lang: str):
    video = _video_from(message)
    if not video:
        await message.answer("Iltimos, video yuboring.")
        return
    pid = (await state.get_data())["edit_product_id"]
    await state.clear()
    await db.set_product_video(pid, video[0], video[1])
    await message.answer("✅ Video yangilandi." + (VIDEO_TOO_BIG if video[1] > MAX_WEB_MEDIA_BYTES else ""),
                         reply_markup=kb.main_menu(lang, True))
    await send_edit_view(message, pid)


@router.message(EditProduct.video)
async def edit_video_invalid(message: Message):
    await message.answer("Iltimos, video yuboring (yoki «❌ Bekor qilish»).")


# ---------------- Mavjud mahsulot ranglarini o'zgartirish ----------------
@router.callback_query(F.data.startswith("ecs:"))
async def cb_edit_colors(callback: CallbackQuery, state: FSMContext):
    product = await db.get_product(int(callback.data.split(":")[1]))
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    colors = color_mod.product_colors(product)
    await state.set_state(EditColors.wait)
    await state.update_data(edit_product_id=product["id"], colors=colors)
    await callback.message.answer(COLORS_HELP.replace("Rang kerak bo'lmasa — «O'tkazib yuborish».",
                                                      "Hamma ranglarni olib tashlab «✔️ Tayyor» bossangiz — rang tanlash o'chadi."),
                                  reply_markup=kb.cancel_kb(DEFAULT_LANG))
    await callback.message.answer("🎨 Ranglar:", reply_markup=kb.colors_select_kb(colors, "ec"))
    await callback.answer()


@router.callback_query(EditColors.wait, F.data.startswith("ec:") | F.data.startswith("ecx:"))
async def cb_edit_colors_toggle(callback: CallbackQuery, state: FSMContext):
    colors = _toggle_color((await state.get_data()).get("colors", []), callback.data)
    await state.update_data(colors=colors)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb.colors_select_kb(colors, "ec"))
    except TelegramBadRequest:
        pass
    await callback.answer()


@router.message(EditColors.wait, F.text)
async def edit_colors_text(message: Message, state: FSMContext):
    colors = (await state.get_data()).get("colors", [])
    for custom in color_mod.parse_custom(message.text):
        custom = await translate.auto_color(custom)
        if custom not in colors and len(colors) < color_mod.MAX_COLORS:
            colors.append(custom)
    await state.update_data(colors=colors)
    await message.answer("🎨 Ranglar:", reply_markup=kb.colors_select_kb(colors, "ec"))


@router.callback_query(EditColors.wait, F.data == "ec_done")
async def cb_edit_colors_done(callback: CallbackQuery, state: FSMContext, lang: str):
    data = await state.get_data()
    await state.clear()
    await db.set_product_colors(data["edit_product_id"], color_mod.dump(data.get("colors") or []))
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.answer()
    names = ", ".join(color_mod.name(c, "uz") for c in data.get("colors") or []) or "yo'q"
    await callback.message.answer(f"✅ Ranglar saqlandi: {escape(names)}", reply_markup=kb.main_menu(lang, True))
    await send_edit_view(callback.message, data["edit_product_id"])


@router.callback_query(F.data.startswith("mdelv:"))
async def cb_media_delete_video(callback: CallbackQuery, state: FSMContext, lang: str):
    pid = int(callback.data.split(":")[1])
    await db.set_product_video(pid, None)
    await state.clear()
    await callback.answer("🗑 Video o'chirildi", show_alert=True)
    await callback.message.answer("✅ Video o'chirildi.", reply_markup=kb.main_menu(lang, True))
    await send_edit_view(callback.message, pid)


@router.callback_query(F.data == "adm:del_prod")
async def cb_del_product(callback: CallbackQuery):
    categories = await db.get_categories()
    if not categories:
        await callback.answer("Kategoriyalar yo'q", show_alert=True)
        return
    await edit(callback, "Kategoriyani tanlang:", kb.categories_kb(categories, prefix="dpc"))


@router.callback_query(F.data.startswith("dpc:"))
async def cb_del_product_category(callback: CallbackQuery):
    products = await db.get_products(int(callback.data.split(":")[1]))
    if not products:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return
    await edit(callback, "Qaysi mahsulotni o'chirasiz?", kb.admin_products_delete_kb(products))


@router.callback_query(F.data.startswith("dp:"))
async def cb_del_product_do(callback: CallbackQuery):
    product = await db.get_product(int(callback.data.split(":")[1]))
    if not product:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return
    await db.delete_product(product["id"])
    await callback.answer(f"🗑 «{product['name']}» o'chirildi")
    products = await db.get_products(product["category_id"])
    if products:
        await edit(callback, "Qaysi mahsulotni o'chirasiz?", kb.admin_products_delete_kb(products))
    else:
        await edit(callback, "⚙️ <b>Admin panel</b>", kb.admin_menu_kb())


# ================= BUYURTMALAR =================
@router.callback_query(F.data == "adm:orders")
async def cb_orders(callback: CallbackQuery):
    orders = await db.get_recent_orders()
    if not orders:
        await callback.answer("Hali buyurtmalar yo'q", show_alert=True)
        return
    lines = ["📋 <b>Oxirgi buyurtmalar:</b>\n"]
    for o in orders:
        lines.append(
            f"#{o['id']} • {escape(o['full_name'] or '')} • {escape(o['phone'] or '')}\n"
            f"    {fmt_price(o['total'])} • {kb.status_label(o['status'])} • {o['created_at']}"
        )
    lines.append("\nBatafsil: /order <code>raqam</code>")
    await edit(callback, "\n".join(lines), kb.admin_menu_kb())


@router.message(Command("order"))
async def cmd_order(message: Message):
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("#").isdigit():
        await message.answer("Foydalanish: /order 12")
        return
    order_id = int(parts[1].lstrip("#"))
    order = await db.get_order(order_id)
    if not order:
        await message.answer("Buyurtma topilmadi.")
        return
    items = await db.get_order_items(order_id)
    await message.answer(kb.order_text(order, items, "uz", for_admin=True), reply_markup=kb.admin_order_kb(order_id))
    if order["latitude"] is not None:
        await message.answer_location(order["latitude"], order["longitude"])


@router.callback_query(F.data.startswith("status:"))
async def cb_order_status(callback: CallbackQuery, bot: Bot):
    _, order_id, status = callback.data.split(":")
    order_id = int(order_id)
    if status not in kb.STATUSES:
        await callback.answer()
        return
    order = await db.get_order(order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    if order["status"] == status:
        await callback.answer("Holat allaqachon shunday")
        return
    if order["status"] == "cancelled":
        await callback.answer("Bekor qilingan buyurtma holatini o'zgartirib bo'lmaydi", show_alert=True)
        return
    await db.set_order_status(order_id, status)
    lang = order.get("lang") or await db.get_user_lang(order["user_id"]) or DEFAULT_LANG
    bonus_notes = []
    if status == "delivered":
        awarded = await db.award_order_bonus(order_id)
        if awarded:
            bonus_notes.append(t("bonus_earned_msg", lang, id=order_id, n=awarded["amount"], total=awarded["balance"],
                                 value=kb.bonus_value(awarded["balance"], lang)))
    elif status == "cancelled":
        result = await db.cancel_order_bonus(order_id)
        if result["refunded"]:
            bonus_notes.append(t("bonus_refund_msg", lang, id=order_id, n=result["refunded"]))
        if await db.restore_order_stock(order_id):
            await callback.message.answer(f"📦 Buyurtma #{order_id} mahsulotlari qoldiqqa qaytarildi.")
        await courier.notify_cancel(order_id)
    order = await db.get_order(order_id)
    items = await db.get_order_items(order_id)
    try:
        await callback.message.edit_text(
            kb.order_text(order, items, "uz", for_admin=True), reply_markup=kb.admin_order_kb(order_id)
        )
    except TelegramBadRequest:
        pass
    await callback.answer(f"Holat o'zgardi: {kb.status_label(status)}")
    if status == "cancelled" and order.get("payment_status") == "paid" and order.get("payment_method") in PAYMENT_NAMES:
        method = order.get("payment_method") or ""
        await callback.message.answer(
            f"⚠️ Buyurtma #{order_id} <b>onlayn to'langan</b> edi ({method}). Pulni mijozga qaytarishni "
            f"{method.capitalize()} biznes kabinetida amalga oshiring.\n"
            f"To'lov ID: <code>{escape(order.get('provider_charge_id') or '-')}</code>"
        )
    # Mijozga o'z tilida xabar
    try:
        await bot.send_message(
            order["user_id"],
            "\n\n".join([t("status_changed", lang, id=order_id, status=kb.status_label(status, lang)), *bonus_notes]),
        )
    except Exception as e:
        log.warning("Mijozga (%s) xabar yuborilmadi: %s", order["user_id"], e)


# ================= BRILLIANT SOVG'A QILISH =================
@router.message(Command("bonus"))
async def cmd_bonus(message: Message, bot: Bot):
    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].lstrip("-").isdigit() or int(parts[2]) == 0:
        await message.answer("Foydalanish: <code>/bonus ID SON</code>\nMasalan: <code>/bonus 123456789 5</code> "
                             "(manfiy son — brilliantni olib qo'yish)")
        return
    user_id, amount = int(parts[1]), int(parts[2])
    user = await db.get_user(user_id)
    if not user:
        await message.answer("❗️ Bu ID dagi mijoz topilmadi (u botga /start bosmagan).")
        return
    if amount < 0 and await db.get_bonus(user_id) < -amount:
        await message.answer("❗️ Mijozda buncha brilliant yo'q.")
        return
    total = await db.admin_give_bonus(user_id, amount)
    await message.answer(f"✅ {escape(user['full_name'] or str(user_id))}: {amount:+d} 💎. Endi: {total} 💎")
    if amount > 0:
        lang = user.get("lang") or DEFAULT_LANG
        try:
            await bot.send_message(user_id, t("bonus_from_shop", lang, n=amount, value=kb.bonus_value(amount, lang), total=total))
        except Exception as e:
            log.warning("Mijozga (%s) xabar yuborilmadi: %s", user_id, e)


# ================= KURYERLAR =================
COURIER_STATUS = {"active": "✅ faol", "pending": "⏳ kutmoqda", "blocked": "⛔️ o'chirilgan"}


async def couriers_view():
    couriers = await db.get_couriers()
    lines = ["🛵 <b>Kuryerlar</b>\n"]
    if not courier.enabled():
        lines.append("⚠️ Kuryer boti ulanmagan. Railway Variables'ga <code>COURIER_BOT_TOKEN</code> qo'shing.\n")
    if not couriers:
        lines.append("Hali kuryer yo'q. Kuryer, kuryer botiga /start bosib, telefon raqamini yuborsin.")
    b = kb.InlineKeyboardBuilder()
    for c in couriers:
        lines.append(f"• {escape(c['full_name'] or '')} — {escape(fmt_phone(c['phone'] or ''))} — {COURIER_STATUS.get(c['status'], c['status'])}")
        if c["status"] == "active":
            b.button(text=f"⛔️ {c['full_name']}", callback_data=f"cr_no:{c['id']}")
        else:
            b.button(text=f"✅ {c['full_name']}", callback_data=f"cr_ok:{c['id']}")
    b.button(text="⬅️ Admin panel", callback_data="adm:menu")
    b.adjust(1)
    return "\n".join(lines), b.as_markup()


@router.callback_query(F.data == "adm:couriers")
async def cb_couriers(callback: CallbackQuery):
    text, markup = await couriers_view()
    await edit(callback, text, markup)


@router.callback_query(F.data.startswith("cr_ok:") | F.data.startswith("cr_no:"))
async def cb_courier_decision(callback: CallbackQuery):
    approve = callback.data.startswith("cr_ok:")
    courier_id = int(callback.data.split(":")[1])
    c = await db.get_courier(courier_id)
    if not c:
        await callback.answer("Kuryer topilmadi", show_alert=True)
        return
    await db.set_courier_status(courier_id, "active" if approve else "blocked")
    await callback.answer("✅ Kuryer tasdiqlandi" if approve else "⛔️ Kuryer o'chirildi", show_alert=True)
    if courier.enabled():
        try:
            await courier.COURIER_BOT.send_message(
                courier_id,
                "🎉 Siz kuryer sifatida tasdiqlandingiz! Yangi buyurtmalar shu yerga keladi."
                if approve else "⛔️ Kuryer hisobingiz faol emas. Savollar bo'lsa, do'kon bilan bog'laning.",
                reply_markup=courier.courier_menu() if approve else None,
            )
        except Exception as e:
            log.warning("Kuryerga (%s) xabar yuborilmadi: %s", courier_id, e)
    text, markup = await couriers_view()
    await edit(callback, text, markup)


# ================= STATISTIKA =================
def payment_status_text() -> str:
    providers = payment_providers()
    if not providers:
        return "ulanmagan (faqat naqd). Railway'ga CLICK_TOKEN / PAYME_TOKEN qo'shing"
    return ", ".join(PAYMENT_NAMES[p] + (" 🧪 test" if is_test_token(p) else " ✅") for p in providers)


@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    s = await db.get_stats()
    bonus = await db.bonus_stats()
    users = await db.get_users_with_lang()
    by_lang = {code: 0 for code in LANG_NAMES}
    for u in users:
        by_lang[u["lang"] or DEFAULT_LANG] = by_lang.get(u["lang"] or DEFAULT_LANG, 0) + 1
    langs = "\n".join(f"    {LANG_NAMES[c]}: {n}" for c, n in by_lang.items())
    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{s['users']}</b>\n{langs}\n"
        f"🛍 Faol mahsulotlar: <b>{s['products']}</b>\n"
        f"📦 Jami buyurtmalar: <b>{s['orders']}</b>\n"
        f"🆕 Yangi buyurtmalar: <b>{s['new_orders']}</b>\n"
        f"💰 Tushum (yetkazilgan): <b>{fmt_price(s['revenue'])}</b>\n"
        f"💳 Onlayn to'langan: <b>{s['paid_orders']}</b> ta — <b>{fmt_price(s['paid_sum'])}</b>\n"
        f"🔌 To'lov tizimlari: {payment_status_text()}\n"
        f"💎 Mijozlardagi brilliantlar: <b>{bonus['outstanding']}</b> ta ({fmt_price(bonus['outstanding'] * BONUS_VALUE)}), "
        f"{bonus['holders']} kishida\n\n"
        "<i>Mijozga brilliant sovg'a qilish: /bonus ID SON (masalan: /bonus 123456789 5)</i>"
    )
    await edit(callback, text, kb.admin_menu_kb())


# ================= XABAR YUBORISH =================
@router.callback_query(F.data == "adm:broadcast")
async def cb_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Broadcast.message)
    await callback.message.answer(
        "Barcha foydalanuvchilarga yuboriladigan xabarni yuboring (matn, rasm, video — istalgan).\n"
        "<i>Xabar qanday yozilsa, barchaga shunday boradi. Aksiya haqida har kimga o'z tilida yuborish uchun "
        "🔥 Aksiya → 📢 Mijozlarga e'lon qilish tugmasidan foydalaning.</i>",
        reply_markup=kb.cancel_kb(DEFAULT_LANG),
    )
    await callback.answer()


@router.message(Broadcast.message)
async def broadcast_send(message: Message, state: FSMContext, lang: str):
    await state.clear()
    user_ids = await db.get_all_user_ids()
    await message.answer(f"⏳ {len(user_ids)} ta foydalanuvchiga yuborilmoqda...", reply_markup=kb.main_menu(lang, True))
    ok = fail = 0
    for uid in user_ids:
        if await send_safely(lambda: message.copy_to(uid)):
            ok += 1
        else:
            fail += 1
        await asyncio.sleep(0.05)  # Telegram limitlaridan oshmaslik uchun
    await message.answer(f"✅ Yuborildi: {ok}\n❌ Yuborilmadi: {fail}")
