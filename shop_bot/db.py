"""Ma'lumotlar bazasi bilan ishlash.

DATABASE_URL o'zgaruvchisi berilsa — PostgreSQL (asyncpg) ishlatiladi
(masalan, Railway'dagi Postgres), aks holda — SQLite fayl (DB_PATH).
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime

from config import DATABASE_URL, DB_PATH, DEFAULT_CATEGORIES

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
CREATE TABLE IF NOT EXISTS users (
    id          {int} PRIMARY KEY,
    full_name   TEXT,
    username    TEXT,
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS categories (
    id    {pk},
    name  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id           {pk},
    category_id  {int} NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    price        {int} NOT NULL,
    photo_id     TEXT,
    sizes        TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cart (
    user_id     {int} NOT NULL,
    product_id  {int} NOT NULL,
    size        TEXT NOT NULL DEFAULT '',
    qty         INTEGER NOT NULL,
    PRIMARY KEY (user_id, product_id, size)
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
    status      TEXT NOT NULL DEFAULT 'new',
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id    {int} NOT NULL,
    product_id  {int} NOT NULL,
    name        TEXT NOT NULL,
    size        TEXT NOT NULL DEFAULT '',
    price       {int} NOT NULL,
    qty         INTEGER NOT NULL
);
""".format(**_T)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


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


async def _sqlite_migrate(db: _Conn):
    """Eski SQLite bazalarni yangi tuzilishga moslash."""
    async def columns(table):
        return {r["name"] for r in await db.fetchall(f"PRAGMA table_info({table})")}

    if "sizes" not in await columns("products"):
        await db.execute("ALTER TABLE products ADD COLUMN sizes TEXT")
    if "comment" not in await columns("orders"):
        await db.execute("ALTER TABLE orders ADD COLUMN comment TEXT")
    if "size" not in await columns("order_items"):
        await db.execute("ALTER TABLE order_items ADD COLUMN size TEXT NOT NULL DEFAULT ''")
    if "size" not in await columns("cart"):
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
        # Birinchi ishga tushirishda standart kategoriyalarni yaratish
        if not await db.fetchone("SELECT 1 FROM meta WHERE key = 'seeded'"):
            await db.executemany(
                "INSERT INTO categories (name) VALUES (?)", [(c,) for c in DEFAULT_CATEGORIES]
            )
            await db.execute("INSERT INTO meta (key, value) VALUES ('seeded', '1')")


# ---------------- Foydalanuvchilar ----------------
async def add_user(user_id: int, full_name: str, username: str | None):
    await _execute(
        "INSERT INTO users (id, full_name, username, created_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET full_name = excluded.full_name, username = excluded.username",
        (user_id, full_name, username, _now()),
    )


async def get_all_user_ids() -> list[int]:
    rows = await _fetchall("SELECT id FROM users")
    return [r["id"] for r in rows]


# ---------------- Kategoriyalar ----------------
async def get_categories():
    return await _fetchall("SELECT * FROM categories ORDER BY id")


async def get_category(category_id: int):
    return await _fetchone("SELECT * FROM categories WHERE id = ?", (category_id,))


async def add_category(name: str) -> int:
    return await _insert("INSERT INTO categories (name) VALUES (?)", (name,))


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
                      price: int, photo_id: str | None, sizes: list[str] | None = None) -> int:
    return await _insert(
        "INSERT INTO products (category_id, name, description, price, photo_id, sizes) VALUES (?, ?, ?, ?, ?, ?)",
        (category_id, name, description, price, photo_id, ",".join(sizes) if sizes else None),
    )


async def delete_product(product_id: int):
    async with _tx() as db:
        await db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        await db.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))


# ---------------- Savat ----------------
async def cart_add(user_id: int, product_id: int, qty: int, size: str = ""):
    await _execute(
        "INSERT INTO cart (user_id, product_id, size, qty) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(user_id, product_id, size) DO UPDATE SET qty = "
        "CASE WHEN cart.qty + excluded.qty > 99 THEN 99 ELSE cart.qty + excluded.qty END",
        (user_id, product_id, size, qty),
    )


async def cart_get(user_id: int):
    async with _tx() as db:
        return await _cart_get(db, user_id)


async def _cart_get(db: _Conn, user_id: int):
    return await db.fetchall(
        "SELECT c.product_id, c.size, c.qty, p.name, p.price, (c.qty * p.price) AS subtotal "
        "FROM cart c JOIN products p ON p.id = c.product_id "
        "WHERE c.user_id = ? AND p.is_active = 1 ORDER BY p.name, c.size",
        (user_id,),
    )


async def cart_remove(user_id: int, product_id: int, size: str = ""):
    await _execute(
        "DELETE FROM cart WHERE user_id = ? AND product_id = ? AND size = ?", (user_id, product_id, size)
    )


async def cart_clear(user_id: int):
    await _execute("DELETE FROM cart WHERE user_id = ?", (user_id,))


# ---------------- Buyurtmalar ----------------
async def create_order(user_id: int, full_name: str, phone: str, address: str | None,
                       latitude: float | None = None, longitude: float | None = None,
                       comment: str | None = None) -> int | None:
    """Savatdagi mahsulotlardan buyurtma yaratadi. Savat bo'sh bo'lsa None qaytaradi."""
    async with _tx() as db:
        items = await _cart_get(db, user_id)
        if not items:
            return None
        total = sum(int(i["subtotal"]) for i in items)
        order_id = await db.insert(
            "INSERT INTO orders (user_id, full_name, phone, address, latitude, longitude, comment, total, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)",
            (user_id, full_name, phone, address, latitude, longitude, comment, total, _now()),
        )
        await db.executemany(
            "INSERT INTO order_items (order_id, product_id, name, size, price, qty) VALUES (?, ?, ?, ?, ?, ?)",
            [(order_id, i["product_id"], i["name"], i["size"], i["price"], i["qty"]) for i in items],
        )
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    return order_id


async def get_order(order_id: int):
    return await _fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))


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
    return {
        "users": int(users["n"]),
        "orders": int(orders["n"]),
        "new_orders": int(new_orders["n"]),
        "revenue": int(revenue["s"]),
        "products": int(products["n"]),
    }
