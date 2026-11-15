"""Mahsulot ranglari: tayyor ranglar (4 tilda) va admin yozgan maxsus ranglar.

Mahsulotda ranglar JSON ro'yxat sifatida saqlanadi, masalan: ["yg", "wg", "Yashil|Зелёный|Сабз|Жасыл"].
- Qisqa kodlar (yg, wg, ...) — tayyor ranglar;
- Boshqa matn — maxsus rang («|» bilan 4 tilda yozilishi mumkin: uz | ru | tg | kk).
"""
import json

from i18n import LANGS

PRESETS: dict[str, dict] = {
    "yg": {"emoji": "🟡", "hex": "#d9b44a", "uz": "Sariq oltin", "ru": "Жёлтое золото", "tg": "Тиллои зард", "kk": "Сары алтын"},
    "wg": {"emoji": "⚪", "hex": "#e9e9e4", "uz": "Oq oltin", "ru": "Белое золото", "tg": "Тиллои сафед", "kk": "Ақ алтын"},
    "rg": {"emoji": "🟠", "hex": "#e3a08f", "uz": "Qizil oltin", "ru": "Розовое золото", "tg": "Тиллои гулобӣ", "kk": "Қызғылт алтын"},
    "sv": {"emoji": "🔘", "hex": "#c4c7cc", "uz": "Kumush", "ru": "Серебро", "tg": "Нуқра", "kk": "Күміс"},
    "pt": {"emoji": "⬜", "hex": "#dcdcd6", "uz": "Platina", "ru": "Платина", "tg": "Платина", "kk": "Платина"},
    "bk": {"emoji": "⚫", "hex": "#2b2b2b", "uz": "Qora", "ru": "Чёрный", "tg": "Сиёҳ", "kk": "Қара"},
}
MAX_COLORS = 8


def product_colors(product: dict) -> list[str]:
    raw = product.get("colors")
    if not raw:
        return []
    try:
        values = json.loads(raw)
        return [str(v) for v in values if v] if isinstance(values, list) else []
    except ValueError:
        return []


def dump(colors: list[str]) -> str | None:
    return json.dumps(colors, ensure_ascii=False) if colors else None


def name(color: str, lang: str) -> str:
    """Rang nomi foydalanuvchi tilida (emoji siz)."""
    if color in PRESETS:
        return PRESETS[color][lang]
    parts = [p.strip() for p in color.split("|")]
    by_lang = dict(zip(LANGS, parts))
    return by_lang.get(lang) or parts[0]


def label(color: str, lang: str) -> str:
    """Rang nomi emoji bilan (tugmalar uchun)."""
    emoji = PRESETS[color]["emoji"] if color in PRESETS else "🎨"
    return f"{emoji} {name(color, lang)}"


def hex_color(color: str) -> str | None:
    return PRESETS[color]["hex"] if color in PRESETS else None


def parse_custom(text: str) -> list[str]:
    """Admin yozgan maxsus ranglar: vergul bilan ajratilgan, har biri «uz | ru | tg | kk» bo'lishi mumkin."""
    result = []
    for chunk in text.split(","):
        parts = [p.strip().replace(":", "") for p in chunk.split("|")]
        parts = [p[:30] for p in parts if p]
        if parts:
            result.append("|".join(parts))
    return result
