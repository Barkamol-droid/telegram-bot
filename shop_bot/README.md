# 💎 Azure Jewelry — zargarlik do'koni boti (aiogram 3)

Telegram orqali zargarlik buyumlarini sotish uchun bot: 4 tilda (🇺🇿 o'zbek, 🇷🇺 rus, 🇹🇯 tojik, 🇰🇿 qozoq),
aksiyalar (masalan 11.11), uzuk o'lchamini tanlash, savat, buyurtma berish va admin panel.

## Imkoniyatlar

**Mijozlar uchun**
- 🛍 **Sayt ko'rinishi (Telegram Mini App)**: bot ichida ochiladigan do'kon — mahsulot kartochkalari, qidiruv,
  kategoriyalar, rasm va 🎬 video, logotip va ikonka — botning Telegram avatari, o'lcham tanlash, savat, brilliantlar, buyurtma berish. Telegram mavzusiga
  (yorug'/qorong'i) moslashadi, 4 tilda. Chat menyusidagi «🛍 Do'kon» tugmasi yoki «🛍 Katalog» orqali ochiladi
- 📦 Qoldiq: «📦 Mavjud: 5 dona», «⚠️ Faqat 2 ta qoldi!», «❌ Hozircha tugagan» — botda va saytda;
  mavjudidan ko'p savatga qo'shib/buyurtma qilib bo'lmaydi
- 🖼 Bir nechta rasm (10 tagacha): botda ⬅️ ➡️ bilan, saytda barmoq bilan suriladigan galereya
- 🎬 Mahsulot videosi: bot chatida ham («🎬 Videoni ko'rish»), saytda ham
- 🌐 Til tanlash: birinchi /start da va «🌐 Til» tugmasi orqali (o'zbek, rus, tojik, qozoq)
- 🔥 Aksiya: chegirmali narxlar (eski narx chizilgan), tugashigacha qolgan vaqt, savatda «Tejadingiz»
- 🛍 Katalog — kategoriyalar va mahsulotlar (rasm, tavsif, narx)
- 🎨 Rang tanlash (Sariq/Oq/Qizil oltin, Kumush, Platina, Qora yoki o'z ranglaringiz) — botda va saytda
- 📏 O'lcham tanlash (uzuk, zanjir va h.k.) — o'lchami bor mahsulotni o'lchamsiz savatga qo'shib bo'lmaydi
- ➖/➕ miqdor tanlash va savatga qo'shish
- 🛒 Savat — ko'rish, mahsulotni olib tashlash, tozalash
- ✅ Buyurtma berish — ism, telefon (kontakt tugmasi), manzil yoki joylashuv, izoh (sovg'a qadoqlash,
  otkritka yozuvi), tasdiqlash
- 💎 Biz haqimizda, 📢 Kanalimiz, ☎️ Aloqa
- 💳 To'lov: Click, Payme (Telegram ichida, kartadan) yoki naqd — qabul qilganda
- 💎 Brilliantlar (bonus): har 100 000 so'm xarid uchun 1 💎 (buyurtma yetkazilgach), 1 💎 = 1 000 so'm
  chegirma; keyingi xaridda ishlatish yoki do'stga (kontaktlardan tanlab) sovg'a qilish mumkin
- 📦 Buyurtmalarim — oxirgi buyurtmalar va ularning holati
- 🔔 Buyurtma holati o'zgarganda xabarnoma

**Adminlar uchun** (`/admin` yoki «⚙️ Admin panel»)
- 🔥 Aksiya: foiz (1–90%), barcha mahsulotlar yoki bitta kategoriya, muddat («Faqat 11.11 kuni»,
  «Hozirdan 11.11 oxirigacha» yoki istalgan sana). Aksiya o'zi boshlanadi va o'zi tugaydi.
  «📢 Mijozlarga e'lon qilish» — har bir mijozga o'z tilida xabar; «👁 Mijozlar qanday ko'radi» — 4 tilda ko'rish
- 💎 Brilliantlar: buyurtma «🚚 Yetkazildi» qilinganda mijozga avtomatik beriladi; bekor qilinsa,
  ishlatilganlari qaytariladi. `/bonus ID SON` — mijozga brilliant sovg'a qilish. Statistikada jami brilliantlar
- 📦 **Qoldiq**: mahsulot qo'shishda «nechta bor» so'raladi (o'tkazib yuborilsa — soni hisoblanmaydi);
  buyurtmada avtomatik kamayadi, bekor qilinsa qaytadi; tugasa yoki 3 tadan kam qolsa — adminga ogohlantirish.
  Bir vaqtdagi buyurtmalarda oxirgi dona faqat bitta mijozga sotiladi
- ✏️ **Mahsulotni tahrirlash**: nom, tavsif, narx, o'lchamlar, ranglar, kategoriya, rasmlar (qo'shish /
  almashtirish / o'chirish), video va tarjimalarni (har bir tilni alohida) mahsulotni o'chirmasdan o'zgartirish
- 🖼 Mahsulot qo'shishda bir nechta rasm yoki albom yuborish, so'ng «✔️ Tayyor»
- 🎨 Ranglar: mahsulot qo'shishda tayyor ranglarni belgilash yoki o'z rangini yozish (`Yashil | Зелёный | Сабз | Жасыл`);
  mavjud mahsulot ranglari — «✏️ Mahsulotni tahrirlash» → mahsulot → «🎨 Ranglar»
- 🎬 Rasm / video: mahsulot qo'shishda video yuklash va mavjud mahsulotning rasm/videosini almashtirish
- 👥 Adminlar: bosh admin yangi adminni telefon kontaktlaridan tanlab (yoki ID orqali) qo'shadi va o'chiradi.
  Qo'shilgan adminlar buyurtmalarni oladi, mahsulot va aksiyalarni boshqaradi
- 🌐 **Avtomatik tarjima**: nom, tavsif, kategoriya va rangni o'zbekcha yozasiz — bot rus, tojik, qozoq
  tillariga o'zi tarjima qiladi va tarjimani ko'rsatadi (Claude — `ANTHROPIC_API_KEY` bo'lsa; aks holda bepul MyMemory)
- Mahsulot/kategoriya nomini 4 tilda qo'lda kiritish ham mumkin: `O'zbekcha | Русский | Тоҷикӣ | Қазақша`
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
| `SHOP_PHONE`   | «☎️ Aloqa» da ko'rsatiladigan telefon (standart: `+998900441678`) |
| `CLICK_TOKEN`  | Click provider token (BotFather → Payments). Bo'lmasa, Click tugmasi chiqmaydi |
| `PAYME_TOKEN`  | Payme provider token (BotFather → Payments). Bo'lmasa, Payme tugmasi chiqmaydi |
| `BONUS_STEP`   | Necha so'm xarid uchun 1 💎 (standart: `100000`) |
| `BONUS_VALUE`  | 1 💎 qiymati, so'mda (standart: `1000`) |
| `WEBAPP_URL`   | Sayt manzili (Railway'da shart emas — `RAILWAY_PUBLIC_DOMAIN` dan olinadi) |
| `ANTHROPIC_API_KEY` | Claude orqali sifatli avtomatik tarjima (ixtiyoriy; bo'lmasa — bepul xizmat) |
| `AUTO_TRANSLATE` | `0` — avtomatik tarjimani o'chirish |
| `COURIER_BOT_TOKEN` | Kuryer boti tokeni (ixtiyoriy) |
| `TIMEZONE`     | Vaqt mintaqasi (standart: `Asia/Tashkent`) — aksiya vaqti shu bo'yicha |
| `CONTACT_TEXT` | «☎️ Aloqa» tugmasi matni (`\n` — yangi qator). Tilga xos: `CONTACT_TEXT_RU`, `_TG`, `_KK` |

> ⚠️ Tokenni hech qachon kodga yozmang va GitHub'ga yuklamang — faqat `.env` yoki hosting
> sozlamalaridagi environment variable orqali bering.

## Sayt ko'rinishi (Mini App) ni yoqish

Bot o'zi ichida veb-server ishga tushiradi (`PORT`, standart 8080). Telegram Mini App uchun HTTPS manzil kerak:

1. Railway → servis → **Settings → Networking → Generate Domain** (port so'ralsa: `8080`).
2. Railway `RAILWAY_PUBLIC_DOMAIN` ni avtomatik beradi — bot uni o'zi topadi. Boshqa hostingda `WEBAPP_URL=https://...` bering.
3. Qayta deploy qiling. Chat menyusida «🛍 Do'kon» tugmasi paydo bo'ladi.

Rasmlar va videolar Telegram'dan olinib, serverda keshlanadi. Bot API cheklovi sababli saytda **20 MB gacha**
videolar ko'rinadi (botda — istalgan hajmda).

## Brauzer va telefon ilovasi (PWA) — Telegram orqali kirish

Do'kon Telegram'dan tashqarida ham ochiladi: `https://<domen>/` — mijoz «Log in with Telegram» orqali kiradi
(savat, buyurtmalar, brilliantlar bot bilan umumiy) va «📲» tugmasi bilan telefon ekraniga ilova qilib o'rnatadi.

1. @BotFather → `/setdomain` → botni tanlang → Railway domenini yozing (masalan `worker-production-xxxx.up.railway.app`,
   `https://` siz). Busiz «Log in with Telegram» tugmasi «Bot domain invalid» deydi.
2. Kirishda mijoz botga xabar yozishga ruxsat beradi — buyurtma xulosasi va Click/Payme to'lov tugmalari Telegram'ga keladi.
3. Sessiya — 30 kunlik HttpOnly cookie; «🌐 → 🚪 Chiqish» bilan chiqiladi.

## 🛵 Kuryer boti

Buyurtmalar alohida kuryer botiga keladi; kuryer «📦 Oldim → 🚚 Yo'ldaman → ✅ Topshirdim» bosqichlarini belgilaydi.

1. @BotFather → `/newbot` → kuryerlar uchun yangi bot (masalan `@AzureKuryerBot`); tokenini Railway Variables'ga
   `COURIER_BOT_TOKEN` sifatida qo'shing va Deploy qiling.
2. Kuryer shu botga `/start` bosib telefon raqamini yuboradi → asosiy botda adminga «✅ Tasdiqlash / ❌ Rad etish».
3. Yangi buyurtma barcha faol kuryerlarga boradi (mijoz ismi/telefoni — faqat olgan kuryerga). Birinchi «📦 Oldim»
   bosgan oladi (bir vaqtda bosilsa ham faqat bittasi); mijoz har bosqichda o'z tilida xabar oladi; «Topshirdim» —
   buyurtma «Yetkazildi», brilliantlar beriladi. Admin bekor qilsa — kuryerlarga xabar boradi.
4. Admin panel → «🛵 Kuryerlar» — ro'yxat, faollashtirish / o'chirish, shu oydagi yetkazishlar va haqlar.
5. 💰 Kuryer haqi: «🛵 Kuryerlar → 💰 Standart haqni o'zgartirish» — har yangi buyurtmaga qo'yiladi; alohida buyurtmada
   admin xabaridagi «💰 Kuryer haqi» bilan o'zgartiriladi (kuryer olishidan oldin ham, keyin ham). Kuryerda «💰 Hisobim».
6. 🔒 Maxfiylik: buyurtmani bir kuryer olsa — boshqalarda manzil o'chadi; «Topshirdim» yoki bekor qilinganda —
   kuryer chatidan mijoz manzili, ismi, telefoni va lokatsiyasi o'chiriladi.

## Onlayn to'lov (Click, Payme)

To'lov **Telegram Payments** orqali ishlaydi — alohida server yoki domen kerak emas.

1. @BotFather → `/mybots` → bot → **Payments** → **Click Uzbekistan** yoki **Payme**.
2. Avval **TEST** tokenni oling (`...:TEST:...`) — haqiqiy pul yechilmaydi, sinab ko'rish uchun.
3. Tokenni Railway Variables'ga `CLICK_TOKEN` / `PAYME_TOKEN` sifatida qo'ying.
4. Haqiqiy to'lov uchun Click/Payme bilan **merchant shartnoma** tuzing (MChJ yoki YaTT kerak),
   so'ng BotFather'dan **LIVE** token olib, test token o'rniga qo'ying.

Mijoz buyurtmadan keyin to'lov usulini tanlaydi; to'lov muvaffaqiyatli bo'lsa buyurtma «✅ To'langan»
bo'ladi va adminlarga xabar boradi. To'lanmagan buyurtmani «📦 Buyurtmalarim» dan keyinroq ham to'lash mumkin.
To'langan buyurtma bekor qilinsa, bot pulni Click/Payme kabinetida qaytarish kerakligini eslatadi.

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
    ├── payment.py   # Click, Payme, naqd to'lov
    ├── bonus.py     # 💎 brilliantlar: balans, tarix, sovg'a qilish
webapp/
├── server.py        # sayt API (initData tekshiruvi, savat, buyurtma, media)
├── auth.py          # brauzer rejimi: Telegram Login Widget tekshiruvi, sessiya
└── static/          # index.html (sayt), sw.js (PWA service worker)
    └── admin.py     # admin panel
```

## Serverga joylash

`Procfile` (`worker: python main.py`) mavjud — Railway, Render yoki Heroku'da **Root directory**
sifatida `shop_bot` ni ko'rsating va `BOT_TOKEN`, `ADMIN_IDS` ni environment variable qilib qo'shing.
Ma'lumotlar o'chib ketmasligi uchun ikki yo'l bor:
- **PostgreSQL (tavsiya):** Railway'da `+ Add → Database → PostgreSQL` qo'shing va bot servisi
  Variables bo'limiga `DATABASE_URL` = `${{Postgres.DATABASE_URL}}` yozing.
- **Volume:** `/data` ga volume ulab, `DB_PATH=/data/shop.db` qiling.
