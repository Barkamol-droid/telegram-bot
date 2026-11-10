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

# Har bir kalit uchun barcha tillar borligini tekshirish (dasturchi xatolarini erta topish)
for _key, _vals in TEXTS.items():
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
