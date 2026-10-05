"""Skills Engine — j.py'ni buzmagan holda yangi qobiliyatlar."""
import os, json, ast, asyncio, subprocess, time, importlib.util, shutil

SKILLS_DIR = os.path.expanduser("~/skills")
REGISTRY = os.path.expanduser("~/skills_registry.json")
BACKUP_DIR = os.path.expanduser("~/skills_backup")
os.makedirs(SKILLS_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)


def load_registry():
    if not os.path.exists(REGISTRY):
        return {}
    try:
        return json.load(open(REGISTRY))
    except Exception:
        return {}


def save_registry(r):
    json.dump(r, open(REGISTRY, "w"), ensure_ascii=False, indent=2)


def test_code(code):
    """Sintaksis va xavfsizlikni tekshiradi."""
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax: {e}"
    banned = ["os.system", "eval(", "exec(", "__import__", "open('/etc", "subprocess.call(['rm"]
    for b in banned:
        if b in code:
            return False, f"Xavfli: {b}"
    return True, "OK"


def load_skill(name):
    """Skill faylini yuklab, funksiyani qaytaradi."""
    path = os.path.join(SKILLS_DIR, name + ".py")
    if not os.path.exists(path):
        return None
    try:
        spec = importlib.util.spec_from_file_location("skill_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "run"):
            return mod.run
    except Exception:
        return None
    return None


async def save_skill(name, code, desc=""):
    """Skillni xavfsiz saqlaydi (backup + test)."""
    ok, msg = test_code(code)
    if not ok:
        return False, msg
    path = os.path.join(SKILLS_DIR, name + ".py")
    # Backup
    if os.path.exists(path):
        shutil.copy2(path, os.path.join(BACKUP_DIR, f"{name}_{int(time.time())}.py.bak"))
    with open(path, "w") as f:
        f.write(code)
    # Test: import qilinadimi
    try:
        spec = importlib.util.spec_from_file_location("skill_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if not hasattr(mod, "run"):
            os.remove(path)
            return False, "run() yo'q"
    except Exception as e:
        os.remove(path)
        return False, f"Load: {str(e)[:100]}"
    # Registry
    r = load_registry()
    r[name] = {"desc": desc, "created": time.time()}
    save_registry(r)
    return True, "OK"


async def run_skill(name, args=""):
    fn = load_skill(name)
    if fn is None:
        return "❌ Skill yo'q: " + name
    try:
        result = await fn(args)
        return str(result)[:4000]
    except Exception as e:
        return f"❌ Xato: {str(e)[:200]}"


def list_skills():
    r = load_registry()
    out = []
    for k, v in r.items():
        desc = v.get("desc", "")[:60] if isinstance(v, dict) else ""
        out.append(f"• `{k}` — {desc}")
    return out
