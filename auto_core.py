"""JARVIS Auto-Core — o'zi qidiradi, qo'shadi, tuzatadi."""
import os, json, ast, asyncio, time, shutil, subprocess, re, httpx

HOME = os.path.expanduser("~")
SKILLS = os.path.join(HOME, "skills")
SERVICES = os.path.join(HOME, "services.json")
SKILL_REG = os.path.join(HOME, "skills_registry.json")
LOG = os.path.join(HOME, "auto.log")
os.makedirs(SKILLS, exist_ok=True)


def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")
    except Exception:
        pass


def load_json(path, default=None):
    try:
        return json.load(open(path))
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    try:
        json.dump(data, open(path, "w"), ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def test_code(code):
    """Sintaksis + xavfsizlik tekshiruvi."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax: {e}"
    banned = ["os.system", "eval(", "__import__", "subprocess.call(['rm",
              "subprocess.run(['rm", "shutil.rmtree", "open('/etc",
              "open('/sys", "open('/data/data/com.termux/files/usr/etc"]
    for b in banned:
        if b in code:
            return False, f"Xavfli: {b}"
    return True, "OK"


async def search_web(query):
    """Bepul qidiruv (DDG Lite)."""
    try:
        ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36"
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": ua},
                                     follow_redirects=True) as cl:
            r = await cl.post("https://lite.duckduckgo.com/lite/", data={"q": query})
        titles = re.findall(r'class="result-link"[^>]*>(.*?)</a>', r.text, re.DOTALL)[:6]
        urls = re.findall(r'href="(https?://[^"]+)"', r.text)[:6]
        out = []
        for t, u in zip(titles, urls):
            tt = re.sub(r'<[^>]+>', '', t).strip()
            if tt:
                out.append(f"{tt[:80]} | {u[:80]}")
        return out
    except Exception as e:
        log(f"search err: {e}")
        return []


async def write_skill_code(desc, groq_client, model):
    """LLM orqali skill kodi yozadi."""
    prompt = (
        "Sen Python dasturchi. ASYNC funksiya yoz.\n"
        "Signature: async def run(args: str) -> str:\n"
        "args - string, return - string javob.\n"
        "FAQAT standart kutubxona + httpx. Izohsiz.\n"
        "```python ... ``` blokida ber.\n\n"
        f"VAZIFA: {desc}"
    )
    try:
        r = await groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500, temperature=0.2)
        code = r.choices[0].message.content
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()
        return code
    except Exception as e:
        log(f"write err: {e}")
        return None


async def save_skill(name, code, desc=""):
    """Skillni saqlaydi (test + backup)."""
    ok, msg = test_code(code)
    if not ok:
        return False, msg
    path = os.path.join(SKILLS, name + ".py")
    if os.path.exists(path):
        shutil.copy2(path, path + f".{int(time.time())}.bak")
    with open(path, "w") as f:
        f.write(code)
    # Import test
    try:
        ns = {}
        exec("import asyncio,httpx,os,json,re,time,datetime,base64,tempfile\n" + code, ns)
        if "run" not in ns or not asyncio.iscoroutinefunction(ns["run"]):
            os.remove(path)
            return False, "run() yo'q yoki async emas"
    except Exception as e:
        os.remove(path)
        return False, f"Load: {str(e)[:100]}"
    reg = load_json(SKILL_REG, {})
    reg[name] = {"desc": desc, "created": time.time()}
    save_json(SKILL_REG, reg)
    log(f"skill saved: {name}")
    return True, "OK"


async def run_skill(name, args=""):
    path = os.path.join(SKILLS, name + ".py")
    if not os.path.exists(path):
        return f"❌ Skill yo'q: {name}"
    try:
        ns = {}
        exec("import asyncio,httpx,os,json,re,time,datetime,base64,tempfile\n" + open(path).read(), ns)
        return str(await ns["run"](args))[:3000]
    except Exception as e:
        return f"❌ {str(e)[:200]}"


def list_skills():
    reg = load_json(SKILL_REG, {})
    return [f"• `{k}` — {v.get('desc','')[:60]}" for k, v in reg.items()]


# ═══════════════ AUTONOMOUS LOOPS ═══════════════

FREE_AI_SOURCES = [
    {"name": "Groq",       "url": "https://api.groq.com/openai/v1",     "key_url": "console.groq.com/keys"},
    {"name": "Gemini",     "url": "https://generativelanguage.googleapis.com/v1beta", "key_url": "aistudio.google.com/app/apikey"},
    {"name": "OpenRouter", "url": "https://openrouter.ai/api/v1",       "key_url": "openrouter.ai/keys"},
    {"name": "Together",   "url": "https://api.together.xyz/v1",        "key_url": "api.together.xyz"},
    {"name": "DeepInfra",  "url": "https://api.deepinfra.com/v1/openai", "key_url": "deepinfra.com/dash"},
    {"name": "Cerebras",   "url": "https://api.cerebras.ai/v1",         "key_url": "cloud.cerebras.ai"},
    {"name": "SambaNova",  "url": "https://api.sambanova.ai/v1",        "key_url": "cloud.sambanova.ai"},
    {"name": "Hyperbolic", "url": "https://api.hyperbolic.xyz/v1",      "key_url": "app.hyperbolic.xyz"},
    {"name": "Mistral",    "url": "https://api.mistral.ai/v1",          "key_url": "console.mistral.ai"},
    {"name": "Fireworks",  "url": "https://api.fireworks.ai/inference/v1", "key_url": "fireworks.ai"},
]


async def discover_missing(owner, bot, groq_client, model):
    """Nima yetishmayotganini topadi va sizga aytadi."""
    svc = load_json(SERVICES, {})
    reg = load_json(SKILL_REG, {})
    have = set(svc.keys()) | set(reg.keys())
    needed = ["video", "music", "voice_clone", "browser", "image_gen", "captcha"]
    missing = [n for n in needed if n not in have and not any(n in h for h in have)]
    if not missing:
        return
    msg = "🧬 JARVIS aniqladi — quyidagilar yetishmayapti:\n\n"
    for need in missing:
        msg += f"📌 **{need}**\n"
        for s in FREE_AI_SOURCES[:3]:
            msg += f"   • [{s['name']}]({s['key_url']})\n"
        msg += "\n"
    msg += "💡 Ushbu xizmatlardan biriga ro'yxatdan o'tib, menga kalitni yuboring:\n"
    msg += "`/addservice <nom> | <url> | <tavsif> | <kalit>`\n"
    try:
        await bot.send_message(owner, msg, parse_mode="Markdown")
        log("discover: report sent")
    except Exception as e:
        log(f"discover msg err: {e}")


async def self_analyze(owner, bot, groq_client, model):
    """O'zini tahlil qiladi va yangi g'oya topadi."""
    try:
        reg = load_json(SKILL_REG, {})
        svc = load_json(SERVICES, {})
        have = ", ".join(list(reg.keys())[:15] + list(svc.keys())[:15]) or "yoq"
        prompt = (
            f"Sen JARVIS. Skillelarim: {have}\n"
            "Menga qanday yangi qobiliyat kerak? 1 jumla, o'zbekcha, 150 belgidan kam. "
            "Faqat g'oyani yoz."
        )
        r = await groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120)
        idea = r.choices[0].message.content.strip().strip('"').strip("'")
        if not (10 < len(idea) < 200):
            return None
        # Skill kod yozish
        code = await write_skill_code(idea, groq_client, model)
        if not code:
            return None
        name = "auto_" + str(int(time.time()))[-6:]
        ok, msg = await save_skill(name, code, idea)
        if not ok:
            log(f"self_analyze save fail: {msg}")
            return None
        # Sinash
        try:
            test = await run_skill(name, "test")
        except Exception:
            test = "?"
        # Hisobot
        try:
            await bot.send_message(owner,
                f"🧬 Rivojlandim!\n\n"
                f"💡 G'oya: {idea}\n"
                f"📛 Skill: `{name}`\n"
                f"🧪 Test: {str(test)[:150]}\n\n"
                f"/runskill {name}",
                parse_mode="Markdown")
        except Exception as e:
            log(f"report err: {e}")
        log(f"self_analyze created: {name} — {idea}")
        return name
    except Exception as e:
        log(f"self_analyze err: {e}")
        return None


async def autonomous_loop(owner, bot, groq_client, model):
    """Asosiy avtonom halqa — 30 daqiqada bir."""
    await asyncio.sleep(120)  # start kutish
    while True:
        try:
            # 1. Yetishmayotganini tekshirish
            await discover_missing(owner, bot, groq_client, model)
            # 2. Yangi g'oya + skill
            await self_analyze(owner, bot, groq_client, model)
        except Exception as e:
            log(f"loop err: {e}")
        await asyncio.sleep(30 * 60)


async def send_startup_report(owner, bot):
    """Ishga tushganda sizga holat yuboradi."""
    reg = load_json(SKILL_REG, {})
    svc = load_json(SERVICES, {})
    msg = (
        "🟢 JARVIS online\n\n"
        f"📚 Skillelar: {len(reg)}\n"
        f"🔌 Xizmatlar: {len(svc)}\n"
        f"🧬 Avtonom rejim: yoqilgan (har 30 daqiqada tahlil)\n\n"
        "Men sizga har muhim voqeada xabar beraman."
    )
    try:
        await bot.send_message(owner, msg)
    except Exception as e:
        log(f"startup err: {e}")
