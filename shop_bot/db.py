"""SQLite ma'lumotlar bazasi bilan ishlash (aiosqlite)."""
from datetime import datetime

import aiosqlite

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    full_name   TEXT,
    username    TEXT,
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id  INTEGER NOT NULL,
    name         TEXT NOT NULL,
    description  TEXT,
    price        INTEGER NOT NULL,
    photo_id     TEXT,
    is_active    INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cart (
    user_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    qty         INTEGER NOT NULL,
    PRIMARY KEY (user_id, product_id)
);
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    full_name   TEXT,
    phone       TEXT,
    address     TEXT,
    latitude    REAL,
    longitude   REAL,
    total       INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',
    created_at  TEXT
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id    INTEGER NOT NULL,
    product_id  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    price       INTEGER NOT NULL,
    qty         INTEGER NOT NULL
);
"""


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _connect():
    conn = aiosqlite.connect(DB_PATH)
    return conn


async def _fetchall(query: str, params=()):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def _fetchone(query: str, params=()):
    async with _connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def _execute(query: str, params=()) -> int:
    async with _connect() as db:
        cur = await db.execute(query, params)
        await db.commit()
        return cur.lastrowid


async def init_db():
    async with _connect() as db:
        await db.executescript(SCHEMA)
        await db.commit()


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
    return await _execute("INSERT INTO categories (name) VALUES (?)", (name,))


async def delete_category(category_id: int):
    async with _connect() as db:
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.execute("UPDATE products SET is_active = 0 WHERE category_id = ?", (category_id,))
        await db.execute(
            "DELETE FROM cart WHERE product_id IN (SELECT id FROM products WHERE category_id = ?)",
            (category_id,),
        )
        await db.commit()


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


async def add_product(category_id: int, name: str, description: str | None,
                      price: int, photo_id: str | None) -> int:
    return await _execute(
        "INSERT INTO products (category_id, name, description, price, photo_id) VALUES (?, ?, ?, ?, ?)",
        (category_id, name, description, price, photo_id),
    )


async def delete_product(product_id: int):
    async with _connect() as db:
        await db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
        await db.execute("DELETE FROM cart WHERE product_id = ?", (product_id,))
        await db.commit()


# ---------------- Savat ----------------
async def cart_add(user_id: int, product_id: int, qty: int):
    await _execute(
        "INSERT INTO cart (user_id, product_id, qty) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, product_id) DO UPDATE SET qty = MIN(qty + excluded.qty, 99)",
        (user_id, product_id, qty),
    )


async def cart_get(user_id: int):
    return await _fetchall(
        "SELECT c.product_id, c.qty, p.name, p.price, (c.qty * p.price) AS subtotal "
        "FROM cart c JOIN products p ON p.id = c.product_id "
        "WHERE c.user_id = ? AND p.is_active = 1 ORDER BY p.name",
        (user_id,),
    )


async def cart_remove(user_id: int, product_id: int):
    await _execute("DELETE FROM cart WHERE user_id = ? AND product_id = ?", (user_id, product_id))


async def cart_clear(user_id: int):
    await _execute("DELETE FROM cart WHERE user_id = ?", (user_id,))


# ---------------- Buyurtmalar ----------------
async def create_order(user_id: int, full_name: str, phone: str, address: str | None,
                       latitude: float | None = None, longitude: float | None = None) -> int | None:
    """Savatdagi mahsulotlardan buyurtma yaratadi. Savat bo'sh bo'lsa None qaytaradi."""
    items = await cart_get(user_id)
    if not items:
        return None
    total = sum(i["subtotal"] for i in items)
    async with _connect() as db:
        cur = await db.execute(
            "INSERT INTO orders (user_id, full_name, phone, address, latitude, longitude, total, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)",
            (user_id, full_name, phone, address, latitude, longitude, total, _now()),
        )
        order_id = cur.lastrowid
        await db.executemany(
            "INSERT INTO order_items (order_id, product_id, name, price, qty) VALUES (?, ?, ?, ?, ?)",
            [(order_id, i["product_id"], i["name"], i["price"], i["qty"]) for i in items],
        )
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()
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
    users = await _fetchone("SELECT COUNT(*) AS n FROM users")
    orders = await _fetchone("SELECT COUNT(*) AS n FROM orders")
    new_orders = await _fetchone("SELECT COUNT(*) AS n FROM orders WHERE status = 'new'")
    revenue = await _fetchone(
        "SELECT COALESCE(SUM(total), 0) AS s FROM orders WHERE status = 'delivered'"
    )
    products = await _fetchone("SELECT COUNT(*) AS n FROM products WHERE is_active = 1")
    return {
        "users": users["n"],
        "orders": orders["n"],
        "new_orders": new_orders["n"],
        "revenue": revenue["s"],
        "products": products["n"],
    }
