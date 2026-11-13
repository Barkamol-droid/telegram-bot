"""Ma'lumotlar bazasi bilan ishlash.

DATABASE_URL o'zgaruvchisi berilsa — PostgreSQL (asyncpg) ishlatiladi
(masalan, Railway'dagi Postgres), aks holda — SQLite fayl (DB_PATH).
"""
import json
import os
from contextlib import asynccontextmanager
import config
import pricing
from config import DATABASE_URL, DB_PATH, DEFAULT_CATEGORIES, now

USE_PG = bool(DATABASE_URL)

if USE_PG:
    import asyncpg
else:
    import aiosqlite

_pool = None  # asyncpg pool (faqat PostgreSQL uchun)

# Bazaga xos turlar
_T = {
    "pk": "BIGSERIAL PRIMARY KEY" if USE_PG else "INTEGER PRIMARY KEY AUTOINCREMENT",
    "int": "BIGINT" if USE_PG else "INTEGER",
    "real": "DOUBLE PRECISION" if USE_PG else "REAL",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
CREATE TABLE IF NOT EXISTS admins (
    id          {int} PRIMARY KEY,
    full_name   TEXT,
    added_by    {int},
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS couriers (
    id          {int} PRIMARY KEY,
    full_name   TEXT,
    phone       TEXT,
    username    TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS bonus_tx (
    id             {pk},
    user_id        {int} NOT NULL,
    amount         INTEGER NOT NULL,
    kind           TEXT NOT NULL,
    order_id       {int},
    other_user_id  {int},
    created_at     TEXT
);
CREATE TABLE IF NOT EXISTS users (
    id          {int} PRIMARY KEY,
    full_name   TEXT,
    username    TEXT,
    lang        TEXT,
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS categories (
    id         {pk},
    name       TEXT NOT NULL,
    name_i18n  TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id           {pk},
    category_id  {int} NOT NULL,
    name         TEXT NOT NULL,
    name_i18n    TEXT,
    description  TEXT,
    description_i18n TEXT,
    price        {int} NOT NULL,
    photo_id     TEXT,
    sizes        TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cart (
    user_id     {int} NOT NULL,
    product_id  {int} NOT NULL,
    size        TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '',
    qty         INTEGER NOT NULL,
    PRIMARY KEY (user_id, product_id, size, color)
);
CREATE TABLE IF NOT EXISTS orders (
    id          {pk},
    user_id     {int} NOT NULL,
    full_name   TEXT,
    phone       TEXT,
    address     TEXT,
    latitude    {real},
    longitude   {real},
    comment     TEXT,
    total       {int} NOT NULL,
    discount    {int} NOT NULL DEFAULT 0,
    lang        TEXT,
    status      TEXT NOT NULL DEFAULT 'new',
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id    {int} NOT NULL,
    product_id  {int} NOT NULL,
    name        TEXT NOT NULL,
    name_i18n   TEXT,
    size        TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '',
    price       {int} NOT NULL,
    qty         INTEGER NOT NULL
);
""".format(**_T)


def _now() -> str:
    return now().strftime("%Y-%m-%d %H:%M")


def _q(query: str) -> str:
    """SQLite uslubidagi `?` belgilarini PostgreSQL uchun `$1, $2...` ga almashtiradi."""
    if not USE_PG:
        return query
    out, n = [], 0
    for ch in query:
        if ch == "?":
            n += 1
            out.append(f"${n}")
        else:
            out.append(ch)
    return "".join(out)


class _Conn:
    """SQLite va PostgreSQL uchun yagona interfeys."""

    def __init__(self, raw):
        self.raw = raw

    async def fetchall(self, query: str, params=()):
        if USE_PG:
            return [dict(r) for r in await self.raw.fetch(_q(query), *params)]
        async with self.raw.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def fetchone(self, query: str, params=()):
        rows = await self.fetchall(query, params)
        return rows[0] if rows else None

    async def execute(self, query: str, params=()):
        if USE_PG:
            await self.raw.execute(_q(query), *params)
        else:
            await self.raw.execute(query, params)

    async def executemany(self, query: str, seq):
        if USE_PG:
            await self.raw.executemany(_q(query), list(seq))
        else:
            await self.raw.executemany(query, list(seq))

    async def insert(self, query: str, params=()) -> int:
        """INSERT bajarib, yangi yozuv id sini qaytaradi."""
        if USE_PG:
            return await self.raw.fetchval(_q(query) + " RETURNING id", *params)
        cur = await self.raw.execute(query, params)
        return cur.lastrowid


@asynccontextmanager
async def _tx():
    """Tranzaksiya: blok xatosiz tugasa — saqlanadi, xato bo'lsa — bekor qilinadi."""
    if USE_PG:
        async with _pool.acquire() as raw:
            async with raw.transaction():
                yield _Conn(raw)
    else:
        async with aiosqlite.connect(DB_PATH) as raw:
            raw.row_factory = aiosqlite.Row
            yield _Conn(raw)
            await raw.commit()


async def _fetchall(query: str, params=()):
    async with _tx() as db:
        return await db.fetchall(query, params)


async def _fetchone(query: str, params=()):
    async with _tx() as db:
        return await db.fetchone(query, params)


async def _execute(query: str, params=()):
    async with _tx() as db:
        await db.execute(query, params)


async def _insert(query: str, params=()) -> int:
    async with _tx() as db:
        return await db.insert(query, params)


# Keyinroq qo'shilgan ustunlar: eski bazalarga avtomatik qo'shiladi
_EXTRA_COLUMNS = [
    ("products", "sizes", "TEXT"),
    ("orders", "comment", "TEXT"),
    ("order_items", "size", "TEXT NOT NULL DEFAULT ''"),
    ("users", "lang", "TEXT"),
    ("categories", "name_i18n", "TEXT"),
    ("products", "name_i18n", "TEXT"),
    ("products", "description_i18n", "TEXT"),
    ("orders", "discount", f"{_T['int']} NOT NULL DEFAULT 0"),
    ("orders", "lang", "TEXT"),
    ("order_items", "name_i18n", "TEXT"),
    ("orders", "payment_method", "TEXT"),
    ("orders", "payment_status", "TEXT NOT NULL DEFAULT 'unpaid'"),
    ("orders", "paid_at", "TEXT"),
    ("orders", "payment_charge_id", "TEXT"),
    ("orders", "provider_charge_id", "TEXT"),
    ("users", "bonus", "INTEGER NOT NULL DEFAULT 0"),
    ("products", "video_id", "TEXT"),
    ("products", "video_size", "INTEGER"),
    ("products", "colors", "TEXT"),
    ("products", "photos", "TEXT"),
    ("products", "stock", "INTEGER"),
    ("orders", "stock_reserved", "INTEGER NOT NULL DEFAULT 0"),
    ("orders", "courier_id", f"{_T['int']}"),
    ("orders", "delivery_status", "TEXT"),
    ("orders", "courier_msgs", "TEXT"),
    ("orders", "courier_fee", f"{_T['int']}"),
    ("orders", "courier_loc_msg", "INTEGER"),
    ("orders", "delivered_at", "TEXT"),
    ("orders", "delivery_problem", "TEXT"),
    ("order_items", "color", "TEXT NOT NULL DEFAULT ''"),
    ("orders", "subtotal", f"{_T['int']}"),
    ("orders", "bonus_used", "INTEGER NOT NULL DEFAULT 0"),
    ("orders", "bonus_discount", f"{_T['int']} NOT NULL DEFAULT 0"),
    ("orders", "bonus_earned", "INTEGER NOT NULL DEFAULT 0"),
    ("orders", "bonus_awarded", "INTEGER NOT NULL DEFAULT 0"),
    ("orders", "bonus_refunded", "INTEGER NOT NULL DEFAULT 0"),
]


async def _add_missing_columns(db: _Conn):
    for table, column, col_type in _EXTRA_COLUMNS:
        if USE_PG:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")
        else:
            existing = {r["name"] for r in await db.fetchall(f"PRAGMA table_info({table})")}
            if column not in existing:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


async def _migrate_cart_color(db: _Conn):
    """Savat jadvaliga «color» ustunini qo'shish (asosiy kalit ham o'zgaradi, savatdagilar saqlanadi)."""
    if USE_PG:
        row = await db.fetchone(
            "SELECT 1 AS ok FROM information_schema.columns WHERE table_name = 'cart' AND column_name = 'color'"
        )
        if row:
            return
        await db.execute("ALTER TABLE cart ADD COLUMN color TEXT NOT NULL DEFAULT ''")
        await db.execute("ALTER TABLE cart DROP CONSTRAINT IF EXISTS cart_pkey")
        await db.execute("ALTER TABLE cart ADD PRIMARY KEY (user_id, product_id, size, color)")
        return
    columns = {r["name"] for r in await db.fetchall("PRAGMA table_info(cart)")}
    if "color" in columns:
        return
    await db.execute("ALTER TABLE cart RENAME TO cart_old")
    await db.raw.executescript(SCHEMA)
    await db.execute(
        "INSERT INTO cart (user_id, product_id, size, color, qty) SELECT user_id, product_id, size, '', qty FROM cart_old"
    )
    await db.execute("DROP TABLE cart_old")


async def _sqlite_migrate(db: _Conn):
    """Eski SQLite bazalarni yangi tuzilishga moslash."""
    cart_columns = {r["name"] for r in await db.fetchall("PRAGMA table_info(cart)")}
    if "size" not in cart_columns:
        # Savat vaqtinchalik ma'lumot — qayta yaratish xavfsiz
        await db.execute("DROP TABLE cart")
        await db.raw.executescript(SCHEMA)
    # Oldin kategoriya yaratilgan bo'lsa, standart kategoriyalarni qayta qo'shmaslik
    if await db.fetchone("SELECT 1 FROM sqlite_sequence WHERE name = 'categories'"):
        await db.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('seeded', '1')")


async def init_db():
    global _pool
    if USE_PG:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        async with _pool.acquire() as raw:
            await raw.execute(SCHEMA)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as raw:
            await raw.executescript(SCHEMA)
            await raw.commit()

    async with _tx() as db:
        if not USE_PG:
            await _sqlite_migrate(db)
        await _migrate_cart_color(db)
        await _add_missing_columns(db)
        # Birinchi ishga tushirishda standart kategoriyalarni yaratish
        if not await db.fetchone("SELECT 1 FROM meta WHERE key = 'seeded'"):
            await db.executemany(
                "INSERT INTO categories (name, name_i18n) VALUES (?, ?)",
                [(c["uz"], json.dumps(c, ensure_ascii=False)) for c in DEFAULT_CATEGORIES],
            )
            await db.execute("INSERT INTO meta (key, value) VALUES ('seeded', '1')")
        # Avval tarjimasiz yaratilgan standart kategoriyalarga tarjima qo'shish
        for c in DEFAULT_CATEGORIES:
            await db.execute(
                "UPDATE categories SET name_i18n = ? WHERE name = ? AND name_i18n IS NULL",
                (json.dumps(c, ensure_ascii=False), c["uz"]),
            )
        # Bot orqali qo'shilgan adminlarni xotiraga yuklash
        config.EXTRA_ADMINS.clear()
        config.EXTRA_ADMINS.update(int(r["id"]) for r in await db.fetchall("SELECT id FROM admins"))


# ---------------- Adminlar ----------------
async def get_admins() -> list[dict]:
    return await _fetchall("SELECT * FROM admins ORDER BY created_at")


async def add_admin(user_id: int, full_name: str | None, added_by: int):
    await _execute(
        "INSERT INTO admins (id, full_name, added_by, created_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET full_name = excluded.full_name",
        (user_id, full_name, added_by, _now()),
    )
    config.EXTRA_ADMINS.add(user_id)


async def remove_admin(user_id: int):
    await _execute("DELETE FROM admins WHERE id = ?", (user_id,))
    config.EXTRA_ADMINS.discard(user_id)


async def get_user(user_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM users WHERE id = ?", (user_id,))


# ---------------- Sozlamalar (meta) va aksiya ----------------
async def get_meta(key: str) -> str | None:
    row = await _fetchone("SELECT value FROM meta WHERE key = ?", (key,))
    return row["value"] if row else None


async def set_meta(key: str, value: str | None):
    if value is None:
        await _execute("DELETE FROM meta WHERE key = ?", (key,))
    else:
        await _execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


async def get_promo() -> dict | None:
    return pricing.parse(await get_meta("promo"))


async def set_promo(raw: str | None):
    await set_meta("promo", raw)


# ---------------- Foydalanuvchilar ----------------
async def add_user(user_id: int, full_name: str, username: str | None):
    await _execute(
        "INSERT INTO users (id, full_name, username, created_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET full_name = excluded.full_name, username = excluded.username",
        (user_id, full_name, username, _now()),
    )


async def get_user_lang(user_id: int) -> str | None:
    row = await _fetchone("SELECT lang FROM users WHERE id = ?", (user_id,))
    return row["lang"] if row else None


async def set_user_lang(user_id: int, lang: str):
    await _execute("UPDATE users SET lang = ? WHERE id = ?", (lang, user_id))


async def get_users_with_lang() -> list[dict]:
    return await _fetchall("SELECT id, lang FROM users")


async def get_all_user_ids() -> list[int]:
    rows = await _fetchall("SELECT id FROM users")
    return [r["id"] for r in rows]


# ---------------- Kategoriyalar ----------------
async def get_categories():
    return await _fetchall("SELECT * FROM categories ORDER BY id")


async def get_category(category_id: int):
    return await _fetchone("SELECT * FROM categories WHERE id = ?", (category_id,))


async def add_category(name: str, name_i18n: str | None = None) -> int:
    return await _insert("INSERT INTO categories (name, name_i18n) VALUES (?, ?)", (name, name_i18n))


async def delete_category(category_id: int):
    async with _tx() as db:
        await db.execute(
            "DELETE FROM cart WHERE product_id IN (SELECT id FROM products WHERE category_id = ?)",
            (category_id,),
        )
        await db.execute("UPDATE products SET is_active = 0 WHERE category_id = ?", (category_id,))
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))


# ---------------- Mahsulotlar ----------------
async def get_products(category_id: int):
    return await _fetchall(
        "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id",
        (category_id,),
    )


async def get_product(product_id: int):
    return await _fetchone(
        "SELECT * FROM products WHERE id = ? AND is_active = 1", (product_id,)
    )


def product_sizes(product) -> list[str]:
    return [x for x in (product.get("sizes") or "").split(",") if x]


async def add_product(category_id: int, name: str, description: str | None,
                      price: int, photo_id: str | None, sizes: list[str] | None = None,
                      name_i18n: str | None = None, description_i18n: str | None = None,
                      video_id: str | None = None, video_size: int | None = None,
                      colors_json: str | None = None, photos: list[str] | None = None,
                      stock: int | None = None) -> int:
    photos = (photos or ([photo_id] if photo_id else []))[:MAX_PHOTOS]
    return await _insert(
        "INSERT INTO products (category_id, name, name_i18n, description, description_i18n, price, photo_id, sizes, "
        "video_id, video_size, colors, photos, stock) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (category_id, name, name_i18n, description, description_i18n, price, photos[0] if photos else None,
         ",".join(sizes) if sizes else None, video_id, video_size, colors_json, json.dumps(photos) if photos else None,
         stock),
    )


async def get_all_products() -> list[dict]:
    """Barcha faol mahsulotlar (sayt ko'rinishi uchun)."""
    return await _fetchall(
        "SELECT p.* FROM products p JOIN categories c ON c.id = p.category_id "
        "WHERE p.is_active = 1 ORDER BY p.id DESC"
    )


async def set_product_colors(product_id: int, colors_json: str | None):
    await _execute("UPDATE products SET colors = ? WHERE id = ?", (colors_json, product_id))


MAX_PHOTOS = 10


def product_photos(product: dict) -> list[str]:
    """Mahsulot rasmlari (birinchisi — asosiy). Eski mahsulotlarda faqat photo_id bo'ladi."""
    raw = product.get("photos")
    if raw:
        try:
            photos = [str(p) for p in json.loads(raw) if p]
            if photos:
                return photos
        except ValueError:
            pass
    return [product["photo_id"]] if product.get("photo_id") else []


async def set_product_photos(product_id: int, photos: list[str]):
    photos = photos[:MAX_PHOTOS]
    await _execute(
        "UPDATE products SET photos = ?, photo_id = ? WHERE id = ?",
        (json.dumps(photos) if photos else None, photos[0] if photos else None, product_id),
    )


async def set_product_photo(product_id: int, photo_id: str | None):
    await set_product_photos(product_id, [photo_id] if photo_id else [])


_EDITABLE = {"name", "name_i18n", "description", "description_i18n", "price", "sizes", "category_id", "stock"}
LOW_STOCK = 3  # shu sondan kam qolsa — «Faqat N ta qoldi!» va adminga ogohlantirish


def product_stock(product: dict) -> int | None:
    """Mahsulot qoldig'i: None — soni hisoblanmaydi (cheklanmagan)."""
    value = product.get("stock")
    return None if value is None else max(int(value), 0)


class OutOfStock(Exception):
    """Buyurtma paytida qoldiq yetmadi. items: [{"product_id", "name", "name_i18n", "available"}]"""

    def __init__(self, items: list[dict]):
        super().__init__("out of stock")
        self.items = items


async def cart_product_qty(user_id: int, product_id: int) -> int:
    """Savatdagi shu mahsulotning jami soni (barcha o'lcham/ranglar bo'yicha)."""
    row = await _fetchone(
        "SELECT COALESCE(SUM(qty), 0) AS n FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id)
    )
    return int(row["n"])


def _stock_issues(items: list[dict]) -> list[dict]:
    """Savatdagi miqdor qoldiqdan oshgan mahsulotlar."""
    wanted: dict[int, int] = {}
    info: dict[int, dict] = {}
    for i in items:
        wanted[i["product_id"]] = wanted.get(i["product_id"], 0) + i["qty"]
        info[i["product_id"]] = i
    issues = []
    for pid, qty in wanted.items():
        stock = info[pid].get("stock")
        if stock is not None and qty > int(stock):
            issues.append({"product_id": pid, "name": info[pid]["name"], "name_i18n": info[pid].get("name_i18n"),
                           "available": max(int(stock), 0)})
    return issues


async def update_product(product_id: int, **fields):
    """Mahsulot maydonlarini yangilash (faqat ruxsat etilganlari)."""
    fields = {k: v for k, v in fields.items() if k in _EDITABLE}
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    await _execute(f"UPDATE products SET {sets} WHERE id = ?", (*fields.values(), product_id))


async def set_product_video(product_id: int, video_id: str | None, video_size: int | None = None):
    await _execute("UPDATE products SET video_id = ?, video_size = ? WHERE id = ?", (video_id, video_size, product_id))


async def is_product_media(file_id: str) -> bool:
    """Fayl biror faol mahsulotning rasmi yoki videosimi (sayt orqali faqat shularni beramiz)."""
    row = await _fetchone(
        "SELECT 1 AS ok FROM products WHERE is_active = 1 AND (photo_id = ? OR video_id = ? OR photos LIKE ?)",
        (file_id, file_id, f'%"{file_id}"%'),
    )
    return row is not None


async def get_last_contact(user_id: int) -> dict | None:
    """Oxirgi buyurtmadagi ism, telefon, manzil — saytdagi formani avtomatik to'ldirish uchun."""
    return await _fetchone(
        "SELECT full_name, phone, address FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    )


async def cart_set(user_id: int, product_id: int, size: str, qty: int, color: str = ""):
    """Savatdagi miqdorni aniq qiymatga o'rnatadi (0 — o'chiradi)."""
    if qty <= 0:
        await cart_remove(user_id, product_id, size, color)
        return
    await _execute(
        "INSERT INTO cart (user_id, product_id, size, color, qty) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, product_id, size, color) DO UPDATE SET qty = excluded.qty",
        (user_id, product_id, size, color, min(qty, 99)),
    )


async def delete_product(product_id: int):
    async with _tx() as db:
        await db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        await db.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))


# ---------------- Savat ----------------
async def cart_add(user_id: int, product_id: int, qty: int, size: str = "", color: str = ""):
    await _execute(
        "INSERT INTO cart (user_id, product_id, size, color, qty) VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(user_id, product_id, size, color) DO UPDATE SET qty = "
        "CASE WHEN cart.qty + excluded.qty > 99 THEN 99 ELSE cart.qty + excluded.qty END",
        (user_id, product_id, size, color, qty),
    )


async def cart_get(user_id: int):
    async with _tx() as db:
        return await _cart_get(db, user_id)


async def _cart_get(db: _Conn, user_id: int):
    """Savatdagi mahsulotlar — joriy aksiya hisobga olingan narxlar bilan.
    Har bir qatorda: price (yakuniy), old_price (aksiyadan oldingi yoki None), percent, subtotal."""
    rows = await db.fetchall(
        "SELECT c.product_id, c.size, c.color, c.qty, p.name, p.name_i18n, p.price, p.category_id, p.stock "
        "FROM cart c JOIN products p ON p.id = c.product_id "
        "WHERE c.user_id = ? AND p.is_active = 1 ORDER BY p.name, c.size, c.color",
        (user_id,),
    )
    meta = await db.fetchone("SELECT value FROM meta WHERE key = 'promo'")
    promo = pricing.parse(meta["value"] if meta else None)
    for r in rows:
        r["price"], r["old_price"], r["percent"] = pricing.price_info(int(r["price"]), r["category_id"], promo)
        r["subtotal"] = r["price"] * r["qty"]
        r["saved"] = (r["old_price"] - r["price"]) * r["qty"] if r["old_price"] else 0
    return rows


async def cart_remove(user_id: int, product_id: int, size: str = "", color: str = ""):
    await _execute(
        "DELETE FROM cart WHERE user_id = ? AND product_id = ? AND size = ? AND color = ?",
        (user_id, product_id, size, color),
    )


async def cart_clear(user_id: int):
    await _execute("DELETE FROM cart WHERE user_id = ?", (user_id,))


# ---------------- Buyurtmalar ----------------
# ---------------- Bonus (💎 brilliant) ----------------
def bonus_for_amount(amount: int) -> int:
    """Xarid summasi uchun beriladigan brilliantlar soni (har to'liq BONUS_STEP so'm uchun 1 ta)."""
    return max(int(amount) // config.BONUS_STEP, 0)


async def _bonus_balance(db: _Conn, user_id: int, lock: bool = False) -> int:
    row = await db.fetchone(
        "SELECT bonus FROM users WHERE id = ?" + (" FOR UPDATE" if lock and USE_PG else ""), (user_id,)
    )
    return int(row["bonus"]) if row else 0


async def _bonus_change(db: _Conn, user_id: int, delta: int, kind: str,
                        order_id: int | None = None, other_user_id: int | None = None):
    await db.execute("UPDATE users SET bonus = bonus + ? WHERE id = ?", (delta, user_id))
    await db.execute(
        "INSERT INTO bonus_tx (user_id, amount, kind, order_id, other_user_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, delta, kind, order_id, other_user_id, _now()),
    )


async def get_bonus(user_id: int) -> int:
    async with _tx() as db:
        return await _bonus_balance(db, user_id)


async def bonus_history(user_id: int, limit: int = 10) -> list[dict]:
    return await _fetchall(
        "SELECT * FROM bonus_tx WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
    )


async def ensure_user(user_id: int, full_name: str | None, username: str | None = None):
    """Foydalanuvchi bazada bo'lmasa qo'shadi (mavjud bo'lsa o'zgartirmaydi)."""
    await _execute(
        "INSERT INTO users (id, full_name, username, created_at) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO NOTHING",
        (user_id, full_name, username, _now()),
    )


async def transfer_bonus(from_id: int, to_id: int, amount: int) -> int | None:
    """Brilliantlarni boshqa foydalanuvchiga o'tkazadi. Muvaffaqiyatli bo'lsa — yuboruvchining qoldig'i."""
    if amount <= 0 or from_id == to_id:
        return None
    async with _tx() as db:
        balance = await _bonus_balance(db, from_id, lock=True)
        if balance < amount:
            return None
        await _bonus_change(db, from_id, -amount, "transfer_out", other_user_id=to_id)
        await _bonus_change(db, to_id, amount, "transfer_in", other_user_id=from_id)
        return balance - amount


async def admin_give_bonus(user_id: int, amount: int) -> int:
    async with _tx() as db:
        await _bonus_change(db, user_id, amount, "admin")
        return await _bonus_balance(db, user_id)


def _bonus_usage(total: int, balance: int, use_bonus: bool) -> tuple[int, int]:
    """(ishlatiladigan brilliantlar, chegirma so'mda) — chegirma buyurtma summasidan oshmaydi."""
    if not use_bonus or balance <= 0:
        return 0, 0
    used = min(balance, total // config.BONUS_VALUE)
    return used, used * config.BONUS_VALUE


async def order_preview(user_id: int, use_bonus: bool = False) -> dict:
    """Buyurtma oldidan hisob: mahsulotlar, aksiya, brilliant chegirmasi va yakuniy summa."""
    async with _tx() as db:
        return await _order_preview(db, user_id, use_bonus)


async def _order_preview(db: _Conn, user_id: int, use_bonus: bool, lock: bool = False) -> dict:
    items = await _cart_get(db, user_id)
    subtotal = sum(i["subtotal"] for i in items)
    balance = await _bonus_balance(db, user_id, lock=lock)
    used, bonus_discount = _bonus_usage(subtotal, balance, use_bonus)
    total = subtotal - bonus_discount
    return {
        "items": items,
        "subtotal": subtotal,
        "promo_discount": sum(i["saved"] for i in items),
        "balance": balance,
        "max_usable": _bonus_usage(subtotal, balance, True)[0],
        "bonus_used": used,
        "bonus_discount": bonus_discount,
        "total": total,
        "bonus_earned": bonus_for_amount(total),
        "stock_issues": _stock_issues(items),
    }


async def award_order_bonus(order_id: int) -> dict | None:
    """Yetkazilgan buyurtma uchun brilliantlarni hisobga yozadi (bir marta)."""
    async with _tx() as db:
        order = await db.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))
        if not order or order["bonus_awarded"]:
            return None
        earned = int(order["bonus_earned"] or 0)
        if order["subtotal"] is None:
            # Bonus tizimidan oldin berilgan buyurtma — brilliantni summadan hisoblaymiz
            earned = bonus_for_amount(int(order["total"]))
        if not earned:
            return None
        await db.execute("UPDATE orders SET bonus_awarded = 1, bonus_earned = ? WHERE id = ?", (earned, order_id))
        await _bonus_change(db, order["user_id"], earned, "earn", order_id=order_id)
        return {"user_id": order["user_id"], "amount": earned,
                "balance": await _bonus_balance(db, order["user_id"])}


async def cancel_order_bonus(order_id: int) -> dict:
    """Bekor qilingan buyurtma: ishlatilgan brilliantlar qaytariladi, berilganlari qaytarib olinadi."""
    result = {"refunded": 0, "revoked": 0, "user_id": None}
    async with _tx() as db:
        order = await db.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))
        if not order:
            return result
        user_id = order["user_id"]
        result["user_id"] = user_id
        if order["bonus_used"] and not order["bonus_refunded"]:
            await db.execute("UPDATE orders SET bonus_refunded = 1 WHERE id = ?", (order_id,))
            await _bonus_change(db, user_id, int(order["bonus_used"]), "refund", order_id=order_id)
            result["refunded"] = int(order["bonus_used"])
        if order["bonus_awarded"]:
            balance = await _bonus_balance(db, user_id, lock=True)
            revoke = min(balance, int(order["bonus_earned"]))
            await db.execute("UPDATE orders SET bonus_awarded = 0, bonus_earned = 0 WHERE id = ?", (order_id,))
            if revoke:
                await _bonus_change(db, user_id, -revoke, "revoke", order_id=order_id)
            result["revoked"] = revoke
        else:
            await db.execute("UPDATE orders SET bonus_earned = 0 WHERE id = ?", (order_id,))
    return result


async def bonus_stats() -> dict:
    row = await _fetchone("SELECT COALESCE(SUM(bonus), 0) AS s, COUNT(*) AS n FROM users WHERE bonus > 0")
    return {"outstanding": int(row["s"]), "holders": int(row["n"])}


async def create_order(user_id: int, full_name: str, phone: str, address: str | None,
                       latitude: float | None = None, longitude: float | None = None,
                       comment: str | None = None, lang: str | None = None,
                       use_bonus: bool = False) -> int | None:
    """Savatdagi mahsulotlardan buyurtma yaratadi. Savat bo'sh bo'lsa None qaytaradi.
    use_bonus=True bo'lsa, brilliantlar chegirma sifatida ishlatiladi (balansdan yechiladi)."""
    async with _tx() as db:
        p = await _order_preview(db, user_id, use_bonus, lock=True)
        items = p["items"]
        if not items:
            return None
        # Qoldiqni tekshirish: PostgreSQL'da mahsulot qatorlari bir vaqtdagi buyurtmalar uchun qulflanadi
        if USE_PG:
            ids = sorted({i["product_id"] for i in items})
            rows = await db.fetchall(
                f"SELECT id, stock FROM products WHERE id IN ({', '.join('?' for _ in ids)}) FOR UPDATE", ids
            )
            fresh = {r["id"]: r["stock"] for r in rows}
            for i in items:
                i["stock"] = fresh.get(i["product_id"], i.get("stock"))
        issues = _stock_issues(items)
        if issues:
            raise OutOfStock(issues)
        total = p["total"]
        fully_paid = total == 0
        order_id = await db.insert(
            "INSERT INTO orders (user_id, full_name, phone, address, latitude, longitude, comment, "
            "subtotal, total, discount, bonus_used, bonus_discount, bonus_earned, lang, status, created_at, "
            "payment_status, payment_method) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?, ?)",
            (user_id, full_name, phone, address, latitude, longitude, comment,
             p["subtotal"], total, p["promo_discount"], p["bonus_used"], p["bonus_discount"], p["bonus_earned"],
             lang, _now(), "paid" if fully_paid else "unpaid", "bonus" if fully_paid else None),
        )
        if p["bonus_used"]:
            await _bonus_change(db, user_id, -p["bonus_used"], "spend", order_id=order_id)
        await db.executemany(
            "INSERT INTO order_items (order_id, product_id, name, name_i18n, size, color, price, qty) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(order_id, i["product_id"], i["name"], i["name_i18n"], i["size"], i["color"], i["price"], i["qty"])
             for i in items],
        )
        # Qoldiqni kamaytirish (soni hisoblanadigan mahsulotlar uchun)
        reserved = False
        for i in items:
            if i.get("stock") is not None:
                await db.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ? AND stock IS NOT NULL", (i["qty"], i["product_id"])
                )
                reserved = True
        if reserved:
            await db.execute("UPDATE orders SET stock_reserved = 1 WHERE id = ?", (order_id,))
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    return order_id


async def restore_order_stock(order_id: int) -> bool:
    """Bekor qilingan buyurtma mahsulotlarini qoldiqqa qaytaradi (bir marta)."""
    async with _tx() as db:
        order = await db.fetchone("SELECT stock_reserved FROM orders WHERE id = ?", (order_id,))
        if not order or not order["stock_reserved"]:
            return False
        await db.execute("UPDATE orders SET stock_reserved = 0 WHERE id = ?", (order_id,))
        for item in await db.fetchall("SELECT product_id, qty FROM order_items WHERE order_id = ?", (order_id,)):
            await db.execute(
                "UPDATE products SET stock = stock + ? WHERE id = ? AND stock IS NOT NULL", (item["qty"], item["product_id"])
            )
    return True


async def low_stock_products(product_ids: list[int]) -> list[dict]:
    """Berilgan mahsulotlardan qoldig'i kam qolganlari (adminga ogohlantirish uchun)."""
    if not product_ids:
        return []
    ids = sorted(set(product_ids))
    return await _fetchall(
        f"SELECT id, name, stock FROM products WHERE id IN ({', '.join('?' for _ in ids)}) "
        "AND stock IS NOT NULL AND stock < ? AND is_active = 1",
        (*ids, LOW_STOCK),
    )


async def get_order(order_id: int):
    return await _fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))


async def set_payment_method(order_id: int, method: str):
    await _execute(
        "UPDATE orders SET payment_method = ? WHERE id = ? AND payment_status <> 'paid'", (method, order_id)
    )


async def mark_paid(order_id: int, method: str, charge_id: str, provider_charge_id: str) -> bool:
    """Buyurtmani to'langan deb belgilaydi. Avval to'langan bo'lsa — False (takroriy xabar)."""
    async with _tx() as db:
        row = await db.fetchone("SELECT payment_status FROM orders WHERE id = ?", (order_id,))
        if not row or row["payment_status"] == "paid":
            return False
        await db.execute(
            "UPDATE orders SET payment_status = 'paid', payment_method = ?, paid_at = ?, "
            "payment_charge_id = ?, provider_charge_id = ? WHERE id = ?",
            (method, _now(), charge_id, provider_charge_id, order_id),
        )
    return True


async def get_order_items(order_id: int):
    return await _fetchall("SELECT * FROM order_items WHERE order_id = ?", (order_id,))


async def get_user_orders(user_id: int, limit: int = 10):
    return await _fetchall(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
    )


async def get_recent_orders(limit: int = 15):
    return await _fetchall("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,))


async def set_order_status(order_id: int, status: str):
    await _execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))


async def get_stats() -> dict:
    async with _tx() as db:
        users = await db.fetchone("SELECT COUNT(*) AS n FROM users")
        orders = await db.fetchone("SELECT COUNT(*) AS n FROM orders")
        new_orders = await db.fetchone("SELECT COUNT(*) AS n FROM orders WHERE status = 'new'")
        revenue = await db.fetchone(
            "SELECT COALESCE(SUM(total), 0) AS s FROM orders WHERE status = 'delivered'"
        )
        products = await db.fetchone("SELECT COUNT(*) AS n FROM products WHERE is_active = 1")
        paid = await db.fetchone(
            "SELECT COUNT(*) AS n, COALESCE(SUM(total), 0) AS s FROM orders WHERE payment_status = 'paid'"
        )
    return {
        "users": int(users["n"]),
        "orders": int(orders["n"]),
        "new_orders": int(new_orders["n"]),
        "revenue": int(revenue["s"]),
        "products": int(products["n"]),
        "paid_orders": int(paid["n"]),
        "paid_sum": int(paid["s"]),
    }


# ---------------- Kuryerlar ----------------
async def courier_request(user_id: int, full_name: str, phone: str, username: str | None) -> str:
    """Kuryer arizasi. Qaytaradi: kuryerning joriy holati (pending / active / blocked)."""
    existing = await get_courier(user_id)
    if existing:
        await _execute("UPDATE couriers SET full_name = ?, phone = ?, username = ? WHERE id = ?",
                       (full_name, phone, username, user_id))
        return existing["status"]
    await _execute(
        "INSERT INTO couriers (id, full_name, phone, username, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (user_id, full_name, phone, username, _now()),
    )
    return "pending"


async def get_courier(user_id: int) -> dict | None:
    return await _fetchone("SELECT * FROM couriers WHERE id = ?", (user_id,))


async def set_courier_status(user_id: int, status: str):
    await _execute("UPDATE couriers SET status = ? WHERE id = ?", (status, user_id))


async def get_couriers(status: str | None = None) -> list[dict]:
    if status:
        return await _fetchall("SELECT * FROM couriers WHERE status = ? ORDER BY created_at", (status,))
    return await _fetchall("SELECT * FROM couriers ORDER BY status, created_at")


async def save_courier_messages(order_id: int, messages: dict[int, int]):
    await _execute("UPDATE orders SET courier_msgs = ? WHERE id = ?",
                   (json.dumps({str(k): v for k, v in messages.items()}), order_id))


def courier_messages(order: dict) -> dict[int, int]:
    try:
        return {int(k): int(v) for k, v in json.loads(order.get("courier_msgs") or "{}").items()}
    except ValueError:
        return {}


async def claim_order(order_id: int, courier_id: int) -> bool:
    """Buyurtmani kuryerga biriktirish. Bir vaqtda bosilsa ham faqat bittasi oladi (shartli UPDATE)."""
    async with _tx() as db:
        await db.execute(
            "UPDATE orders SET courier_id = ?, delivery_status = 'assigned', "
            "status = CASE WHEN status = 'new' THEN 'accepted' ELSE status END "
            "WHERE id = ? AND courier_id IS NULL AND status NOT IN ('cancelled', 'delivered')",
            (courier_id, order_id),
        )
        row = await db.fetchone("SELECT courier_id FROM orders WHERE id = ?", (order_id,))
    return bool(row) and row["courier_id"] == courier_id


async def set_delivery_status(order_id: int, courier_id: int, status: str) -> bool:
    """Kuryer bosqichini yangilash (faqat shu buyurtmani olgan kuryer uchun)."""
    allowed_from = {"on_way": ("assigned",), "delivered": ("assigned", "on_way")}[status]
    async with _tx() as db:
        order = await db.fetchone("SELECT courier_id, delivery_status, status FROM orders WHERE id = ?", (order_id,))
        if (not order or order["courier_id"] != courier_id or order["status"] == "cancelled"
                or order["delivery_status"] not in allowed_from):
            return False
        await db.execute("UPDATE orders SET delivery_status = ? WHERE id = ?", (status, order_id))
        if status == "delivered":
            await db.execute("UPDATE orders SET status = 'delivered', delivered_at = ? WHERE id = ?", (_now(), order_id))
    return True


async def courier_active_orders(courier_id: int) -> list[dict]:
    return await _fetchall(
        "SELECT * FROM orders WHERE courier_id = ? AND "
        "(delivery_status IN ('assigned', 'on_way', 'problem') AND status <> 'cancelled' OR delivery_status = 'returning') "
        "ORDER BY id", (courier_id,)
    )


# ---------------- Kuryer haqi va hisob-kitob ----------------
async def get_default_courier_fee() -> int:
    value = await get_meta("courier_fee")
    return int(value) if value and value.isdigit() else 0


async def set_default_courier_fee(amount: int):
    await set_meta("courier_fee", str(max(int(amount), 0)))


async def set_order_courier_fee(order_id: int, amount: int):
    await _execute("UPDATE orders SET courier_fee = ? WHERE id = ?", (max(int(amount), 0), order_id))


async def set_courier_location_message(order_id: int, message_id: int | None):
    await _execute("UPDATE orders SET courier_loc_msg = ? WHERE id = ?", (message_id, order_id))


async def courier_earnings(courier_id: int, since: str) -> dict:
    """Kuryer topshirgan buyurtmalar soni va haqlari yig'indisi (since — "YYYY-MM-DD HH:MM" dan boshlab)."""
    row = await _fetchone(
        "SELECT COUNT(*) AS n, COALESCE(SUM(courier_fee), 0) AS s FROM orders "
        "WHERE courier_id = ? AND delivery_status = 'delivered' AND delivered_at >= ?",
        (courier_id, since),
    )
    return {"count": int(row["n"]), "sum": int(row["s"])}


# ---------------- Kuryer: voz kechish, muammo, qaytarish ----------------
async def release_order(order_id: int, courier_id: int) -> bool:
    """Kuryer yo'lga chiqmasidan oldin buyurtmadan voz kechadi — buyurtma yana hech kimga biriktirilmagan bo'ladi."""
    async with _tx() as db:
        order = await db.fetchone("SELECT courier_id, delivery_status, status FROM orders WHERE id = ?", (order_id,))
        if (not order or order["courier_id"] != courier_id or order["status"] == "cancelled"
                or order["delivery_status"] != "assigned"):
            return False
        await db.execute(
            "UPDATE orders SET courier_id = NULL, delivery_status = NULL, courier_msgs = NULL, courier_loc_msg = NULL "
            "WHERE id = ?", (order_id,)
        )
    return True


async def report_problem(order_id: int, courier_id: int, reason: str) -> bool:
    async with _tx() as db:
        order = await db.fetchone("SELECT courier_id, delivery_status, status FROM orders WHERE id = ?", (order_id,))
        if (not order or order["courier_id"] != courier_id or order["status"] == "cancelled"
                or order["delivery_status"] not in ("assigned", "on_way", "problem")):
            return False
        await db.execute("UPDATE orders SET delivery_status = 'problem', delivery_problem = ? WHERE id = ?",
                         (reason[:500], order_id))
    return True


async def resolve_problem_retry(order_id: int) -> bool:
    """Admin: «Qayta urinsin» — kuryer yetkazishni davom ettiradi."""
    async with _tx() as db:
        order = await db.fetchone("SELECT delivery_status, status FROM orders WHERE id = ?", (order_id,))
        if not order or order["status"] == "cancelled" or order["delivery_status"] != "problem":
            return False
        await db.execute("UPDATE orders SET delivery_status = 'on_way' WHERE id = ?", (order_id,))
    return True


async def admin_release_order(order_id: int) -> int | None:
    """Admin: «Boshqa kuryerga» — buyurtmani joriy kuryerdan olib, qayta tarqatishga tayyorlaydi.
    Qaytaradi: oldingi kuryer ID si (yoki None)."""
    async with _tx() as db:
        order = await db.fetchone("SELECT courier_id, delivery_status, status FROM orders WHERE id = ?", (order_id,))
        if not order or order["status"] in ("cancelled", "delivered") or order["delivery_status"] == "delivered":
            return None
        await db.execute(
            "UPDATE orders SET courier_id = NULL, delivery_status = NULL, courier_msgs = NULL, courier_loc_msg = NULL, "
            "delivery_problem = NULL WHERE id = ?", (order_id,)
        )
    return order["courier_id"]


async def set_returning(order_id: int) -> bool:
    """Bekor qilingan buyurtma kuryerda bo'lsa — mahsulotni do'konga qaytarish kerak."""
    async with _tx() as db:
        order = await db.fetchone("SELECT courier_id, delivery_status FROM orders WHERE id = ?", (order_id,))
        if not order or not order["courier_id"] or order["delivery_status"] not in ("assigned", "on_way", "problem"):
            return False
        await db.execute("UPDATE orders SET delivery_status = 'returning' WHERE id = ?", (order_id,))
    return True


async def mark_returned(order_id: int, courier_id: int) -> bool:
    async with _tx() as db:
        order = await db.fetchone("SELECT courier_id, delivery_status FROM orders WHERE id = ?", (order_id,))
        if not order or order["courier_id"] != courier_id or order["delivery_status"] != "returning":
            return False
        await db.execute("UPDATE orders SET delivery_status = 'returned' WHERE id = ?", (order_id,))
    return True
