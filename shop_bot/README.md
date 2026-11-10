# 💎 Azure Jewelry — zargarlik do'koni boti (aiogram 3)

Telegram orqali zargarlik buyumlarini sotish uchun bot: 4 tilda (🇺🇿 o'zbek, 🇷🇺 rus, 🇹🇯 tojik, 🇰🇿 qozoq),
aksiyalar (masalan 11.11), uzuk o'lchamini tanlash, savat, buyurtma berish va admin panel.

## Imkoniyatlar

**Mijozlar uchun**
- 🌐 Til tanlash: birinchi /start da va «🌐 Til» tugmasi orqali (o'zbek, rus, tojik, qozoq)
- 🔥 Aksiya: chegirmali narxlar (eski narx chizilgan), tugashigacha qolgan vaqt, savatda «Tejadingiz»
- 🛍 Katalog — kategoriyalar va mahsulotlar (rasm, tavsif, narx)
- 📏 O'lcham tanlash (uzuk, zanjir va h.k.) — o'lchami bor mahsulotni o'lchamsiz savatga qo'shib bo'lmaydi
- ➖/➕ miqdor tanlash va savatga qo'shish
- 🛒 Savat — ko'rish, mahsulotni olib tashlash, tozalash
- ✅ Buyurtma berish — ism, telefon (kontakt tugmasi), manzil yoki joylashuv, izoh (sovg'a qadoqlash,
  otkritka yozuvi), tasdiqlash
- 💎 Biz haqimizda, 📢 Kanalimiz, ☎️ Aloqa
- 📦 Buyurtmalarim — oxirgi buyurtmalar va ularning holati
- 🔔 Buyurtma holati o'zgarganda xabarnoma

**Adminlar uchun** (`/admin` yoki «⚙️ Admin panel»)
- 🔥 Aksiya: foiz (1–90%), barcha mahsulotlar yoki bitta kategoriya, muddat («Faqat 11.11 kuni»,
  «Hozirdan 11.11 oxirigacha» yoki istalgan sana). Aksiya o'zi boshlanadi va o'zi tugaydi.
  «📢 Mijozlarga e'lon qilish» — har bir mijozga o'z tilida xabar; «👁 Mijozlar qanday ko'radi» — 4 tilda ko'rish
- Mahsulot/kategoriya nomini 4 tilda kiritish: `O'zbekcha | Русский | Тоҷикӣ | Қазақша`
- Kategoriya / mahsulot qo'shish (rasm, tavsif, narx, o'lchamlar) va o'chirish
- Birinchi ishga tushirishda tayyor kategoriyalar yaratiladi: Uzuklar, Sirg'alar, Zanjirlar,
  Bilakuzuklar, Kulonlar, To'plamlar
- Yangi buyurtmalar haqida darhol xabar + holatni o'zgartirish tugmalari
  (Qabul qilindi / Yetkazildi / Bekor qilindi)
- 📋 Buyurtmalar ro'yxati, `/order 12` — batafsil ko'rish
- 📊 Statistika (foydalanuvchilar, buyurtmalar, tushum)
- 📢 Barcha foydalanuvchilarga xabar yuborish (matn, rasm, video)

## O'rnatish

```bash
cd shop_bot
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # so'ng .env ichini to'ldiring
python main.py
```

`.env` sozlamalari:

| O'zgaruvchi    | Tavsif                                                        |
|----------------|---------------------------------------------------------------|
| `BOT_TOKEN`    | [@BotFather](https://t.me/BotFather) dan olingan token        |
| `ADMIN_IDS`    | Adminlar Telegram ID lari, vergul bilan (ID ni @userinfobot dan bilish mumkin) |
| `DATABASE_URL` | PostgreSQL manzili (ixtiyoriy). Berilsa, SQLite o'rniga PostgreSQL ishlatiladi |
| `DB_PATH`      | SQLite fayl nomi (standart: `shop.db`)                        |
| `SHOP_NAME`    | Do'kon nomi (standart: `Azure Jewelry`)                      |
| `CHANNEL`      | Telegram kanal (standart: `@azure_jewelry`, bo'sh — tugma chiqmaydi) |
| `ABOUT_TEXT`   | «💎 Biz haqimizda» matni (ixtiyoriy)                          |
| `TIMEZONE`     | Vaqt mintaqasi (standart: `Asia/Tashkent`) — aksiya vaqti shu bo'yicha |
| `CONTACT_TEXT` | «☎️ Aloqa» tugmasi matni (`\n` — yangi qator). Tilga xos: `CONTACT_TEXT_RU`, `_TG`, `_KK` |

> ⚠️ Tokenni hech qachon kodga yozmang va GitHub'ga yuklamang — faqat `.env` yoki hosting
> sozlamalaridagi environment variable orqali bering.

## Fayllar tuzilishi

```
shop_bot/
├── main.py          # ishga tushirish
├── config.py        # sozlamalar (.env)
├── db.py            # SQLite bilan ishlash
├── keyboards.py     # tugmalar va matnlar
├── states.py        # FSM holatlari
└── handlers/
    ├── common.py    # /start, bekor qilish
    ├── user.py      # katalog, savat, buyurtma
    └── admin.py     # admin panel
```

## Serverga joylash

`Procfile` (`worker: python main.py`) mavjud — Railway, Render yoki Heroku'da **Root directory**
sifatida `shop_bot` ni ko'rsating va `BOT_TOKEN`, `ADMIN_IDS` ni environment variable qilib qo'shing.
Ma'lumotlar o'chib ketmasligi uchun ikki yo'l bor:
- **PostgreSQL (tavsiya):** Railway'da `+ Add → Database → PostgreSQL` qo'shing va bot servisi
  Variables bo'limiga `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` yozing.
- **Volume:** `/data` ga volume ulab, `DB_PATH=/data/shop.db` qiling.
