"""Brauzer (PWA) rejimi uchun avtorizatsiya: «Telegram orqali kirish» (Login Widget) va sessiya cookie.

- Login Widget ma'lumotlari bot tokeni bilan imzolangan bo'ladi — tekshiramiz (Telegram hujjatidagi algoritm):
  secret = SHA256(bot_token); hash = HMAC_SHA256(secret, "key=value\\n..." saralangan).
- Kirgandan keyin brauzerga HttpOnly cookie beriladi: "<user_id>.<muddati>.<imzo>".
"""
import hashlib
import hmac
import time

LOGIN_MAX_AGE = 24 * 3600            # widget ma'lumoti 1 kundan eski bo'lmasin
SESSION_MAX_AGE = 30 * 24 * 3600     # sessiya 30 kun amal qiladi
COOKIE_NAME = "sid"


def verify_login_widget(bot_token: str, data: dict) -> dict | None:
    """Telegram Login Widget ma'lumotini tekshiradi. To'g'ri bo'lsa — foydalanuvchi ma'lumoti, aks holda None."""
    if not isinstance(data, dict):
        return None
    received_hash = str(data.get("hash") or "")
    fields = {k: str(v) for k, v in data.items() if k != "hash" and v is not None}
    if not received_hash or "id" not in fields or "auth_date" not in fields:
        return None
    check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return None
    try:
        auth_date = int(fields["auth_date"])
        user_id = int(fields["id"])
    except ValueError:
        return None
    if time.time() - auth_date > LOGIN_MAX_AGE:
        return None
    return {
        "id": user_id,
        "first_name": fields.get("first_name", ""),
        "last_name": fields.get("last_name", ""),
        "username": fields.get("username"),
    }


def _session_key(bot_token: str) -> bytes:
    return hashlib.sha256(f"session:{bot_token}".encode()).digest()


def make_session(bot_token: str, user_id: int, now: float | None = None) -> str:
    expires = int((now or time.time()) + SESSION_MAX_AGE)
    payload = f"{user_id}.{expires}"
    signature = hmac.new(_session_key(bot_token), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def parse_session(bot_token: str, value: str | None) -> int | None:
    """Cookie qiymatidan foydalanuvchi ID si (imzo yoki muddat noto'g'ri bo'lsa — None)."""
    if not value or value.count(".") != 2:
        return None
    user_id, expires, signature = value.split(".")
    expected = hmac.new(_session_key(bot_token), f"{user_id}.{expires}".encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    if not (user_id.isdigit() and expires.isdigit()) or int(expires) < time.time():
        return None
    return int(user_id)
