"""Ko'p tillilik: o'zbek, rus, tojik, qozoq.

Matnlar TEXTS lug'atida saqlanadi. t("kalit", lang, **qiymatlar) — tarjima olish.
"""
import json

from aiogram import BaseMiddleware

LANGS = ["uz", "ru", "tg", "kk"]
DEFAULT_LANG = "uz"
LANG_NAMES = {
    "uz": "🇺🇿 O'zbekcha",
    "ru": "🇷🇺 Русский",
    "tg": "🇹🇯 Тоҷикӣ",
    "kk": "🇰🇿 Қазақша",
}

TEXTS: dict[str, dict[str, str]] = {
    # ---------------- Umumiy ----------------
    "choose_lang": dict.fromkeys(
        LANGS,
        "🌐 Tilni tanlang\n🌐 Выберите язык\n🌐 Забонро интихоб кунед\n🌐 Тілді таңдаңыз",
    ),
    "lang_set": {
        "uz": "✅ Til tanlandi: O'zbekcha",
        "ru": "✅ Выбран язык: Русский",
        "tg": "✅ Забон интихоб шуд: Тоҷикӣ",
        "kk": "✅ Тіл таңдалды: Қазақша",
    },
    "welcome": {
        "uz": "Assalomu alaykum, <b>{name}</b>! 👋\n\n💎 <b>{shop}</b> zargarlik do'koniga xush kelibsiz!\n\n"
              "Bu yerda siz uzuk, sirg'a, zanjir, bilakuzuk va boshqa nafis taqinchoqlarni ko'rib, "
              "bir necha bosishda buyurtma berishingiz mumkin.\n\n👇 Boshlash uchun «{catalog}» tugmasini bosing.",
        "ru": "Здравствуйте, <b>{name}</b>! 👋\n\n💎 Добро пожаловать в ювелирный магазин <b>{shop}</b>!\n\n"
              "Здесь вы можете выбрать кольца, серьги, цепочки, браслеты и другие изысканные украшения "
              "и оформить заказ в несколько касаний.\n\n👇 Чтобы начать, нажмите «{catalog}».",
        "tg": "Ассалому алейкум, <b>{name}</b>! 👋\n\n💎 Ба мағозаи заргарии <b>{shop}</b> хуш омадед!\n\n"
              "Дар ин ҷо шумо метавонед ангуштарин, гӯшвор, занҷир, дастпона ва дигар ороишоти зеборо "
              "интихоб карда, бо чанд пахш фармоиш диҳед.\n\n👇 Барои оғоз тугмаи «{catalog}»-ро пахш кунед.",
        "kk": "Сәлеметсіз бе, <b>{name}</b>! 👋\n\n💎 <b>{shop}</b> зергерлік дүкеніне қош келдіңіз!\n\n"
              "Мұнда сіз сақина, сырға, шынжыр, білезік және басқа да әсем әшекейлерді таңдап, "
              "бірнеше рет басу арқылы тапсырыс бере аласыз.\n\n👇 Бастау үшін «{catalog}» түймесін басыңыз.",
    },
    "cancelled": {"uz": "Bekor qilindi.", "ru": "Отменено.", "tg": "Бекор карда шуд.", "kk": "Бас тартылды."},
    "use_menu": {
        "uz": "Iltimos, quyidagi menyudan foydalaning 👇",
        "ru": "Пожалуйста, воспользуйтесь меню ниже 👇",
        "tg": "Лутфан, аз менюи поён истифода баред 👇",
        "kk": "Төмендегі мәзірді пайдаланыңыз 👇",
    },
    # ---------------- Tugmalar ----------------
    "btn_catalog": {"uz": "🛍 Katalog", "ru": "🛍 Каталог", "tg": "🛍 Каталог", "kk": "🛍 Каталог"},
    "btn_cart": {"uz": "🛒 Savat", "ru": "🛒 Корзина", "tg": "🛒 Сабад", "kk": "🛒 Себет"},
    "btn_orders": {"uz": "📦 Buyurtmalarim", "ru": "📦 Мои заказы", "tg": "📦 Фармоишҳои ман", "kk": "📦 Тапсырыстарым"},
    "btn_about": {"uz": "💎 Biz haqimizda", "ru": "💎 О нас", "tg": "💎 Дар бораи мо", "kk": "💎 Біз туралы"},
    "btn_channel": {"uz": "📢 Kanalimiz", "ru": "📢 Наш канал", "tg": "📢 Канали мо", "kk": "📢 Біздің арна"},
    "btn_contact": {"uz": "☎️ Aloqa", "ru": "☎️ Контакты", "tg": "☎️ Тамос", "kk": "☎️ Байланыс"},
    "btn_lang": {"uz": "🌐 Til", "ru": "🌐 Язык", "tg": "🌐 Забон", "kk": "🌐 Тіл"},
    "btn_promo": {"uz": "🔥 Aksiya", "ru": "🔥 Акция", "tg": "🔥 Аксия", "kk": "🔥 Акция"},
    "btn_cancel": {"uz": "❌ Bekor qilish", "ru": "❌ Отмена", "tg": "❌ Бекор кардан", "kk": "❌ Бас тарту"},
    "btn_skip": {"uz": "⏭ O'tkazib yuborish", "ru": "⏭ Пропустить", "tg": "⏭ Гузаштан", "kk": "⏭ Өткізіп жіберу"},
    "btn_phone": {"uz": "📱 Raqamni yuborish", "ru": "📱 Отправить номер", "tg": "📱 Фиристодани рақам", "kk": "📱 Нөмірді жіберу"},
    "btn_location": {
        "uz": "📍 Joylashuvni yuborish", "ru": "📍 Отправить геолокацию",
        "tg": "📍 Фиристодани макон", "kk": "📍 Орналасқан жерді жіберу",
    },
    "btn_back": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад", "tg": "⬅️ Бозгашт", "kk": "⬅️ Артқа"},
    "btn_back_cats": {"uz": "⬅️ Kategoriyalar", "ru": "⬅️ Категории", "tg": "⬅️ Категорияҳо", "kk": "⬅️ Санаттар"},
    "btn_add_cart": {"uz": "🛒 Savatga qo'shish", "ru": "🛒 В корзину", "tg": "🛒 Ба сабад", "kk": "🛒 Себетке қосу"},
    "btn_clear_cart": {
        "uz": "🧹 Savatni tozalash", "ru": "🧹 Очистить корзину",
        "tg": "🧹 Тоза кардани сабад", "kk": "🧹 Себетті тазалау",
    },
    "btn_checkout": {"uz": "✅ Buyurtma berish", "ru": "✅ Оформить заказ", "tg": "✅ Фармоиш додан", "kk": "✅ Тапсырыс беру"},
    "btn_confirm": {"uz": "✅ Tasdiqlash", "ru": "✅ Подтвердить", "tg": "✅ Тасдиқ кардан", "kk": "✅ Растау"},
    "btn_open_channel": {
        "uz": "📢 Kanalga o'tish", "ru": "📢 Перейти в канал",
        "tg": "📢 Ба канал гузаштан", "kk": "📢 Арнаға өту",
    },
    "btn_shop_now": {"uz": "🛍 Xarid qilish", "ru": "🛍 За покупками", "tg": "🛍 Харид кардан", "kk": "🛍 Сатып алу"},
    "pcs": {"uz": "dona", "ru": "шт.", "tg": "дона", "kk": "дана"},
    # ---------------- Katalog ----------------
    "choose_category": {
        "uz": "📂 Kategoriyani tanlang:", "ru": "📂 Выберите категорию:",
        "tg": "📂 Категорияро интихоб кунед:", "kk": "📂 Санатты таңдаңыз:",
    },
    "no_products": {
        "uz": "Hozircha mahsulotlar mavjud emas. Keyinroq urinib ko'ring 🙂",
        "ru": "Пока товаров нет. Загляните позже 🙂",
        "tg": "Ҳоло маҳсулот мавҷуд нест. Баъдтар бори дигар кӯшиш кунед 🙂",
        "kk": "Әзірге тауарлар жоқ. Кейінірек қайта кіріңіз 🙂",
    },
    "category_empty": {
        "uz": "Bu kategoriyada hozircha mahsulot yo'q.", "ru": "В этой категории пока нет товаров.",
        "tg": "Дар ин категория ҳоло маҳсулот нест.", "kk": "Бұл санатта әзірге тауар жоқ.",
    },
    "choose_product": {
        "uz": "Mahsulotni tanlang:", "ru": "Выберите товар:",
        "tg": "Маҳсулотро интихоб кунед:", "kk": "Тауарды таңдаңыз:",
    },
    "not_found_category": {"uz": "Kategoriya topilmadi", "ru": "Категория не найдена", "tg": "Категория ёфт нашуд", "kk": "Санат табылмады"},
    "not_found_product": {"uz": "Mahsulot topilmadi", "ru": "Товар не найден", "tg": "Маҳсулот ёфт нашуд", "kk": "Тауар табылмады"},
    "price": {"uz": "💰 Narxi", "ru": "💰 Цена", "tg": "💰 Нарх", "kk": "💰 Бағасы"},
    "sizes": {"uz": "📏 O'lchamlar", "ru": "📏 Размеры", "tg": "📏 Андозаҳо", "kk": "📏 Өлшемдер"},
    "choose_size_hint": {
        "uz": "👇 Kerakli o'lchamni tanlang", "ru": "👇 Выберите нужный размер",
        "tg": "👇 Андозаи лозимиро интихоб кунед", "kk": "👇 Қажетті өлшемді таңдаңыз",
    },
    "size_selected": {"uz": "O'lcham: {size}", "ru": "Размер: {size}", "tg": "Андоза: {size}", "kk": "Өлшем: {size}"},
    "size_label": {"uz": " (o'lcham: {size})", "ru": " (размер: {size})", "tg": " (андоза: {size})", "kk": " (өлшем: {size})"},
    "colors": {"uz": "🎨 Ranglar", "ru": "🎨 Цвета", "tg": "🎨 Рангҳо", "kk": "🎨 Түстер"},
    "choose_color_hint": {
        "uz": "👇 Rangni tanlang", "ru": "👇 Выберите цвет", "tg": "👇 Рангро интихоб кунед", "kk": "👇 Түсін таңдаңыз",
    },
    "choose_color_first": {
        "uz": "🎨 Avval rangni tanlang!", "ru": "🎨 Сначала выберите цвет!",
        "tg": "🎨 Аввал рангро интихоб кунед!", "kk": "🎨 Алдымен түсін таңдаңыз!",
    },
    "color_selected": {"uz": "Rang: {color}", "ru": "Цвет: {color}", "tg": "Ранг: {color}", "kk": "Түсі: {color}"},
    "variant_size": {"uz": "o'lcham: {v}", "ru": "размер: {v}", "tg": "андоза: {v}", "kk": "өлшем: {v}"},
    "variant_color": {"uz": "rang: {v}", "ru": "цвет: {v}", "tg": "ранг: {v}", "kk": "түсі: {v}"},
    "in_stock": {"uz": "📦 Mavjud: {n} dona", "ru": "📦 В наличии: {n} шт.", "tg": "📦 Мавҷуд: {n} дона", "kk": "📦 Қолда бар: {n} дана"},
    "low_stock": {
        "uz": "⚠️ Faqat {n} ta qoldi!", "ru": "⚠️ Осталось всего {n} шт.!",
        "tg": "⚠️ Танҳо {n} дона монд!", "kk": "⚠️ Тек {n} дана қалды!",
    },
    "out_of_stock": {
        "uz": "❌ Hozircha tugagan", "ru": "❌ Нет в наличии", "tg": "❌ Ҳоло тамом шудааст", "kk": "❌ Қазір қолда жоқ",
    },
    "btn_out_of_stock": {"uz": "❌ Tugagan", "ru": "❌ Нет в наличии", "tg": "❌ Тамом шуд", "kk": "❌ Таусылды"},
    "stock_limit": {
        "uz": "Bu mahsulotdan faqat {n} ta bor (savatingizda {c} ta).",
        "ru": "Этого товара всего {n} шт. (в корзине {c}).",
        "tg": "Аз ин маҳсулот танҳо {n} дона ҳаст (дар сабад {c}).",
        "kk": "Бұл тауардан тек {n} дана бар (себетте {c}).",
    },
    "stock_changed": {
        "uz": "⚠️ Kechirasiz, ba'zi mahsulotlar soni o'zgardi:\n{items}\n\nSavatni tekshirib, qaytadan buyurtma bering.",
        "ru": "⚠️ Извините, наличие некоторых товаров изменилось:\n{items}\n\nПроверьте корзину и оформите заказ снова.",
        "tg": "⚠️ Бубахшед, миқдори баъзе маҳсулотҳо тағйир ёфт:\n{items}\n\nСабадро санҷида, дубора фармоиш диҳед.",
        "kk": "⚠️ Кешіріңіз, кейбір тауарлардың саны өзгерді:\n{items}\n\nСебетті тексеріп, қайта тапсырыс беріңіз.",
    },
    "stock_left_item": {
        "uz": "• {name}: {n} ta qoldi", "ru": "• {name}: осталось {n} шт.",
        "tg": "• {name}: {n} дона монд", "kk": "• {name}: {n} дана қалды",
    },
    "choose_size_first": {
        "uz": "📏 Avval o'lchamni tanlang!", "ru": "📏 Сначала выберите размер!",
        "tg": "📏 Аввал андозаро интихоб кунед!", "kk": "📏 Алдымен өлшемді таңдаңыз!",
    },
    "qty_range": {
        "uz": "Miqdor 1 dan 99 gacha bo'lishi kerak", "ru": "Количество — от 1 до 99",
        "tg": "Миқдор бояд аз 1 то 99 бошад", "kk": "Саны 1-ден 99-ға дейін болуы керек",
    },
    "added": {
        "uz": "✅ {name}{size} — {qty} dona savatga qo'shildi!",
        "ru": "✅ {name}{size} — {qty} шт. добавлено в корзину!",
        "tg": "✅ {name}{size} — {qty} дона ба сабад илова шуд!",
        "kk": "✅ {name}{size} — {qty} дана себетке қосылды!",
    },
    # ---------------- Savat ----------------
    "cart_title": {
        "uz": "🛒 <b>Savatingiz:</b>", "ru": "🛒 <b>Ваша корзина:</b>",
        "tg": "🛒 <b>Сабади шумо:</b>", "kk": "🛒 <b>Сіздің себетіңіз:</b>",
    },
    "total": {"uz": "💰 Jami", "ru": "💰 Итого", "tg": "💰 Ҳамагӣ", "kk": "💰 Барлығы"},
    "saved": {"uz": "🔥 Tejadingiz", "ru": "🔥 Ваша экономия", "tg": "🔥 Сарфаи шумо", "kk": "🔥 Үнемдедіңіз"},
    "cart_empty": {
        "uz": "🛒 Savatingiz bo'sh.", "ru": "🛒 Ваша корзина пуста.",
        "tg": "🛒 Сабади шумо холӣ аст.", "kk": "🛒 Себетіңіз бос.",
    },
    "cart_cleared": {
        "uz": "🛒 Savatingiz tozalandi.", "ru": "🛒 Корзина очищена.",
        "tg": "🛒 Сабад тоза карда шуд.", "kk": "🛒 Себет тазартылды.",
    },
    # ---------------- Buyurtma berish ----------------
    "ask_name": {
        "uz": "👤 Ismingizni kiriting:", "ru": "👤 Введите ваше имя:",
        "tg": "👤 Номи худро ворид кунед:", "kk": "👤 Атыңызды енгізіңіз:",
    },
    "bad_name": {
        "uz": "Iltimos, ismingizni to'g'ri kiriting (2-64 belgi).",
        "ru": "Пожалуйста, введите имя корректно (2–64 символа).",
        "tg": "Лутфан, номи худро дуруст ворид кунед (2–64 аломат).",
        "kk": "Атыңызды дұрыс енгізіңіз (2–64 таңба).",
    },
    "ask_phone": {
        "uz": "📞 Telefon raqamingizni yuboring (tugmani bosing yoki +998901234567 ko'rinishida yozing):",
        "ru": "📞 Отправьте номер телефона (нажмите кнопку или напишите в формате +998901234567):",
        "tg": "📞 Рақами телефони худро фиристед (тугмаро пахш кунед ё дар шакли +992901234567 нависед):",
        "kk": "📞 Телефон нөміріңізді жіберіңіз (түймені басыңыз немесе +77011234567 түрінде жазыңыз):",
    },
    "own_phone": {
        "uz": "Iltimos, o'zingizning raqamingizni yuboring.", "ru": "Пожалуйста, отправьте свой собственный номер.",
        "tg": "Лутфан, рақами худатонро фиристед.", "kk": "Өз нөміріңізді жіберіңіз.",
    },
    "bad_phone": {
        "uz": "Telefon raqam noto'g'ri. Masalan: +998901234567",
        "ru": "Неверный номер. Пример: +998901234567",
        "tg": "Рақам нодуруст аст. Масалан: +992901234567",
        "kk": "Нөмір қате. Мысалы: +77011234567",
    },
    "ask_address": {
        "uz": "📍 Yetkazib berish manzilini yozing yoki joylashuvni yuboring:",
        "ru": "📍 Напишите адрес доставки или отправьте геолокацию:",
        "tg": "📍 Суроғаи расониданро нависед ё маконро фиристед:",
        "kk": "📍 Жеткізу мекенжайын жазыңыз немесе орналасқан жерді жіберіңіз:",
    },
    "address_short": {
        "uz": "Manzilni batafsilroq yozing.", "ru": "Пожалуйста, укажите адрес подробнее.",
        "tg": "Суроғаро муфассалтар нависед.", "kk": "Мекенжайды толығырақ жазыңыз.",
    },
    "ask_comment": {
        "uz": "💬 Qo'shimcha izoh qoldiring (masalan: sovg'a uchun qadoqlash, otkritkaga yozuv, qulay vaqt) "
              "yoki «{skip}» tugmasini bosing:",
        "ru": "💬 Оставьте комментарий (например: подарочная упаковка, текст открытки, удобное время) "
              "или нажмите «{skip}»:",
        "tg": "💬 Шарҳи иловагӣ гузоред (масалан: бастабандии тӯҳфавӣ, матни открытка, вақти мувофиқ) "
              "ё «{skip}»-ро пахш кунед:",
        "kk": "💬 Қосымша пікір қалдырыңыз (мысалы: сыйлық орамасы, ашықхатқа жазу, ыңғайлы уақыт) "
              "немесе «{skip}» түймесін басыңыз:",
    },
    "data_received": {
        "uz": "Ma'lumotlar qabul qilindi ✅", "ru": "Данные приняты ✅",
        "tg": "Маълумот қабул шуд ✅", "kk": "Деректер қабылданды ✅",
    },
    "location_sent": {
        "uz": "Joylashuv yuborilgan", "ru": "Геолокация отправлена",
        "tg": "Макон фиристода шуд", "kk": "Орналасқан жер жіберілді",
    },
    "confirm_q": {
        "uz": "Buyurtmani tasdiqlaysizmi?", "ru": "Подтверждаете заказ?",
        "tg": "Фармоишро тасдиқ мекунед?", "kk": "Тапсырысты растайсыз ба?",
    },
    "order_cancelled": {
        "uz": "Buyurtma bekor qilindi. Mahsulotlar savatingizda qoldi.",
        "ru": "Заказ отменён. Товары остались в корзине.",
        "tg": "Фармоиш бекор шуд. Маҳсулотҳо дар сабад монданд.",
        "kk": "Тапсырыстан бас тартылды. Тауарлар себетте қалды.",
    },
    "prices_changed": {
        "uz": "⚠️ Narxlar o'zgardi (aksiya muddati tugagan bo'lishi mumkin). "
              "Iltimos, yangilangan buyurtmani tekshirib, qayta tasdiqlang:",
        "ru": "⚠️ Цены изменились (возможно, закончилась акция). "
              "Проверьте обновлённый заказ и подтвердите ещё раз:",
        "tg": "⚠️ Нархҳо тағйир ёфтанд (шояд мӯҳлати аксия тамом шуд). "
              "Лутфан, фармоиши навшударо санҷида, боз тасдиқ кунед:",
        "kk": "⚠️ Бағалар өзгерді (акция аяқталған болуы мүмкін). "
              "Жаңартылған тапсырысты тексеріп, қайта растаңыз:",
    },
    "order_accepted": {
        "uz": "✅ Buyurtmangiz qabul qilindi!", "ru": "✅ Ваш заказ принят!",
        "tg": "✅ Фармоиши шумо қабул шуд!", "kk": "✅ Тапсырысыңыз қабылданды!",
    },
    "order_thanks": {
        "uz": "Tez orada operatorimiz siz bilan bog'lanadi. Xaridingiz uchun rahmat! 💎",
        "ru": "Наш оператор скоро свяжется с вами. Спасибо за покупку! 💎",
        "tg": "Оператори мо ба зудӣ бо шумо тамос мегирад. Ташаккур барои харид! 💎",
        "kk": "Операторымыз жақын арада сізбен хабарласады. Сатып алғаныңызға рахмет! 💎",
    },
    "order_expired": {
        "uz": "Bu buyurtma eskirgan. Iltimos, savatdan qaytadan rasmiylashtiring.",
        "ru": "Этот заказ устарел. Оформите его заново из корзины.",
        "tg": "Ин фармоиш кӯҳна шудааст. Лутфан, аз сабад дубора фармоиш диҳед.",
        "kk": "Бұл тапсырыс ескірген. Себеттен қайта ресімдеңіз.",
    },
    # ---------------- Buyurtmalar ----------------
    "no_orders": {
        "uz": "Sizda hali buyurtmalar yo'q.", "ru": "У вас пока нет заказов.",
        "tg": "Шумо ҳоло фармоиш надоред.", "kk": "Сізде әзірге тапсырыстар жоқ.",
    },
    "my_orders": {
        "uz": "📦 <b>Oxirgi buyurtmalaringiz:</b>", "ru": "📦 <b>Ваши последние заказы:</b>",
        "tg": "📦 <b>Фармоишҳои охирини шумо:</b>", "kk": "📦 <b>Соңғы тапсырыстарыңыз:</b>",
    },
    "order": {
        "uz": "🧾 <b>Buyurtma #{id}</b>", "ru": "🧾 <b>Заказ №{id}</b>",
        "tg": "🧾 <b>Фармоиш №{id}</b>", "kk": "🧾 <b>Тапсырыс №{id}</b>",
    },
    "comment": {"uz": "💬 Izoh", "ru": "💬 Комментарий", "tg": "💬 Шарҳ", "kk": "💬 Пікір"},
    "status": {"uz": "📌 Holati", "ru": "📌 Статус", "tg": "📌 Ҳолат", "kk": "📌 Күйі"},
    "discount": {"uz": "🔥 Chegirma", "ru": "🔥 Скидка", "tg": "🔥 Тахфиф", "kk": "🔥 Жеңілдік"},
    "status_new": {"uz": "🆕 Yangi", "ru": "🆕 Новый", "tg": "🆕 Нав", "kk": "🆕 Жаңа"},
    "status_accepted": {"uz": "✅ Qabul qilindi", "ru": "✅ Принят", "tg": "✅ Қабул шуд", "kk": "✅ Қабылданды"},
    "status_delivered": {"uz": "🚚 Yetkazildi", "ru": "🚚 Доставлен", "tg": "🚚 Расонида шуд", "kk": "🚚 Жеткізілді"},
    "status_cancelled": {"uz": "❌ Bekor qilindi", "ru": "❌ Отменён", "tg": "❌ Бекор шуд", "kk": "❌ Тоқтатылды"},
    "status_changed": {
        "uz": "🔔 Buyurtma #{id} holati o'zgardi: <b>{status}</b>",
        "ru": "🔔 Статус заказа №{id} изменён: <b>{status}</b>",
        "tg": "🔔 Ҳолати фармоиши №{id} тағйир ёфт: <b>{status}</b>",
        "kk": "🔔 №{id} тапсырыстың күйі өзгерді: <b>{status}</b>",
    },
    # ---------------- Ma'lumot ----------------
    "channel_text": {
        "uz": "📢 Yangi kolleksiyalar va aksiyalardan xabardor bo'lish uchun kanalimizga obuna bo'ling!",
        "ru": "📢 Подпишитесь на наш канал, чтобы узнавать о новых коллекциях и акциях!",
        "tg": "📢 Барои огоҳ шудан аз коллексияҳо ва аксияҳои нав ба канали мо обуна шавед!",
        "kk": "📢 Жаңа коллекциялар мен акциялардан хабардар болу үшін арнамызға жазылыңыз!",
    },
    "about": {
        "uz": "💎 <b>{shop}</b>\n\nBiz sifatli va nafis zargarlik buyumlarini taklif qilamiz.\n\n"
              "✨ Har bir mahsulot sifat nazoratidan o'tgan\n🎁 Sovg'a uchun chiroyli qadoqlash\n"
              "🚚 Shahar bo'ylab yetkazib berish\n💍 Uzuklar uchun o'lcham tanlash imkoniyati",
        "ru": "💎 <b>{shop}</b>\n\nМы предлагаем качественные и изысканные ювелирные украшения.\n\n"
              "✨ Каждое изделие проходит контроль качества\n🎁 Красивая подарочная упаковка\n"
              "🚚 Доставка по городу\n💍 Выбор размера для колец",
        "tg": "💎 <b>{shop}</b>\n\nМо ороишоти заргарии босифат ва зеборо пешниҳод мекунем.\n\n"
              "✨ Ҳар як маҳсулот аз назорати сифат гузаштааст\n🎁 Бастабандии зебои тӯҳфавӣ\n"
              "🚚 Расонидан дар саросари шаҳр\n💍 Интихоби андоза барои ангуштаринҳо",
        "kk": "💎 <b>{shop}</b>\n\nБіз сапалы әрі әсем зергерлік бұйымдарды ұсынамыз.\n\n"
              "✨ Әр бұйым сапа бақылауынан өтеді\n🎁 Әдемі сыйлық орамасы\n"
              "🚚 Қала бойынша жеткізу\n💍 Сақиналар үшін өлшем таңдау мүмкіндігі",
    },
    "contact_default": {
        "uz": "☎️ <b>Biz bilan bog'lanish</b>\n\n📞 Telefon: {phone}\n\n"
              "Savollaringiz bo'lsa, qo'ng'iroq qiling yoki Telegram orqali yozing — yordam berishdan xursandmiz! 💎",
        "ru": "☎️ <b>Связаться с нами</b>\n\n📞 Телефон: {phone}\n\n"
              "Если у вас есть вопросы — позвоните или напишите нам в Telegram, мы с радостью поможем! 💎",
        "tg": "☎️ <b>Тамос бо мо</b>\n\n📞 Телефон: {phone}\n\n"
              "Агар савол дошта бошед, занг занед ё дар Telegram нависед — бо хурсандӣ кӯмак мекунем! 💎",
        "kk": "☎️ <b>Бізбен байланыс</b>\n\n📞 Телефон: {phone}\n\n"
              "Сұрақтарыңыз болса, қоңырау шалыңыз немесе Telegram арқылы жазыңыз — көмектесуге қуаныштымыз! 💎",
    },
    "admin_appointed": {
        "uz": "🎉 Siz <b>{shop}</b> botida <b>admin</b> etib tayinlandingiz!\n\nPastdagi «⚙️ Admin panel» tugmasidan foydalaning.",
        "ru": "🎉 Вы назначены <b>администратором</b> бота <b>{shop}</b>!\n\nИспользуйте кнопку «⚙️ Admin panel» внизу.",
        "tg": "🎉 Шумо <b>админи</b> боти <b>{shop}</b> таъин шудед!\n\nАз тугмаи «⚙️ Admin panel» дар поён истифода баред.",
        "kk": "🎉 Сіз <b>{shop}</b> ботының <b>әкімшісі</b> болып тағайындалдыңыз!\n\nТөмендегі «⚙️ Admin panel» түймесін пайдаланыңыз.",
    },
    # ---------------- To'lov ----------------
    "choose_payment": {
        "uz": "💳 To'lov usulini tanlang:", "ru": "💳 Выберите способ оплаты:",
        "tg": "💳 Усули пардохтро интихоб кунед:", "kk": "💳 Төлем тәсілін таңдаңыз:",
    },
    "btn_pay_cash": {
        "uz": "💵 Naqd (qabul qilganda)", "ru": "💵 Наличными при получении",
        "tg": "💵 Нақд (ҳангоми гирифтан)", "kk": "💵 Алғанда қолма-қол",
    },
    "btn_pay_order": {"uz": "💳 #{id} ni to'lash", "ru": "💳 Оплатить №{id}", "tg": "💳 Пардохти №{id}", "kk": "💳 №{id} төлеу"},
    "invoice_title": {"uz": "Buyurtma #{id}", "ru": "Заказ №{id}", "tg": "Фармоиш №{id}", "kk": "Тапсырыс №{id}"},
    "invoice_desc": {
        "uz": "{shop} — zargarlik buyumlari: {items}", "ru": "{shop} — ювелирные украшения: {items}",
        "tg": "{shop} — ороишоти заргарӣ: {items}", "kk": "{shop} — зергерлік бұйымдар: {items}",
    },
    "pay_hint": {
        "uz": "👇 Quyidagi «To'lash» tugmasini bosing. To'lov {provider} orqali xavfsiz amalga oshiriladi.",
        "ru": "👇 Нажмите кнопку «Оплатить» ниже. Оплата проходит безопасно через {provider}.",
        "tg": "👇 Тугмаи «Пардохт»-ро дар поён пахш кунед. Пардохт тавассути {provider} бехатар анҷом дода мешавад.",
        "kk": "👇 Төмендегі «Төлеу» түймесін басыңыз. Төлем {provider} арқылы қауіпсіз жүзеге асады.",
    },
    "pay_ok": {
        "uz": "✅ <b>To'lov qabul qilindi!</b>\n\nBuyurtma #{id} uchun {amount} {provider} orqali to'landi. Rahmat! 💎",
        "ru": "✅ <b>Оплата получена!</b>\n\nЗаказ №{id} оплачен через {provider}: {amount}. Спасибо! 💎",
        "tg": "✅ <b>Пардохт қабул шуд!</b>\n\nФармоиши №{id} тавассути {provider} пардохт шуд: {amount}. Ташаккур! 💎",
        "kk": "✅ <b>Төлем қабылданды!</b>\n\n№{id} тапсырыс {provider} арқылы төленді: {amount}. Рахмет! 💎",
    },
    "pay_cash_ok": {
        "uz": "💵 Yaxshi! Buyurtma #{id} uchun to'lovni mahsulotni qabul qilganda naqd amalga oshirasiz.",
        "ru": "💵 Хорошо! Оплату заказа №{id} вы произведёте наличными при получении.",
        "tg": "💵 Хуб! Пардохти фармоиши №{id}-ро ҳангоми гирифтани маҳсулот нақд анҷом медиҳед.",
        "kk": "💵 Жақсы! №{id} тапсырыстың төлемін тауарды алғанда қолма-қол жасайсыз.",
    },
    "pay_unavailable": {
        "uz": "Bu buyurtmani to'lab bo'lmaydi: u bekor qilingan yoki allaqachon to'langan.",
        "ru": "Этот заказ нельзя оплатить: он отменён или уже оплачен.",
        "tg": "Ин фармоишро пардохт кардан мумкин нест: он бекор шудааст ё аллакай пардохт шудааст.",
        "kk": "Бұл тапсырысты төлеу мүмкін емес: ол тоқтатылған немесе бұрын төленген.",
    },
    "pay_failed": {
        "uz": "⚠️ Onlayn to'lovni boshlab bo'lmadi (summa chegaradan tashqarida bo'lishi mumkin). "
              "Iltimos, boshqa usulni tanlang yoki biz bilan bog'laning: {phone}",
        "ru": "⚠️ Не удалось начать онлайн-оплату (возможно, сумма вне допустимых пределов). "
              "Выберите другой способ или свяжитесь с нами: {phone}",
        "tg": "⚠️ Пардохти онлайнро оғоз кардан нашуд (шояд маблағ аз ҳад берун аст). "
              "Усули дигарро интихоб кунед ё бо мо тамос гиред: {phone}",
        "kk": "⚠️ Онлайн төлемді бастау мүмкін болмады (сома шектен тыс болуы мүмкін). "
              "Басқа тәсілді таңдаңыз немесе бізбен байланысыңыз: {phone}",
    },
    "payment": {"uz": "💳 To'lov", "ru": "💳 Оплата", "tg": "💳 Пардохт", "kk": "💳 Төлем"},
    "pay_status_paid": {"uz": "✅ To'langan ({method})", "ru": "✅ Оплачено ({method})", "tg": "✅ Пардохт шуд ({method})", "kk": "✅ Төленді ({method})"},
    "pay_status_cash": {"uz": "💵 Naqd, qabul qilganda", "ru": "💵 Наличными при получении", "tg": "💵 Нақд, ҳангоми гирифтан", "kk": "💵 Алғанда қолма-қол"},
    "pay_status_unpaid": {"uz": "⏳ To'lanmagan", "ru": "⏳ Не оплачено", "tg": "⏳ Пардохт нашудааст", "kk": "⏳ Төленбеген"},
    # ---------------- Bonus (💎 brilliant) ----------------
    "btn_bonus": {"uz": "💎 Brilliantlarim", "ru": "💎 Мои бриллианты", "tg": "💎 Бриллиантҳои ман", "kk": "💎 Бриллианттарым"},
    "bonus_info": {
        "uz": "💎 <b>Sizda: {n} ta brilliant</b>\n💰 Qiymati: <b>{value}</b>\n\n"
              "📌 <b>Qanday ishlaydi:</b>\n• Har {step} xarid uchun — 1 💎\n• 1 💎 = {one} chegirma\n"
              "• Brilliantlar buyurtma yetkazilgach hisobingizga tushadi\n"
              "• Keyingi xaridda chegirma sifatida ishlating yoki do'stingizga sovg'a qiling 🎁",
        "ru": "💎 <b>У вас: {n} бриллиант(ов)</b>\n💰 Стоимость: <b>{value}</b>\n\n"
              "📌 <b>Как это работает:</b>\n• За каждые {step} покупок — 1 💎\n• 1 💎 = скидка {one}\n"
              "• Бриллианты начисляются после доставки заказа\n"
              "• Используйте их как скидку при следующей покупке или подарите другу 🎁",
        "tg": "💎 <b>Шумо доред: {n} бриллиант</b>\n💰 Арзиш: <b>{value}</b>\n\n"
              "📌 <b>Чӣ тавр кор мекунад:</b>\n• Барои ҳар {step} харид — 1 💎\n• 1 💎 = тахфифи {one}\n"
              "• Бриллиантҳо пас аз расонидани фармоиш ба ҳисоби шумо мегузаранд\n"
              "• Онҳоро ҳамчун тахфиф дар хариди навбатӣ истифода баред ё ба дӯстатон тӯҳфа кунед 🎁",
        "kk": "💎 <b>Сізде: {n} бриллиант</b>\n💰 Құны: <b>{value}</b>\n\n"
              "📌 <b>Қалай жұмыс істейді:</b>\n• Әр {step} сатып алу үшін — 1 💎\n• 1 💎 = {one} жеңілдік\n"
              "• Бриллианттар тапсырыс жеткізілгеннен кейін есептеледі\n"
              "• Келесі сатып алуда жеңілдік ретінде пайдаланыңыз немесе досыңызға сыйлаңыз 🎁",
    },
    "bonus_history": {"uz": "🧾 <b>Oxirgi amallar:</b>", "ru": "🧾 <b>Последние операции:</b>", "tg": "🧾 <b>Амалҳои охирин:</b>", "kk": "🧾 <b>Соңғы операциялар:</b>"},
    "btx_earn": {"uz": "🛍 Xarid uchun", "ru": "🛍 За покупку", "tg": "🛍 Барои харид", "kk": "🛍 Сатып алу үшін"},
    "btx_spend": {"uz": "💳 Chegirmaga ishlatildi", "ru": "💳 Использовано как скидка", "tg": "💳 Барои тахфиф истифода шуд", "kk": "💳 Жеңілдікке жұмсалды"},
    "btx_refund": {"uz": "↩️ Qaytarildi", "ru": "↩️ Возвращено", "tg": "↩️ Баргардонида шуд", "kk": "↩️ Қайтарылды"},
    "btx_revoke": {"uz": "↩️ Bekor qilingan buyurtma", "ru": "↩️ Отменённый заказ", "tg": "↩️ Фармоиши бекоршуда", "kk": "↩️ Тоқтатылған тапсырыс"},
    "btx_transfer_in": {"uz": "🎁 Sovg'a olindi", "ru": "🎁 Получен подарок", "tg": "🎁 Тӯҳфа гирифта шуд", "kk": "🎁 Сыйлық алынды"},
    "btx_transfer_out": {"uz": "📤 Sovg'a yuborildi", "ru": "📤 Отправлен подарок", "tg": "📤 Тӯҳфа фиристода шуд", "kk": "📤 Сыйлық жіберілді"},
    "btx_admin": {"uz": "⚙️ Do'kondan sovg'a", "ru": "⚙️ Подарок от магазина", "tg": "⚙️ Тӯҳфа аз мағоза", "kk": "⚙️ Дүкеннен сыйлық"},
    "btn_send_bonus": {"uz": "🎁 Do'stga yuborish", "ru": "🎁 Отправить другу", "tg": "🎁 Ба дӯст фиристодан", "kk": "🎁 Досқа жіберу"},
    "btn_pick_contact": {"uz": "👤 Kontaktlardan tanlash", "ru": "👤 Выбрать из контактов", "tg": "👤 Аз контактҳо интихоб", "kk": "👤 Контактілерден таңдау"},
    "no_bonus": {
        "uz": "Sizda hali brilliant yo'q. Har {step} xarid uchun 1 💎 olasiz!",
        "ru": "У вас пока нет бриллиантов. За каждые {step} покупок — 1 💎!",
        "tg": "Шумо ҳоло бриллиант надоред. Барои ҳар {step} харид 1 💎 мегиред!",
        "kk": "Сізде әзірге бриллиант жоқ. Әр {step} сатып алу үшін 1 💎 аласыз!",
    },
    "ask_recipient": {
        "uz": "🎁 Kimga yubormoqchisiz?\n\n👇 «👤 Kontaktlardan tanlash» tugmasini bosing va odamni tanlang.",
        "ru": "🎁 Кому хотите отправить?\n\n👇 Нажмите «👤 Выбрать из контактов» и выберите человека.",
        "tg": "🎁 Ба кӣ фиристодан мехоҳед?\n\n👇 Тугмаи «👤 Аз контактҳо интихоб»-ро пахш карда, шахсро интихоб кунед.",
        "kk": "🎁 Кімге жібергіңіз келеді?\n\n👇 «👤 Контактілерден таңдау» түймесін басып, адамды таңдаңыз.",
    },
    "recipient_hint": {
        "uz": "Iltimos, «👤 Kontaktlardan tanlash» tugmasidan foydalaning.",
        "ru": "Пожалуйста, воспользуйтесь кнопкой «👤 Выбрать из контактов».",
        "tg": "Лутфан, аз тугмаи «👤 Аз контактҳо интихоб» истифода баред.",
        "kk": "«👤 Контактілерден таңдау» түймесін пайдаланыңыз.",
    },
    "self_send": {"uz": "O'zingizga yubora olmaysiz 🙂", "ru": "Нельзя отправить самому себе 🙂", "tg": "Ба худатон фиристода наметавонед 🙂", "kk": "Өзіңізге жібере алмайсыз 🙂"},
    "ask_bonus_amount": {
        "uz": "{name} ga nechta 💎 yuborasiz? (1 dan {n} gacha)",
        "ru": "Сколько 💎 отправить {name}? (от 1 до {n})",
        "tg": "Ба {name} чанд 💎 мефиристед? (аз 1 то {n})",
        "kk": "{name} қанша 💎 жібересіз? (1-ден {n}-ге дейін)",
    },
    "bad_bonus_amount": {
        "uz": "1 dan {n} gacha son kiriting.", "ru": "Введите число от 1 до {n}.",
        "tg": "Аз 1 то {n} рақам ворид кунед.", "kk": "1-ден {n}-ге дейін сан енгізіңіз.",
    },
    "confirm_send": {
        "uz": "🎁 <b>{name}</b> ga <b>{n} 💎</b> ({value}) yuborilsinmi?",
        "ru": "🎁 Отправить <b>{name}</b> <b>{n} 💎</b> ({value})?",
        "tg": "🎁 Ба <b>{name}</b> <b>{n} 💎</b> ({value}) фиристода шавад?",
        "kk": "🎁 <b>{name}</b> үшін <b>{n} 💎</b> ({value}) жіберілсін бе?",
    },
    "btn_send": {"uz": "✅ Yuborish", "ru": "✅ Отправить", "tg": "✅ Фиристодан", "kk": "✅ Жіберу"},
    "sent_ok": {
        "uz": "✅ <b>{name}</b> ga {n} 💎 yuborildi!\nQoldiq: {left} 💎",
        "ru": "✅ <b>{name}</b> отправлено {n} 💎!\nОстаток: {left} 💎",
        "tg": "✅ Ба <b>{name}</b> {n} 💎 фиристода шуд!\nБақия: {left} 💎",
        "kk": "✅ <b>{name}</b> үшін {n} 💎 жіберілді!\nҚалдық: {left} 💎",
    },
    "sent_not_started": {
        "uz": "ℹ️ U hali botni ochmagan. /start bosganda brilliantlarni ko'radi — bot havolasini unga yuboring: {link}",
        "ru": "ℹ️ Он(а) ещё не открывал(а) бота. Бриллианты будут видны после /start — отправьте ссылку: {link}",
        "tg": "ℹ️ Ӯ ҳанӯз ботро накушодааст. Пас аз /start бриллиантҳоро мебинад — пайвандро фиристед: {link}",
        "kk": "ℹ️ Ол әлі ботты ашпаған. /start басқанда бриллианттарды көреді — сілтемені жіберіңіз: {link}",
    },
    "send_failed": {
        "uz": "❗️ Yuborilmadi: brilliantlar yetarli emas.", "ru": "❗️ Не отправлено: недостаточно бриллиантов.",
        "tg": "❗️ Фиристода нашуд: бриллиант кифоя нест.", "kk": "❗️ Жіберілмеді: бриллиант жеткіліксіз.",
    },
    "bonus_received": {
        "uz": "🎁 <b>{name}</b> sizga <b>{n} 💎</b> sovg'a qildi! ({value})\nSizda jami: {total} 💎\n\nKeyingi xaridda chegirma sifatida ishlating 😊",
        "ru": "🎁 <b>{name}</b> подарил(а) вам <b>{n} 💎</b>! ({value})\nВсего у вас: {total} 💎\n\nИспользуйте их как скидку при следующей покупке 😊",
        "tg": "🎁 <b>{name}</b> ба шумо <b>{n} 💎</b> тӯҳфа кард! ({value})\nҲамагӣ дар шумо: {total} 💎\n\nДар хариди навбатӣ ҳамчун тахфиф истифода баред 😊",
        "kk": "🎁 <b>{name}</b> сізге <b>{n} 💎</b> сыйлады! ({value})\nСізде барлығы: {total} 💎\n\nКелесі сатып алуда жеңілдік ретінде пайдаланыңыз 😊",
    },
    "bonus_from_shop": {
        "uz": "🎁 Do'kondan sizga <b>{n} 💎</b> sovg'a! ({value})\nSizda jami: {total} 💎",
        "ru": "🎁 Подарок от магазина: <b>{n} 💎</b>! ({value})\nВсего у вас: {total} 💎",
        "tg": "🎁 Тӯҳфа аз мағоза: <b>{n} 💎</b>! ({value})\nҲамагӣ дар шумо: {total} 💎",
        "kk": "🎁 Дүкеннен сыйлық: <b>{n} 💎</b>! ({value})\nСізде барлығы: {total} 💎",
    },
    "ask_use_bonus": {
        "uz": "💎 Sizda <b>{n}</b> ta brilliant bor ({value}).\nBu buyurtmada <b>{use}</b> tasini ishlatib, <b>{disc}</b> chegirma olasizmi?",
        "ru": "💎 У вас <b>{n}</b> бриллиант(ов) ({value}).\nИспользовать <b>{use}</b> из них и получить скидку <b>{disc}</b>?",
        "tg": "💎 Шумо <b>{n}</b> бриллиант доред ({value}).\nДар ин фармоиш <b>{use}</b>-тоашро истифода бурда, <b>{disc}</b> тахфиф мегиред?",
        "kk": "💎 Сізде <b>{n}</b> бриллиант бар ({value}).\nОсы тапсырыста <b>{use}</b> данасын пайдаланып, <b>{disc}</b> жеңілдік аласыз ба?",
    },
    "btn_use_bonus": {"uz": "✅ Ha, ishlatish", "ru": "✅ Да, использовать", "tg": "✅ Ҳа, истифода", "kk": "✅ Иә, пайдалану"},
    "btn_keep_bonus": {"uz": "Yo'q, saqlab qo'yaman", "ru": "Нет, сохраню", "tg": "Не, нигоҳ медорам", "kk": "Жоқ, сақтаймын"},
    "bonus_discount_line": {"uz": "💎 Brilliantlar ({n} ta)", "ru": "💎 Бриллианты ({n} шт.)", "tg": "💎 Бриллиантҳо ({n} дона)", "kk": "💎 Бриллианттар ({n} дана)"},
    "to_pay": {"uz": "💰 To'lov uchun", "ru": "💰 К оплате", "tg": "💰 Барои пардохт", "kk": "💰 Төлеуге"},
    "bonus_will_earn": {
        "uz": "🎁 Bu buyurtma uchun: <b>+{n} 💎</b> (yetkazilgach)", "ru": "🎁 За этот заказ: <b>+{n} 💎</b> (после доставки)",
        "tg": "🎁 Барои ин фармоиш: <b>+{n} 💎</b> (пас аз расонидан)", "kk": "🎁 Осы тапсырыс үшін: <b>+{n} 💎</b> (жеткізілгеннен кейін)",
    },
    "bonus_got": {"uz": "🎁 Olingan bonus: <b>+{n} 💎</b>", "ru": "🎁 Получено: <b>+{n} 💎</b>", "tg": "🎁 Бонуси гирифташуда: <b>+{n} 💎</b>", "kk": "🎁 Алынған бонус: <b>+{n} 💎</b>"},
    "bonus_earned_msg": {
        "uz": "🎉 Buyurtma #{id} uchun hisobingizga <b>+{n} 💎</b> tushdi!\nSizda jami: {total} 💎 ({value})",
        "ru": "🎉 За заказ №{id} вам начислено <b>+{n} 💎</b>!\nВсего у вас: {total} 💎 ({value})",
        "tg": "🎉 Барои фармоиши №{id} ба ҳисоби шумо <b>+{n} 💎</b> гузашт!\nҲамагӣ: {total} 💎 ({value})",
        "kk": "🎉 №{id} тапсырыс үшін <b>+{n} 💎</b> есептелді!\nБарлығы: {total} 💎 ({value})",
    },
    "bonus_refund_msg": {
        "uz": "↩️ Buyurtma #{id} bekor qilingani uchun {n} 💎 hisobingizga qaytarildi.",
        "ru": "↩️ Заказ №{id} отменён — {n} 💎 возвращены на ваш счёт.",
        "tg": "↩️ Фармоиши №{id} бекор шуд — {n} 💎 ба ҳисоби шумо баргардонида шуд.",
        "kk": "↩️ №{id} тапсырыс тоқтатылды — {n} 💎 шотыңызға қайтарылды.",
    },
    "paid_by_bonus": {
        "uz": "💎 Buyurtma to'liq brilliantlar bilan to'landi — qo'shimcha to'lov kerak emas!",
        "ru": "💎 Заказ полностью оплачен бриллиантами — доплата не нужна!",
        "tg": "💎 Фармоиш пурра бо бриллиантҳо пардохт шуд — пардохти иловагӣ лозим нест!",
        "kk": "💎 Тапсырыс толығымен бриллианттармен төленді — қосымша төлем қажет емес!",
    },
    # ---------------- Sayt (Mini App) va video ----------------
    "btn_video": {"uz": "🎬 Videoni ko'rish", "ru": "🎬 Смотреть видео", "tg": "🎬 Тамошои видео", "kk": "🎬 Бейнені көру"},
    "btn_open_shop": {"uz": "🛍 Do'konni ochish", "ru": "🛍 Открыть магазин", "tg": "🛍 Кушодани мағоза", "kk": "🛍 Дүкенді ашу"},
    "menu_shop": {"uz": "🛍 Do'kon", "ru": "🛍 Магазин", "tg": "🛍 Мағоза", "kk": "🛍 Дүкен"},
    "open_shop_hint": {
        "uz": "🛍 Do'konimizni chiroyli ko'rinishda oching — rasm va videolar bilan:",
        "ru": "🛍 Откройте наш магазин в удобном виде — с фото и видео:",
        "tg": "🛍 Мағозаи моро дар намуди зебо кушоед — бо акс ва видео:",
        "kk": "🛍 Дүкенімізді әдемі көріністе ашыңыз — фото және бейнелермен:",
    },
    # ---------------- Aksiya ----------------
    "promo_title_1111": {
        "uz": "🔥 11.11 MEGA AKSIYA", "ru": "🔥 МЕГА-АКЦИЯ 11.11",
        "tg": "🔥 МЕГА-АКСИЯИ 11.11", "kk": "🔥 11.11 МЕГА-АКЦИЯСЫ",
    },
    "promo_title_custom": {"uz": "🔥 AKSIYA", "ru": "🔥 АКЦИЯ", "tg": "🔥 АКСИЯ", "kk": "🔥 АКЦИЯ"},
    "promo_all": {
        "uz": "Barcha mahsulotlarga <b>{p}%</b> chegirma!", "ru": "Скидка <b>{p}%</b> на все товары!",
        "tg": "Тахфифи <b>{p}%</b> ба ҳамаи маҳсулотҳо!", "kk": "Барлық тауарларға <b>{p}%</b> жеңілдік!",
    },
    "promo_cat": {
        "uz": "«{cat}» bo'limiga <b>{p}%</b> chegirma!", "ru": "Скидка <b>{p}%</b> на раздел «{cat}»!",
        "tg": "Тахфифи <b>{p}%</b> ба бахши «{cat}»!", "kk": "«{cat}» бөліміне <b>{p}%</b> жеңілдік!",
    },
    "promo_ends_in": {"uz": "⏰ Tugashiga: {left}", "ru": "⏰ До конца: {left}", "tg": "⏰ То анҷом: {left}", "kk": "⏰ Аяқталуына: {left}"},
    "promo_starts_in": {
        "uz": "⏳ Boshlanishiga: {left}", "ru": "⏳ До начала: {left}",
        "tg": "⏳ То оғоз: {left}", "kk": "⏳ Басталуына: {left}",
    },
    "promo_footer": {
        "uz": "Shoshiling, aksiya muddati cheklangan! 👇", "ru": "Спешите, акция ограничена по времени! 👇",
        "tg": "Шитобед, мӯҳлати аксия маҳдуд аст! 👇", "kk": "Асығыңыз, акция уақыты шектеулі! 👇",
    },
    "no_promo": {
        "uz": "Hozircha faol aksiya yo'q. Yangiliklarni kanalimizda kuzatib boring! 📢",
        "ru": "Сейчас активных акций нет. Следите за новостями в нашем канале! 📢",
        "tg": "Ҳоло аксияи фаъол нест. Хабарҳоро дар канали мо пайгирӣ кунед! 📢",
        "kk": "Қазір белсенді акция жоқ. Жаңалықтарды арнамыздан қадағалаңыз! 📢",
    },
    "dur_d": {"uz": "kun", "ru": "дн.", "tg": "рӯз", "kk": "күн"},
    "dur_h": {"uz": "soat", "ru": "ч", "tg": "соат", "kk": "сағ"},
    "dur_m": {"uz": "daqiqa", "ru": "мин", "tg": "дақиқа", "kk": "мин"},
}

# Sayt (Mini App) uchun qo'shimcha matnlar
WEB_TEXTS: dict[str, dict[str, str]] = {
    "search": {"uz": "Qidirish...", "ru": "Поиск...", "tg": "Ҷустуҷӯ...", "kk": "Іздеу..."},
    "all": {"uz": "Hammasi", "ru": "Все", "tg": "Ҳама", "kk": "Барлығы"},
    "nothing_found": {"uz": "Hech narsa topilmadi", "ru": "Ничего не найдено", "tg": "Ҳеҷ чиз ёфт нашуд", "kk": "Ештеңе табылмады"},
    "add_to_cart": {"uz": "Savatga qo'shish", "ru": "Добавить в корзину", "tg": "Ба сабад илова", "kk": "Себетке қосу"},
    "added": {"uz": "Savatga qo'shildi ✓", "ru": "Добавлено в корзину ✓", "tg": "Ба сабад илова шуд ✓", "kk": "Себетке қосылды ✓"},
    "go_cart": {"uz": "Savatga o'tish", "ru": "Перейти в корзину", "tg": "Ба сабад гузаштан", "kk": "Себетке өту"},
    "cart": {"uz": "Savat", "ru": "Корзина", "tg": "Сабад", "kk": "Себет"},
    "cart_empty": {"uz": "Savat bo'sh", "ru": "Корзина пуста", "tg": "Сабад холӣ аст", "kk": "Себет бос"},
    "checkout": {"uz": "Rasmiylashtirish", "ru": "Оформить заказ", "tg": "Ба расмият даровардан", "kk": "Ресімдеу"},
    "name": {"uz": "Ismingiz", "ru": "Ваше имя", "tg": "Номи шумо", "kk": "Атыңыз"},
    "phone": {"uz": "Telefon raqamingiz", "ru": "Номер телефона", "tg": "Рақами телефон", "kk": "Телефон нөмірі"},
    "address": {"uz": "Yetkazib berish manzili", "ru": "Адрес доставки", "tg": "Суроғаи расонидан", "kk": "Жеткізу мекенжайы"},
    "comment": {"uz": "Izoh (ixtiyoriy)", "ru": "Комментарий (необязательно)", "tg": "Шарҳ (ихтиёрӣ)", "kk": "Пікір (міндетті емес)"},
    "comment_ph": {
        "uz": "Sovg'a qadoqlash, otkritka yozuvi, qulay vaqt...", "ru": "Подарочная упаковка, текст открытки, удобное время...",
        "tg": "Бастабандии тӯҳфавӣ, матни открытка, вақти мувофиқ...", "kk": "Сыйлық орамасы, ашықхат мәтіні, ыңғайлы уақыт...",
    },
    "place_order": {"uz": "Buyurtma berish", "ru": "Оформить заказ", "tg": "Фармоиш додан", "kk": "Тапсырыс беру"},
    "use_bonus": {
        "uz": "{n} 💎 ishlatish (−{value})", "ru": "Использовать {n} 💎 (−{value})",
        "tg": "Истифодаи {n} 💎 (−{value})", "kk": "{n} 💎 пайдалану (−{value})",
    },
    "subtotal": {"uz": "Mahsulotlar", "ru": "Товары", "tg": "Маҳсулотҳо", "kk": "Тауарлар"},
    "order_done": {"uz": "Buyurtma qabul qilindi!", "ru": "Заказ принят!", "tg": "Фармоиш қабул шуд!", "kk": "Тапсырыс қабылданды!"},
    "order_done_text": {
        "uz": "Buyurtma #{id} rasmiylashtirildi. To'lov usulini bot chatida tanlang — u yerga xabar yubordik.",
        "ru": "Заказ №{id} оформлен. Выберите способ оплаты в чате с ботом — мы отправили туда сообщение.",
        "tg": "Фармоиши №{id} ба расмият дароварда шуд. Усули пардохтро дар чати бот интихоб кунед — мо ба он ҷо паём фиристодем.",
        "kk": "№{id} тапсырыс ресімделді. Төлем тәсілін бот чатында таңдаңыз — біз сол жерге хабар жібердік.",
    },
    "go_chat": {"uz": "Chatga qaytish", "ru": "Вернуться в чат", "tg": "Бозгашт ба чат", "kk": "Чатқа оралу"},
    "continue_shopping": {"uz": "Xaridni davom ettirish", "ru": "Продолжить покупки", "tg": "Идомаи харид", "kk": "Сатып алуды жалғастыру"},
    "photo": {"uz": "Rasm", "ru": "Фото", "tg": "Акс", "kk": "Фото"},
    "video": {"uz": "Video", "ru": "Видео", "tg": "Видео", "kk": "Бейне"},
    "description": {"uz": "Tavsif", "ru": "Описание", "tg": "Тавсиф", "kk": "Сипаттама"},
    "size": {"uz": "O'lcham", "ru": "Размер", "tg": "Андоза", "kk": "Өлшем"},
    "color": {"uz": "Rang", "ru": "Цвет", "tg": "Ранг", "kk": "Түсі"},
    "quantity": {"uz": "Miqdor", "ru": "Количество", "tg": "Миқдор", "kk": "Саны"},
    "open_in_telegram": {
        "uz": "Bu sahifani Telegram'dagi @{bot} bot orqali oching.", "ru": "Откройте эту страницу через бота @{bot} в Telegram.",
        "tg": "Ин саҳифаро тавассути боти @{bot} дар Telegram кушоед.", "kk": "Бұл бетті Telegram-дағы @{bot} боты арқылы ашыңыз.",
    },
    "error": {"uz": "Xatolik yuz berdi. Qayta urinib ko'ring.", "ru": "Произошла ошибка. Попробуйте ещё раз.", "tg": "Хатогӣ рух дод. Боз кӯшиш кунед.", "kk": "Қате орын алды. Қайта көріңіз."},
    "fill_required": {"uz": "Iltimos, maydonlarni to'g'ri to'ldiring", "ru": "Пожалуйста, заполните поля правильно", "tg": "Лутфан, майдонҳоро дуруст пур кунед", "kk": "Өрістерді дұрыс толтырыңыз"},
    "your_bonus": {"uz": "Brilliantlaringiz", "ru": "Ваши бриллианты", "tg": "Бриллиантҳои шумо", "kk": "Бриллианттарыңыз"},
    "language": {"uz": "Til", "ru": "Язык", "tg": "Забон", "kk": "Тіл"},
}

# Har bir kalit uchun barcha tillar borligini tekshirish (dasturchi xatolarini erta topish)
for _key, _vals in [*TEXTS.items(), *WEB_TEXTS.items()]:
    assert set(_vals) == set(LANGS), f"Tarjima yetishmaydi: {_key}"


def t(key: str, lang: str, **kwargs) -> str:
    text = TEXTS[key].get(lang) or TEXTS[key][DEFAULT_LANG]
    return text.format(**kwargs) if kwargs else text


def all_texts(key: str) -> set[str]:
    """Tugma matnlarini barcha tillarda olish (handler filtrlarida ishlatiladi)."""
    return set(TEXTS[key].values())


def guess_lang(language_code: str | None) -> str:
    code = (language_code or "").split("-")[0].lower()
    return code if code in LANGS else DEFAULT_LANG


def fmt_duration(seconds: float, lang: str) -> str:
    seconds = max(int(seconds), 60)
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days} {t('dur_d', lang)}")
    if hours:
        parts.append(f"{hours} {t('dur_h', lang)}")
    if minutes and not days:
        parts.append(f"{minutes} {t('dur_m', lang)}")
    return " ".join(parts)


# ---------------- Ko'p tilli nomlar (kategoriya, mahsulot) ----------------
def parse_multilang(text: str) -> tuple[str, str | None]:
    """Admin «O'zbekcha | Русский | Тоҷикӣ | Қазақша» ko'rinishida yozishi mumkin.
    Qaytaradi: (asosiy matn, JSON tarjimalar yoki None)."""
    parts = [p.strip() for p in text.split("|")]
    if len(parts) == 1:
        return parts[0], None
    translations = {lang: value for lang, value in zip(LANGS, parts) if value}
    return parts[0], json.dumps(translations, ensure_ascii=False)


def loc(row: dict, field: str, lang: str) -> str | None:
    """Yozuvning tarjima qilingan maydonini qaytaradi (bo'lmasa — asosiy qiymat)."""
    raw = row.get(f"{field}_i18n")
    if raw:
        try:
            value = json.loads(raw).get(lang)
            if value:
                return value
        except (ValueError, AttributeError):
            pass
    return row.get(field)


# ---------------- Middleware: har bir so'rovga foydalanuvchi tilini qo'shadi ----------------
_lang_cache: dict[int, str] = {}


def remember_lang(user_id: int, lang: str):
    _lang_cache[user_id] = lang


class LangMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        import db  # aylanma importdan qochish uchun

        user = data.get("event_from_user")
        lang = DEFAULT_LANG
        if user:
            lang = _lang_cache.get(user.id)
            if not lang:
                lang = await db.get_user_lang(user.id)
                if lang:
                    _lang_cache[user.id] = lang
                else:
                    lang = guess_lang(user.language_code)
        data["lang"] = lang
        return await handler(event, data)
