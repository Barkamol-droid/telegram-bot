# 💎 Azure Jewelry — zargarlik do'koni boti (aiogram 3)

Telegram orqali zargarlik buyumlarini sotish uchun bot: katalog, uzuk o'lchamini tanlash, savat,
buyurtma berish va admin panel.

## Imkoniyatlar

**Mijozlar uchun**
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
| `DB_PATH`      | SQLite fayl nomi (standart: `shop.db`)                        |
| `SHOP_NAME`    | Do'kon nomi (standart: `Azure Jewelry`)                      |
| `CHANNEL`      | Telegram kanal (standart: `@azure_jewelry`, bo'sh — tugma chiqmaydi) |
| `ABOUT_TEXT`   | «💎 Biz haqimizda» matni (ixtiyoriy)                          |
| `CONTACT_TEXT` | «☎️ Aloqa» tugmasi matni (`\n` — yangi qator)                 |

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
SQLite fayli saqlanib qolishi uchun hostingda doimiy disk (volume) ulang.
