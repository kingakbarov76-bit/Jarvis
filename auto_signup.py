"""Auto-signup, captcha aniqlash, vaqtinchalik email."""
import os, json, re, time, asyncio, httpx

TEMP_MAIL_API = "https://api.mail.tm"


async def create_temp_email():
    """Vaqtinchalik email yaratadi (mail.tm — bepul, captcha yo'q)."""
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            # Domen olish
            r = await cl.get(f"{TEMP_MAIL_API}/domains")
            domains = r.json().get("hydra:member", [])
            if not domains:
                return None
            domain = domains[0]["domain"]
            # Random nom
            import random, string
            name = "jarvis" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
            email = f"{name}@{domain}"
            password = "Jarvis" + str(random.randint(100000, 999999))
            # Akkaunt yaratish
            r = await cl.post(f"{TEMP_MAIL_API}/accounts",
                              json={"address": email, "password": password})
            if r.status_code not in (200, 201):
                return None
            # Token olish
            r = await cl.post(f"{TEMP_MAIL_API}/token",
                              json={"address": email, "password": password})
            if r.status_code != 200:
                return None
            token = r.json().get("token")
            return {"email": email, "password": password, "token": token}
    except Exception as e:
        return {"error": str(e)[:200]}


async def read_temp_inbox(token):
    """Vaqtinchalik emailga kelgan xatlarni o‘qiydi."""
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            r = await cl.get(f"{TEMP_MAIL_API}/messages",
                             headers={"Authorization": f"Bearer {token}"})
            msgs = r.json().get("hydra:member", [])
            out = []
            for m in msgs[:5]:
                out.append({
                    "from": m.get("from", {}).get("address", "?"),
                    "subject": m.get("subject", "?"),
                    "id": m.get("id")
                })
            return out
    except Exception as e:
        return [{"error": str(e)[:100]}]


async def read_message(token, msg_id):
    """Xat matnini o‘qiydi."""
    try:
        async with httpx.AsyncClient(timeout=20) as cl:
            r = await cl.get(f"{TEMP_MAIL_API}/messages/{msg_id}",
                             headers={"Authorization": f"Bearer {token}"})
            data = r.json()
            text = data.get("text", "") or data.get("html", [""])[0] if data.get("html") else ""
            return text[:2000]
    except Exception:
        return ""


async def extract_otp(text):
    """Matndan 4-8 xonali kodni topadi."""
    if not text:
        return None
    codes = re.findall(r'\b(\d{4,8})\b', text)
    for c in codes:
        if 4 <= len(c) <= 8:
            return c
    return None


def detect_protection(html):
    """Saytda qanday himoya borligini aniqlaydi."""
    if not html:
        return "unknown"
    low = html.lower()
    if "recaptcha" in low or "g-recaptcha" in low:
        return "recaptcha"
    if "hcaptcha" in low:
        return "hcaptcha"
    if "cf-challenge" in low or "cloudflare" in low or "just a moment" in low:
        return "cloudflare"
    if "turnstile" in low:
        return "turnstile"
    if "captcha" in low:
        return "generic_captcha"
    return "none"


async def try_auto_signup(url, email=None, password=None):
    """Saytga ro'yxatdan o'tishga urinadi. To'siqni aniqlaydi."""
    result = {"status": "unknown", "protection": None, "url": url, "message": ""}
    try:
        ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": ua},
                                     follow_redirects=True) as cl:
            r = await cl.get(url)
        result["status_code"] = r.status_code
        protection = detect_protection(r.text)
        result["protection"] = protection
        if protection == "none":
            result["status"] = "ready"
            result["message"] = "To'siq yo'q — avtomatik urinish mumkin"
        else:
            result["status"] = "blocked"
            result["message"] = f"To'siq: {protection}"
        return result
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)[:200]
        return result
