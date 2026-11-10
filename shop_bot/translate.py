"""Avtomatik tarjima: admin bitta tilda yozadi — bot rus, tojik, qozoq (va kerak bo'lsa o'zbek) tillariga tarjima qiladi.

Tartib:
1. ANTHROPIC_API_KEY bo'lsa — Claude (eng sifatli; zargarlik atamalari, nomlar, «» ichidagi brendlar to'g'ri).
2. Aks holda yoki Claude ishlamasa — bepul MyMemory xizmati (sifati o'rtacha, kunlik cheklov bor).
3. Hech biri ishlamasa — tarjimasiz qoladi (matn barcha tillarda bir xil ko'rinadi), admin ogohlantiriladi.

AUTO_TRANSLATE=0 — avtomatik tarjimani o'chiradi.
"""
import asyncio
import json
import logging
import os

import aiohttp

from i18n import LANGS, LANG_NAMES, parse_multilang

log = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
AUTO_TRANSLATE = os.getenv("AUTO_TRANSLATE", "1").strip() != "0"
CLAUDE_MODEL = "claude-opus-5-5"
MYMEMORY_URL = "https://api.mymemory.translated.net/get"
MYMEMORY_MAX_CHARS = 450

SYSTEM_PROMPT = (
    "You translate short texts for an online jewelry shop in Uzbekistan: product names, product descriptions, "
    "category names and color names. Return the text in four languages: uz (Uzbek, Latin script), "
    "ru (Russian), tg (Tajik, Cyrillic script), kk (Kazakh, Cyrillic script).\n"
    "- The source is usually Uzbek; if it is in another language, still return all four.\n"
    "- Keep the source text unchanged for its own language.\n"
    "- Use natural jewelry-trade wording (e.g. 'proba' -> 'проба', 'oq oltin' -> 'белое золото').\n"
    "- Proper names and brand names in quotes («Malika») are not translated; write them in the target "
    "language's script (Russian/Tajik/Kazakh: Cyrillic).\n"
    "- Keep numbers, units, sizes, emojis and punctuation as they are. Do not add explanations."
)
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {lang: {"type": "string"} for lang in LANGS},
    "required": list(LANGS),
    "additionalProperties": False,
}

_claude_client = None


def _client():
    global _claude_client
    if _claude_client is None:
        from anthropic import AsyncAnthropic
        _claude_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY, timeout=45.0, max_retries=2)
    return _claude_client


async def _claude(text: str) -> dict | None:
    """Claude orqali 4 tilga tarjima (JSON chiqish sxemasi bilan kafolatlangan)."""
    import anthropic

    try:
        response = await _client().beta.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # xavfsizlik filtri rad etsa — server boshqa modelda qayta urinadi
            system=SYSTEM_PROMPT,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
            messages=[{"role": "user", "content": text}],
        )
    except anthropic.AuthenticationError:
        log.error("ANTHROPIC_API_KEY noto'g'ri — Claude tarjimasi o'chirildi")
        return None
    except anthropic.RateLimitError:
        log.warning("Claude: so'rovlar chegarasi — bepul tarjimaga o'tilmoqda")
        return None
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        log.warning("Claude tarjimasi ishlamadi: %s", e)
        return None
    if response.stop_reason != "end_turn":
        log.warning("Claude tarjimasi to'liq emas (stop_reason=%s)", response.stop_reason)
        return None
    raw = next((b.text for b in response.content if b.type == "text"), "")
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    result = {lang: str(data.get(lang) or "").strip() for lang in LANGS}
    return result if all(result.values()) else None


async def _mymemory(session: aiohttp.ClientSession, text: str, target: str) -> str | None:
    """Bepul MyMemory xizmati orqali bitta tilga tarjima."""
    try:
        async with session.get(MYMEMORY_URL, params={"q": text, "langpair": f"uz|{target}"},
                               timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        log.warning("MyMemory (%s) ishlamadi: %s", target, e)
        return None
    if str(data.get("responseStatus")) != "200":
        return None
    translated = str((data.get("responseData") or {}).get("translatedText") or "").strip()
    # Kunlik cheklov tugaganda xizmat matn o'rniga ogohlantirish qaytaradi
    if not translated or translated.upper().startswith("MYMEMORY WARNING") or "QUERY LENGTH LIMIT" in translated.upper():
        return None
    return translated


async def _free(text: str) -> dict | None:
    if len(text) > MYMEMORY_MAX_CHARS:
        return None
    targets = [lang for lang in LANGS if lang != "uz"]
    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*(_mymemory(session, text, lang) for lang in targets))
    if not any(results):
        return None
    out = {"uz": text}
    for lang, value in zip(targets, results):
        out[lang] = value or text
    return out


async def translate_all(text: str) -> dict | None:
    """{uz, ru, tg, kk} yoki None (tarjima qilib bo'lmadi)."""
    text = text.strip()
    if not text:
        return None
    if ANTHROPIC_API_KEY:
        result = await _claude(text)
        if result:
            return result
    return await _free(text)


async def auto_i18n(text: str) -> tuple[str, str | None, str]:
    """Admin matnini saqlashga tayyorlaydi: (asosiy matn, tarjimalar JSON, holat).

    Holat: "manual" — admin «|» bilan o'zi yozgan; "auto" — avtomatik tarjima qilindi;
           "failed" — tarjima qilib bo'lmadi; "off" — avtomatik tarjima o'chirilgan."""
    if "|" in text:
        base, i18n = parse_multilang(text)
        return base, i18n, "manual"
    if not AUTO_TRANSLATE:
        return text, None, "off"
    result = await translate_all(text)
    if not result:
        return text, None, "failed"
    return result.get("uz") or text, json.dumps(result, ensure_ascii=False), "auto"


async def auto_color(text: str) -> str:
    """Maxsus rang nomi: «Yashil» -> «Yashil|Зелёный|Сабз|Жасыл» (tarjima bo'lmasa — o'zi)."""
    if "|" in text or not AUTO_TRANSLATE:
        return text
    result = await translate_all(text)
    if not result:
        return text
    return "|".join(result[lang].replace("|", "/").replace(":", "")[:30] for lang in LANGS)


def preview(i18n_json: str | None, status: str) -> str:
    """Admin uchun tarjimalar ko'rinishi."""
    if status == "failed":
        return ("\n⚠️ Avtomatik tarjima ishlamadi — matn barcha tillarda shu ko'rinishda chiqadi. "
                "Tarjimani qo'lda berish uchun «|» bilan yozing: <code>uz | ru | tg | kk</code>")
    if not i18n_json or status not in ("auto", "manual"):
        return ""
    from html import escape
    data = json.loads(i18n_json)
    lines = [f"{LANG_NAMES[lang].split()[0]} {escape(data[lang])}" for lang in LANGS if lang != "uz" and data.get(lang)]
    title = "🌐 Avtomatik tarjima:" if status == "auto" else "🌐 Tarjimalar:"
    return f"\n{title}\n" + "\n".join(lines) if lines else ""
