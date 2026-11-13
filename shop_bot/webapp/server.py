"""Sayt ko'rinishi (Telegram Mini App) uchun veb-server.

- GET  /                 — sayt sahifasi (index.html)
- GET  /api/bootstrap    — til, matnlar, kategoriyalar, mahsulotlar, aksiya, savat, brilliantlar
- POST /api/cart         — savatdagi miqdorni o'zgartirish
- GET  /api/cart         — savat hisobi (?use_bonus=1)
- POST /api/order        — buyurtma berish
- POST /api/lang         — tilni o'zgartirish
- GET  /media/{file_id}  — mahsulot rasmi/videosi (Telegram'dan olinib, keshlanadi)

Har bir /api so'rovi Telegram imzolagan initData bilan tekshiriladi (X-Init-Data sarlavhasi).
"""
import asyncio
import hashlib
import logging
import os
import time
from html import escape
from pathlib import Path

from aiogram import Bot
from aiogram.utils.web_app import safe_parse_webapp_init_data
from aiohttp import web

import colors as color_mod
import db
import pricing
from config import (
    BONUS_STEP, BONUS_VALUE, CURRENCY, MAX_WEB_MEDIA_BYTES, SHOP_NAME, SHOP_PHONE, channel_url, fmt_phone, now,
    payment_providers,
)
from db import product_sizes
from i18n import LANG_NAMES, LANGS, TEXTS, WEB_TEXTS, guess_lang, loc, remember_lang
from services import finish_order

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).parent / "static"
MEDIA_CACHE = Path(os.getenv("MEDIA_CACHE_DIR", "/tmp/shop_media_cache"))
MEDIA_CACHE_LIMIT = 500 * 1024 * 1024  # 500 MB
INIT_DATA_MAX_AGE = 24 * 3600

# Botdagi matnlardan saytga kerak bo'lganlari
BOT_KEYS = [
    "price", "sizes", "choose_size_first", "total", "saved", "to_pay", "bonus_will_earn", "pcs",
    "promo_ends_in", "promo_starts_in", "promo_footer", "prices_changed", "cart_empty", "bonus_discount_line",
    "btn_catalog", "discount", "bad_name", "bad_phone", "address_short", "dur_d", "dur_h", "dur_m",
    "promo_title_1111", "promo_title_custom", "choose_color_first",
    "in_stock", "low_stock", "out_of_stock", "btn_out_of_stock", "stock_limit", "stock_changed", "stock_left_item",
]


# ---------------- Yordamchi funksiyalar ----------------
def _texts(lang: str) -> dict:
    out = {k: TEXTS[k][lang] for k in BOT_KEYS}
    out.update({k: v[lang] for k, v in WEB_TEXTS.items()})
    return out


def _media_url(file_id: str | None) -> str | None:
    return f"/media/{file_id}" if file_id else None


def _product_json(p: dict, lang: str, promo: dict | None) -> dict:
    final, old, percent = pricing.price_info(int(p["price"]), p["category_id"], promo)
    video_ok = p.get("video_id") and (not p.get("video_size") or p["video_size"] <= MAX_WEB_MEDIA_BYTES)
    return {
        "id": p["id"],
        "category_id": p["category_id"],
        "name": loc(p, "name", lang),
        "description": loc(p, "description", lang) or "",
        "price": final,
        "old_price": old,
        "percent": percent,
        "sizes": product_sizes(p),
        "stock": db.product_stock(p),
        "colors": [
            {"key": c, "name": color_mod.name(c, lang), "hex": color_mod.hex_color(c)}
            for c in color_mod.product_colors(p)
        ],
        "photo": _media_url((db.product_photos(p) or [None])[0]),
        "photos": [_media_url(f) for f in db.product_photos(p)],
        "video": _media_url(p["video_id"]) if video_ok else None,
    }


def _cart_json(preview: dict, lang: str) -> dict:
    return {
        "items": [
            {
                "product_id": i["product_id"], "size": i["size"], "qty": i["qty"],
                "color": i["color"], "color_name": color_mod.name(i["color"], lang) if i["color"] else "",
                "stock": None if i.get("stock") is None else max(int(i["stock"]), 0),
                "name": loc(i, "name", lang), "price": i["price"], "old_price": i["old_price"],
                "percent": i["percent"], "subtotal": i["subtotal"],
            }
            for i in preview["items"]
        ],
        **{k: preview[k] for k in (
            "subtotal", "promo_discount", "balance", "max_usable", "bonus_used", "bonus_discount", "total", "bonus_earned",
        )},
        "stock_issues": _issues_json(preview.get("stock_issues") or [], lang),
    }


def _issues_json(issues: list[dict], lang: str) -> list[dict]:
    return [{"product_id": i["product_id"], "name": loc(i, "name", lang), "available": i["available"]} for i in issues]


def _promo_json(promo: dict | None, category: dict | None, lang: str) -> dict | None:
    if not promo or pricing.is_finished(promo):
        return None
    title_key = "promo_title_1111" if promo.get("kind") == "1111" else "promo_title_custom"
    if promo.get("category_id") and category:
        scope = TEXTS["promo_cat"][lang].format(p=promo["percent"], cat=escape(loc(category, "name", lang)))
    else:
        scope = TEXTS["promo_all"][lang].format(p=promo["percent"])
    return {
        "title": TEXTS[title_key][lang],
        "scope_html": scope,
        "percent": promo["percent"],
        "running": pricing.is_running(promo),
        "start": promo["_start"].isoformat(),
        "end": promo["_end"].isoformat(),
    }


# ---------------- Avtorizatsiya ----------------
@web.middleware
async def auth_middleware(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)
    init_data = request.headers.get("X-Init-Data", "")
    try:
        data = safe_parse_webapp_init_data(request.app["bot"].token, init_data)
    except ValueError:
        return web.json_response({"error": "unauthorized"}, status=401)
    if not data.user or time.time() - data.auth_date.timestamp() > INIT_DATA_MAX_AGE:
        return web.json_response({"error": "unauthorized"}, status=401)
    user = data.user
    await db.ensure_user(user.id, " ".join(x for x in [user.first_name, user.last_name] if x), user.username)
    lang = await db.get_user_lang(user.id)
    if not lang:
        lang = guess_lang(user.language_code)
    request["user"] = user
    request["lang"] = lang
    return await handler(request)


# ---------------- API ----------------
async def bootstrap(request: web.Request) -> web.Response:
    user, lang = request["user"], request["lang"]
    promo = await db.get_promo()
    category = await db.get_category(promo["category_id"]) if promo and promo.get("category_id") else None
    categories = await db.get_categories()
    products = await db.get_all_products()
    contact = await db.get_last_contact(user.id) or {}
    bot: Bot = request.app["bot"]
    me = await bot.me()
    return web.json_response({
        "lang": lang,
        "langs": LANG_NAMES,
        "texts": _texts(lang),
        "shop": {
            "name": SHOP_NAME, "phone": fmt_phone(SHOP_PHONE), "channel": channel_url(),
            "currency": CURRENCY.get(lang, CURRENCY["uz"]), "bot": me.username,
        },
        "categories": [{"id": c["id"], "name": loc(c, "name", lang)} for c in categories],
        "products": [_product_json(p, lang, promo) for p in products],
        "promo": _promo_json(promo, category, lang),
        "cart": _cart_json(await db.order_preview(user.id), lang),
        "bonus": {"balance": await db.get_bonus(user.id), "value": BONUS_VALUE, "step": BONUS_STEP},
        "contact": {
            "full_name": contact.get("full_name") or " ".join(x for x in [user.first_name, user.last_name] if x),
            "phone": contact.get("phone") or "",
            "address": contact.get("address") or "",
        },
        "payments": payment_providers(),
        "now": now().isoformat(),
    })


async def get_cart(request: web.Request) -> web.Response:
    use_bonus = request.query.get("use_bonus") == "1"
    preview = await db.order_preview(request["user"].id, use_bonus=use_bonus)
    return web.json_response(_cart_json(preview, request["lang"]))


async def set_cart(request: web.Request) -> web.Response:
    user = request["user"]
    try:
        body = await request.json()
        product_id, qty, size = int(body["product_id"]), int(body["qty"]), str(body.get("size") or "")
        color = str(body.get("color") or "")
    except (ValueError, KeyError, TypeError):
        return web.json_response({"error": "bad_request"}, status=400)
    product = await db.get_product(product_id)
    if not product:
        return web.json_response({"error": "not_found"}, status=404)
    sizes = product_sizes(product)
    if qty > 0 and sizes and size not in sizes:
        return web.json_response({"error": "size_required"}, status=400)
    if not sizes:
        size = ""
    stock = db.product_stock(product)
    if stock is not None and qty > 0:
        others = await db.cart_product_qty(user.id, product_id)
        current = next((i["qty"] for i in (await db.cart_get(user.id))
                        if i["product_id"] == product_id and i["size"] == size and i["color"] == color), 0)
        if others - current + qty > stock:
            return web.json_response({"error": "out_of_stock", "available": stock, "in_cart": others}, status=409)
    colors = color_mod.product_colors(product)
    if qty > 0 and colors and color not in colors:
        return web.json_response({"error": "color_required"}, status=400)
    if not colors and qty > 0:
        color = ""
    await db.cart_set(user.id, product_id, size, max(0, min(qty, 99)), color)
    preview = await db.order_preview(user.id, use_bonus=body.get("use_bonus") is True)
    return web.json_response(_cart_json(preview, request["lang"]))


async def place_order(request: web.Request) -> web.Response:
    user, lang = request["user"], request["lang"]
    try:
        body = await request.json()
    except ValueError:
        return web.json_response({"error": "bad_request"}, status=400)
    full_name = str(body.get("full_name") or "").strip()
    phone = str(body.get("phone") or "").strip()
    address = str(body.get("address") or "").strip()
    comment = str(body.get("comment") or "").strip()[:500] or None
    use_bonus = body.get("use_bonus") is True
    errors = []
    if not 2 <= len(full_name) <= 64:
        errors.append("full_name")
    if not 9 <= len("".join(ch for ch in phone if ch.isdigit())) <= 15:
        errors.append("phone")
    if len(address) < 5:
        errors.append("address")
    if errors:
        return web.json_response({"error": "validation", "fields": errors}, status=400)
    if not phone.startswith("+"):
        phone = "+" + phone

    preview = await db.order_preview(user.id, use_bonus=use_bonus)
    if not preview["items"]:
        return web.json_response({"error": "cart_empty"}, status=400)
    if preview["stock_issues"]:
        return web.json_response({"error": "out_of_stock", "items": _issues_json(preview["stock_issues"], lang),
                                  "cart": _cart_json(preview, lang)}, status=409)
    if preview["total"] != body.get("expected_total"):
        return web.json_response({"error": "prices_changed", "cart": _cart_json(preview, lang)}, status=409)

    try:
        order_id = await db.create_order(user.id, full_name[:64], phone, address[:300], None, None, comment, lang,
                                         use_bonus=use_bonus)
    except db.OutOfStock as e:
        fresh = await db.order_preview(user.id, use_bonus=use_bonus)
        return web.json_response({"error": "out_of_stock", "items": _issues_json(e.items, lang),
                                  "cart": _cart_json(fresh, lang)}, status=409)
    if not order_id:
        return web.json_response({"error": "cart_empty"}, status=400)
    order = await db.get_order(order_id)
    await finish_order(request.app["bot"], order_id, lang, send_summary=True)
    return web.json_response({
        "order_id": order_id, "total": order["total"], "paid": order["payment_status"] == "paid",
    })


async def set_lang(request: web.Request) -> web.Response:
    body = await request.json()
    lang = body.get("lang")
    if lang not in LANGS:
        return web.json_response({"error": "bad_request"}, status=400)
    await db.set_user_lang(request["user"].id, lang)
    remember_lang(request["user"].id, lang)
    return web.json_response({"ok": True})


# ---------------- Media (rasm/video) ----------------
_media_locks: dict[str, asyncio.Lock] = {}


def _trim_cache():
    files = sorted((f for f in MEDIA_CACHE.glob("*") if f.is_file()), key=lambda f: f.stat().st_atime)
    total = sum(f.stat().st_size for f in files)
    while files and total > MEDIA_CACHE_LIMIT:
        f = files.pop(0)
        total -= f.stat().st_size
        f.unlink(missing_ok=True)


async def media(request: web.Request) -> web.StreamResponse:
    file_id = request.match_info["file_id"]
    if not await db.is_product_media(file_id):
        raise web.HTTPNotFound()
    MEDIA_CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(file_id.encode()).hexdigest()
    lock = _media_locks.setdefault(key, asyncio.Lock())
    async with lock:
        cached = next((f for f in MEDIA_CACHE.glob(f"{key}.*") if f.suffix != ".part"), None)
        if not cached:
            bot: Bot = request.app["bot"]
            try:
                tg_file = await bot.get_file(file_id)
            except Exception as e:  # masalan, 20 MB dan katta fayl
                log.warning("Media olinmadi (%s...): %s", file_id[:12], e)
                raise web.HTTPNotFound()
            suffix = Path(tg_file.file_path or "").suffix or ".bin"
            tmp = MEDIA_CACHE / f"{key}.part"
            try:
                await bot.download_file(tg_file.file_path, destination=tmp)
            except Exception as e:
                tmp.unlink(missing_ok=True)
                log.warning("Media yuklab olinmadi (%s...): %s", file_id[:12], e)
                raise web.HTTPNotFound()
            cached = MEDIA_CACHE / f"{key}{suffix}"
            tmp.rename(cached)
            _trim_cache()
    return web.FileResponse(cached, headers={"Cache-Control": "public, max-age=604800"})


# ---------------- Bot avatari (sayt logotipi) ----------------
LOGO_MAX_AGE = 6 * 3600  # avatar o'zgarsa, 6 soat ichida saytda ham yangilanadi
_logo_lock = asyncio.Lock()


async def logo(request: web.Request) -> web.StreamResponse:
    """Botning Telegram'dagi avatari — saytdagi logotip va ikonka bot bilan bir xil bo'lishi uchun."""
    MEDIA_CACHE.mkdir(parents=True, exist_ok=True)
    path = MEDIA_CACHE / "bot_logo.jpg"
    missing_marker = MEDIA_CACHE / "bot_logo.none"
    async with _logo_lock:
        fresh = path.exists() and time.time() - path.stat().st_mtime < LOGO_MAX_AGE
        known_missing = missing_marker.exists() and time.time() - missing_marker.stat().st_mtime < LOGO_MAX_AGE
        if not fresh and not known_missing:
            bot: Bot = request.app["bot"]
            try:
                me = await bot.me()
                photos = await bot.get_user_profile_photos(me.id, limit=1)
                if photos.total_count and photos.photos:
                    tg_file = await bot.get_file(photos.photos[0][-1].file_id)
                    tmp = MEDIA_CACHE / "bot_logo.part"
                    await bot.download_file(tg_file.file_path, destination=tmp)
                    tmp.replace(path)
                    missing_marker.unlink(missing_ok=True)
                else:
                    missing_marker.touch()
            except Exception as e:
                log.warning("Bot avatari olinmadi: %s", e)
    if not path.exists():
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Cache-Control": "public, max-age=3600", "Content-Type": "image/jpeg"})


# ---------------- Sahifa ----------------
async def health(request: web.Request) -> web.Response:
    return web.json_response({"ok": True})


async def index(request: web.Request) -> web.FileResponse:
    return web.FileResponse(STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"})


def create_app(bot: Bot) -> web.Application:
    app = web.Application(middlewares=[auth_middleware], client_max_size=64 * 1024)
    app["bot"] = bot
    app.router.add_get("/", index)
    app.router.add_get("/api/bootstrap", bootstrap)
    app.router.add_get("/api/cart", get_cart)
    app.router.add_post("/api/cart", set_cart)
    app.router.add_post("/api/order", place_order)
    app.router.add_post("/api/lang", set_lang)
    app.router.add_get("/media/{file_id}", media)
    app.router.add_get("/logo", logo)
    app.router.add_static("/static/", STATIC_DIR, append_version=True)
    app.router.add_get("/health", health)
    return app


async def start_web_server(bot: Bot, port: int) -> web.AppRunner:
    runner = web.AppRunner(create_app(bot), access_log=None)
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=port).start()
    log.info("Veb-server ishga tushdi: port %s", port)
    return runner
