"""Aksiya (chegirma) qoidalari va narx hisoblash.

Aksiya ma'lumoti bazadagi `meta` jadvalida JSON ko'rinishida saqlanadi:
{"percent": 11, "start": "...ISO...", "end": "...ISO...", "category_id": null, "kind": "1111"}
"""
import json
from datetime import datetime

from config import now


def parse(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        promo = json.loads(raw)
        promo["_start"] = datetime.fromisoformat(promo["start"])
        promo["_end"] = datetime.fromisoformat(promo["end"])
        return promo
    except (ValueError, KeyError, TypeError):
        return None


def dump(percent: int, start: datetime, end: datetime, category_id: int | None, kind: str) -> str:
    return json.dumps({
        "percent": percent,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "category_id": category_id,
        "kind": kind,
    })


def is_running(promo: dict | None, at: datetime | None = None) -> bool:
    if not promo:
        return False
    at = at or now()
    return promo["_start"] <= at < promo["_end"]


def is_upcoming(promo: dict | None, at: datetime | None = None) -> bool:
    return bool(promo) and (at or now()) < promo["_start"]


def is_finished(promo: dict | None, at: datetime | None = None) -> bool:
    return bool(promo) and (at or now()) >= promo["_end"]


def applies(promo: dict | None, category_id: int | None) -> bool:
    """Aksiya hozir shu kategoriyadagi mahsulotga amal qiladimi."""
    if not is_running(promo):
        return False
    return promo.get("category_id") in (None, category_id)


def discounted(price: int, percent: int) -> int:
    """Chegirmali narx. Katta summalar 100 so'mgacha yaxlitlanadi (mijoz foydasiga)."""
    value = price * (100 - percent) / 100
    if price >= 1000:
        value = int(value // 100 * 100)
    return max(int(value), 1)


def price_info(price: int, category_id: int | None, promo: dict | None) -> tuple[int, int | None, int | None]:
    """(yakuniy narx, eski narx yoki None, chegirma foizi yoki None)."""
    if applies(promo, category_id):
        return discounted(price, promo["percent"]), price, promo["percent"]
    return price, None, None
