# 🛍 Do'kon bot (aiogram 3)

Telegram orqali mahsulot sotish uchun bot: katalog, savat, buyurtma berish va admin panel.

## Imkoniyatlar

**Mijozlar uchun**
- 🛍 Katalog — kategoriyalar va mahsulotlar (rasm, tavsif, narx)
- ➖/➕ miqdor tanlash va savatga qo'shish
- 🛒 Savat — ko'rish, mahsulotni olib tashlash, tozalash
- ✅ Buyurtma berish — ism, telefon (kontakt tugmasi), manzil yoki joylashuv, tasdiqlash
- 📦 Buyurtmalarim — oxirgi buyurtmalar va ularning holati
- 🔔 Buyurtma holati o'zgarganda xabarnoma

**Adminlar uchun** (`/admin` yoki «⚙️ Admin panel»)
- Kategoriya / mahsulot qo'shish va o'chirish
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
