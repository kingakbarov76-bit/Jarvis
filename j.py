import asyncio,logging,json,os,aiosqlite,tempfile,base64,httpx,re,time,datetime,imaplib,email,smtplib,sys,subprocess,shutil
from email.mime.text import MIMEText
from urllib.parse import quote_plus
from aiogram import Bot,Dispatcher,F
from aiogram.types import Message,FSInputFile
from aiogram.filters import Command
from aiogram.enums import ChatAction
from groq import AsyncGroq
try: import edge_tts
except: edge_tts=None
try: from pypdf import PdfReader
except: PdfReader=None
try: from docx import Document
except: Document=None
try: from deep_translator import GoogleTranslator
except: GoogleTranslator=None
try: import feedparser
except: feedparser=None
T="8976119838:AAEEiFeS05RRhn-aolzCJrytcaPs2cJDm8Y"
C=os.path.expanduser("~/jcfg.json")
SK=os.path.expanduser("~/jskills.json")
TM=["llama-3.3-70b-versatile","llama-3.1-8b-instant","llama3-70b-8192","openai/gpt-oss-20b"]
WM=["whisper-large-v3","whisper-large-v3-turbo"]
VOICES={"uz":"uz-UZ-MadinaNeural","en":"en-US-AriaNeural","ru":"ru-RU-SvetlanaNeural"}
if not os.path.exists(C):
 print("SOZLASH:");o=input("TG ID: ");k=input("Groq: ");n=input("Ism: ") or "Janob"
 json.dump({"o":int(o),"k":k,"n":n,"v":"uz","d":"08:00","e":"","p":"","g":""},open(C,"w"))
if not os.path.exists(SK): json.dump({},open(SK,"w"))
c=json.load(open(C)); skills=json.load(open(SK))
O=c.get("o");N=c.get("n");K=c.get("k");V=c.get("v","uz")
D=c.get("d","08:00");E=c.get("e","");P=c.get("p","");GEMINI_KEY=c.get("g","")
logging.basicConfig(level=logging.INFO,format="%(message)s")
log=logging.getLogger("j")
g=AsyncGroq(api_key=K); db=None; TMx=WMx=None; bot=None

SYSTEM=(f"Sen JARVIS — {N}ning shaxsiy AI. Faqat o'zbek tilida qisqa javob ber. "
        f"Imlo xatolarini tushun. Noaniq bo'lsa savol ber.")

async def ini():
 global db,TMx,WMx
 db=await aiosqlite.connect(os.path.expanduser("~/j.db"))
 await db.executescript("CREATE TABLE IF NOT EXISTS m(id INTEGER PRIMARY KEY,c INT,r TEXT,t TEXT);CREATE TABLE IF NOT EXISTS rem(id INTEGER PRIMARY KEY,c INT,at REAL,txt TEXT,done INT DEFAULT 0);CREATE TABLE IF NOT EXISTS rules(id INTEGER PRIMARY KEY,rule TEXT,ts TEXT);CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY,c INT,action TEXT,status TEXT,ts TEXT);")
 await db.commit()
 try:
  ml=await g.models.list(); av=[x.id for x in ml.data]
  TMx=next((x for x in TM if x in av),av[0] if av else "llama-3.1-8b-instant")
  WMx=next((x for x in WM if x in av),"whisper-large-v3-turbo")
  log.info("T="+TMx+" W="+WMx)
 except Exception as e:
  log.error(e);TMx="llama-3.1-8b-instant";WMx="whisper-large-v3-turbo"

async def sv(cid,r,t):
 await db.execute("INSERT INTO m(c,r,t) VALUES(?,?,?)",(cid,r,t)); await db.commit()

async def hi(cid,n=10):
 cur=await db.execute("SELECT r,t FROM m WHERE c=? ORDER BY id DESC LIMIT ?",(cid,n))
 return [{"role":a,"content":b} for a,b in reversed(await cur.fetchall())]

async def srch(q):
 try:
  ua="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
  async with httpx.AsyncClient(timeout=15,headers={"User-Agent":ua},follow_redirects=True) as cl:
   r=await cl.post("https://lite.duckduckgo.com/lite/",data={"q":q})
  rows=re.findall(r'<a[^>]*class="result-link"[^>]*>(.*?)</a>',r.text,re.DOTALL)
  snips=re.findall(r'class="result-snippet"[^>]*>(.*?)</td>',r.text,re.DOTALL)
  out=[]
  for i,a in enumerate(rows[:4]):
   t=re.sub(r'<[^>]+>','',a).strip()
   s=re.sub(r'<[^>]+>','',snips[i]).strip() if i<len(snips) else ""
   if t: out.append("- "+t+": "+s[:200])
  return "\n".join(out)
 except: return ""

async def stt(p):
 for w in [WMx]+WM:
  try:
   async with httpx.AsyncClient(timeout=120) as cl:
    with open(p,"rb") as f:
     r=await cl.post("https://api.groq.com/openai/v1/audio/transcriptions",
      headers={"Authorization":"Bearer "+K},
      files={"file":("v.ogg",f,"audio/ogg")},
      data={"model":w,"language":"uz","temperature":"0",
      "prompt":"O'zbek tilida aytilgan. O'zbekiston, Toshkent, kod, JARVIS."})
    if r.status_code==200:
     t=r.json().get("text","").strip()
     if t: return t
  except: pass
 return ""

async def tts(text):
 if edge_tts is None: return None
 clean=re.sub(r'[*_`#\[\]]','',text)[:500]
 try:
  out=os.path.join(tempfile.gettempdir(),f"t_{int(time.time())}.mp3")
  await edge_tts.Communicate(clean,VOICES.get(V,VOICES["uz"])).save(out)
  return out if os.path.exists(out) else None
 except: return None

async def gen_img(prompt):
 try:
  url="https://image.pollinations.ai/prompt/"+quote_plus(prompt)+"?width=1024&height=1024&nologo=true"
  async with httpx.AsyncClient(timeout=90) as cl: r=await cl.get(url)
  if r.status_code==200:
   p=os.path.join(tempfile.gettempdir(),"gen.jpg")
   with open(p,"wb") as f: f.write(r.content)
   return p
 except: pass
 return None

def read_file(path):
 ext=os.path.splitext(path)[1].lower()
 try:
  if ext==".pdf" and PdfReader:
   r=PdfReader(path); return "\n".join((pg.extract_text() or "") for pg in r.pages)[:8000]
  if ext in(".docx",".doc") and Document:
   d=Document(path); return "\n".join(p.text for p in d.paragraphs)[:8000]
  if ext in(".txt",".md",".py",".json",".csv",".log"):
   with open(path,"r",encoding="utf-8",errors="ignore") as f: return f.read()[:8000]
 except: pass
 return None

async def gmail_read(n=5):
 if not E or not P: return "Email sozlanmagan."
 try:
  m=imaplib.IMAP4_SSL("imap.gmail.com"); m.login(E,P); m.select("INBOX")
  _,data=m.search(None,"ALL"); ids=data[0].split()[-n:][::-1]
  out=[]
  for i in ids:
   _,msg=m.fetch(i,"(RFC822)")
   e=email.message_from_bytes(msg[0][1])
   subj=e.get("Subject","?"); frm=e.get("From","?"); body=""
   if e.is_multipart():
    for part in e.walk():
     if part.get_content_type()=="text/plain":
      try: body=part.get_payload(decode=True).decode("utf-8","ignore")[:400]; break
      except: pass
   else:
    try: body=e.get_payload(decode=True).decode("utf-8","ignore")[:400]
    except: pass
   out.append(f"📧 {frm}\n📌 {subj}\n{body[:300]}")
  m.logout()
  return "\n\n".join(out) if out else "Email yo'q"
 except Exception as ex: return "Xato: "+str(ex)[:150]

async def gmail_otp():
 if not E or not P: return None,None
 try:
  m=imaplib.IMAP4_SSL("imap.gmail.com"); m.login(E,P); m.select("INBOX")
  _,data=m.search(None,"ALL"); ids=data[0].split()[-10:][::-1]
  for i in ids:
   _,msg=m.fetch(i,"(RFC822)")
   e=email.message_from_bytes(msg[0][1])
   subj=e.get("Subject","?"); frm=e.get("From","?"); body=""
   if e.is_multipart():
    for part in e.walk():
     if part.get_content_type()=="text/plain":
      try: body=part.get_payload(decode=True).decode("utf-8","ignore"); break
      except: pass
   else:
    try: body=e.get_payload(decode=True).decode("utf-8","ignore")
    except: pass
   codes=re.findall(r'\b(\d{4,8})\b',subj+"\n"+body)
   for code in codes:
    if len(code)>=4: return code,f"{frm} — {subj}"
  m.logout()
 except: pass
 return None,None

async def gmail_send(to,subj,body):
 if not E or not P: return "Email sozlanmagan."
 try:
  msg=MIMEText(body,"plain","utf-8")
  msg["Subject"]=subj; msg["From"]=E; msg["To"]=to
  s=smtplib.SMTP_SSL("smtp.gmail.com",465); s.login(E,P); s.send_message(msg); s.quit()
  return "✅ Yuborildi: "+to
 except Exception as ex: return "Xato: "+str(ex)[:150]

async def is_feedback(txt):
 low=txt.lower().strip()
 for w in["yo'q","yoq","xato","noto'g'ri","bunday emas","tushunmadim","adashding"]:
  if w in low: return True
 return False

async def get_rules():
 cur=await db.execute("SELECT rule FROM rules ORDER BY id DESC LIMIT 10")
 return [r[0] for r in await cur.fetchall()]

async def learn_rule(user_msg,bot_msg):
 try:
  p=f"Foydalanuvchi: {user_msg}\nJARVIS xatosi: {bot_msg[:300]}\n1 jumlali qoida chiqar (o'zbekcha)."
  r=await g.chat.completions.create(model=TMx,messages=[{"role":"user","content":p}],max_tokens=100)
  rule=r.choices[0].message.content.strip().strip('"').strip("'")
  if 5<len(rule)<200:
   await db.execute("INSERT INTO rules(rule,ts) VALUES(?,?)",(rule,datetime.datetime.now().isoformat()))
   await db.commit()
   return rule
 except: pass
 return None

async def gemini_img(img_b64,prompt="Bu rasmda nima? O'zbek tilida ayt."):
 if not GEMINI_KEY: return "❌ Gemini yo'q"
 try:
  url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
  body={"contents":[{"parts":[{"text":prompt},{"inline_data":{"mime_type":"image/jpeg","data":img_b64}}]}]}
  async with httpx.AsyncClient(timeout=60) as cl: r=await cl.post(url,json=body)
  if r.status_code!=200: return f"Gemini: {r.status_code}"
  return r.json()["candidates"][0]["content"]["parts"][0]["text"]
 except Exception as e: return "Xato: "+str(e)[:200]

def smart_model(txt):
 low=txt.lower()
 if any(k in low for k in["kod","code","python","function","dastur"]):
  return "coding"
 if any(k in low for k in["hisobla","matematika","mantiq","analiz"]):
  return "reasoning"
 return "fast"

async def make_backup():
 try:
  src=os.path.expanduser("~/j.db")
  bdir=os.path.expanduser("~/jarvis_full/data/backups")
  os.makedirs(bdir,exist_ok=True)
  if os.path.exists(src):
   ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
   dst=os.path.join(bdir,"j_"+ts+".db")
   shutil.copy2(src,dst)
   log.info("Backup: "+dst)
   # 7 kundan eski backup'ni o'chirish
   files=sorted([f for f in os.listdir(bdir) if f.startswith("j_")])
   for old_f in files[:-7]:
    try:os.remove(os.path.join(bdir,old_f))
    except:pass
   return dst
 except Exception as e:log.error("backup: "+str(e))
 return None

async def backup_loop():
 while True:
  await asyncio.sleep(86400)
  await make_backup()

async def need_approval(cid,action):
 await db.execute("INSERT INTO approvals(c,action,status,ts) VALUES(?,?,?,?)",(cid,action,"pending",datetime.datetime.now().isoformat()))
 await db.commit()
 cur=await db.execute("SELECT last_insert_rowid()")
 aid=(await cur.fetchone())[0]
 return aid

async def approve(cid,aid):
 await db.execute("UPDATE approvals SET status=? WHERE id=? AND c=?",("approved",aid,cid))
 await db.commit()
 return True

async def ask(cid,txt,from_voice=False):
 await sv(cid,"user",txt)
 h=await hi(cid)
 last_bot=""
 for m in reversed(h):
  if m["role"]=="assistant":
   last_bot=m["content"]
   break
 is_fb=await is_feedback(txt)
 rule_learned=None
 if is_fb and last_bot:
  prev=h[-2]["content"] if len(h)>=2 else ""
  rule_learned=await learn_rule(prev,last_bot)
 rules=await get_rules()
 rules_txt=""
 if rules:
  rules_txt="\n\nQOIDALAR:"
  for r in rules:
   rules_txt=rules_txt+"\n- "+r
 ctx="\n".join(x["role"]+": "+x["content"] for x in h[:-1])[:4000]
 sys=SYSTEM+rules_txt
 ex=""
 if not is_fb:
  low=txt.lower()
  need=False
  for k in ["ob-havo","narx","yangilik","bugun","qancha","bitcoin","kurs","qidir","yangiliklar","dollar","qachon","oxirgi"]:
   if k in low:
    need=True
    break
  if need:
   r=await srch(txt)
   if r:
    ex="\n\nInternet:\n"+r
 prefix=""
 if from_voice:
  prefix="[Ovozli xabar] "
 user_msg=prefix+ctx+"\n\nYangi: "+txt+ex
 if is_fb:
  user_msg="[Xatoni ko'rsatyapti. Uzr so'ra.] "+user_msg
 try:
  r=await g.chat.completions.create(model=TMx,messages=[{"role":"system","content":sys},{"role":"user","content":user_msg}],max_tokens=2000,temperature=0.7)
  out=r.choices[0].message.content
 except Exception as e:
  try:
   r=await g.chat.completions.create(model="llama-3.1-8b-instant",messages=[{"role":"system","content":sys},{"role":"user","content":user_msg}],max_tokens=2000)
   out=r.choices[0].message.content
  except Exception as e2:
   out="XATO: "+str(e2)[:200]
 await sv(cid,"assistant",out)
 if rule_learned:
  out=out+"\n\n[O'rgandim: "+rule_learned+"]"
 return out

def parse_dur(s):
 m=re.match(r'^(\d+)([smhd])$',s.strip().lower())
 if not m: return 0
 return int(m.group(1))*{"s":1,"m":60,"h":3600,"d":86400}[m.group(2)]

async def rem_loop():
 while True:
  await asyncio.sleep(15)
  try:
   cur=await db.execute("SELECT id,c,txt FROM rem WHERE done=0 AND at<=?",(time.time(),))
   for rid,cid,txt in await cur.fetchall():
    try: await bot.send_message(cid,"⏰ "+txt)
    except: pass
    await db.execute("UPDATE rem SET done=1 WHERE id=?",(rid,))
   await db.commit()
  except: pass

async def daily_report():
 wx="?"
 try:
  async with httpx.AsyncClient(timeout=10) as cl: r=await cl.get("https://wttr.in/Tashkent?format=%C+%t")
  wx=r.text.strip()
 except: pass
 news=""
 if feedparser:
  try:
   f=feedparser.parse("https://kun.uz/rss")
   news="\n".join(f"• {i.title}" for i in f.entries[:3])
  except: pass
 cur=await db.execute("SELECT txt FROM rem WHERE c=? AND done=0 AND at>?",(O,time.time()))
 rows=await cur.fetchall()
 remtxt="\n".join(f"• {t}" for (t,) in rows) if rows else "yo'q"
 try:
  r=await g.chat.completions.create(model=TMx,messages=[{"role":"user","content":"1 jumlali motivatsiya (o'zbekcha)"}],max_tokens=80)
  tip=r.choices[0].message.content.strip()
 except: tip="Bugun ajoyib kun!"
 msg=f"🌅 Xayrli tong, {N}!\n\n🌤 {wx}\n\n📰 {news}\n\n⏰ {remtxt}\n\n💡 {tip}"
 try: await bot.send_message(O,msg)
 except: pass

async def daily_loop():
 while True:
  now=datetime.datetime.now()
  try: hh,mm=[int(x) for x in D.split(":")]
  except: hh,mm=8,0
  target=now.replace(hour=hh,minute=mm,second=0,microsecond=0)
  if target<=now: target+=datetime.timedelta(days=1)
  await asyncio.sleep((target-now).total_seconds())
  await daily_report()
  await asyncio.sleep(60)

async def main():
 global bot,E,P,V,D,GEMINI_KEY
 await ini(); bot=Bot(T); dp=Dispatcher()
 asyncio.create_task(rem_loop())
 asyncio.create_task(daily_loop())
 def ok(m): return m.from_user.id==O

 @dp.message(Command("start"))
 async def h_start(m):
  if not ok(m): return
  await m.answer(f"Salom {N}! 🧠\n\nMen JARVIS.\n/help — buyruqlar")

 @dp.message(Command("help"))
 async def h_help(m):
  if not ok(m): return
  await m.answer("🧠 JARVIS buyruqlari:\n\n"
   "💬 Yozing | 🎤 Ovoz | 📸 Rasm\n"
   "🎨 /img matn\n"
   "🎬 /yt <url> — video yuklash\n"
   "🌐 /translate en Matn\n"
   "📰 /news\n"
   "🌤 /weather Tashkent\n"
   "⏰ /remind 5m Matn\n"
   "📧 /email /otp /send\n"
   "🔐 /signup /give /creds\n"
   "📤 /post instagram | Matn\n"
   "🧠 /build /rules /skills\n"
   "⚙️ /voice /stats /clear")

 @dp.message(Command("setemail"))
 async def h_setemail(m):
  global E
  if not ok(m): return
  p=m.text.split(maxsplit=1)
  if len(p)<2 or "@" not in p[1]: return await m.answer("Format: /setemail email@gmail.com")
  E=p[1].strip(); c["e"]=E; json.dump(c,open(C,"w"))
  await m.answer(f"✅ {E}")

 @dp.message(Command("setpass"))
 async def h_setpass(m):
  global P
  if not ok(m): return
  p=m.text.split(maxsplit=1)
  if len(p)<2: return await m.answer("Format: /setpass parol")
  P=p[1].strip().replace(" ",""); c["p"]=P; json.dump(c,open(C,"w"))
  await m.answer(f"✅ Parol ({len(P)} belgi)")

 @dp.message(Command("email"))
 async def h_email(m):
  if not ok(m): return
  await m.answer("📬..."); await m.answer(await gmail_read(5))

 @dp.message(Command("otp"))
 async def h_otp(m):
  if not ok(m): return
  await m.answer("🔍...")
  code,src=await gmail_otp()
  if code: await m.answer(f"🔑 `{code}`\n📧 {src}",parse_mode="Markdown")
  else: await m.answer("❌ OTP topilmadi")

 @dp.message(Command("send"))
 async def h_send(m):
  if not ok(m): return
  p=m.text.split(maxsplit=2)
  if len(p)<3 or "|" not in p[2]: return await m.answer("Format: /send email@x.com Mavzu | Matn")
  subj,body=p[2].split("|",1)
  await m.answer(await gmail_send(p[1].strip(),subj.strip(),body.strip()))

 @dp.message(Command("translate"))
 async def h_tr(m):
  if not ok(m): return
  p=m.text.split(maxsplit=2)
  if len(p)<3: return await m.answer("Format: /translate en Matn")
  if GoogleTranslator is None: return await m.answer("❌ deep-translator yoq")
  try:
   r=GoogleTranslator(source="auto",target=p[1]).translate(p[2])
   await m.answer(f"🌐 {r}")
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("news"))
 async def h_nw(m):
  if not ok(m): return
  if feedparser is None: return await m.answer("❌ feedparser yoq")
  try:
   f=feedparser.parse("https://kun.uz/rss")
   items=f.entries[:5]
   if not items: return await m.answer("❌ Yangilik yoq")
   out="\n\n".join(f"📰 {i.title}\n{i.link}" for i in items)
   await m.answer(out)
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("weather"))
 async def h_wx(m):
  if not ok(m): return
  p=m.text.split(maxsplit=1)
  city=p[1].strip() if len(p)>1 else "Tashkent"
  try:
   async with httpx.AsyncClient(timeout=10) as cl:
    r=await cl.get(f"https://wttr.in/{city}?format=%C+%t+%w+%h")
   await m.answer(f"🌤 {city}: {r.text.strip()}")
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("yt"))
 async def h_yt(m):
  if not ok(m): return
  p=m.text[4:].strip()
  if not p: return await m.answer("Format: /yt <url>")
  await m.answer(f"⬇️ Yuklayapman...")
  try:
   out=os.path.join(tempfile.gettempdir(),"yt_dl")
   os.makedirs(out,exist_ok=True)
   r=subprocess.run(["yt-dlp","-o",os.path.join(out,"v.%(ext)s"),
     "-f","best[filesize<50M]","--max-filesize","50M",p],
     capture_output=True,text=True,timeout=180)
   files=[f for f in os.listdir(out) if not f.endswith(".part")]
   if not files: return await m.answer(f"❌ {r.stderr[:300]}")
   f=os.path.join(out,files[0])
   sz=os.path.getsize(f)//1024//1024
   await m.answer(f"📤 ({sz}MB)...")
   with open(f,"rb") as fp: await m.answer_video(fp)
   os.remove(f)
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("backup"))
 async def h_backup(m):
  if not ok(m):return
  await m.answer("💾 Backup...")
  r=await make_backup()
  if r:await m.answer("✅ "+os.path.basename(r))
  else:await m.answer("❌ Xato")

 @dp.message(Command("pending"))
 async def h_pending(m):
  if not ok(m):return
  cur=await db.execute("SELECT id,action FROM approvals WHERE c=? AND status=?",(m.chat.id,"pending"))
  rows=await cur.fetchall()
  if not rows:return await m.answer("Tasdiq kutayotgan yo'q")
  out=["⏳ Tasdiq kutayotgan:"]
  for aid,act in rows:out.append(f"#{aid}: {act[:100]}")
  out.append("\nTasdiqlash: /approve <id>")
  await m.answer("\n".join(out))

 @dp.message(Command("approve"))
 async def h_approve(m):
  if not ok(m):return
  p=m.text.split()
  if len(p)<2:return await m.answer("Format: /approve <id>")
  try:aid=int(p[1])
  except:return await m.answer("ID raqam bo'lishi kerak")
  r=await approve(m.chat.id,aid)
  if r:await m.answer(f"✅ #{aid} tasdiqlandi")
  else:await m.answer("❌ Topilmadi")

 @dp.message(Command("build"))
 async def h_build(m):
  if not ok(m): return
  p=m.text[7:].split("|",1)
  if len(p)<2: return await m.answer("Format: /build nom | vazifa")
  await m.answer(f"🧠 {p[0].strip()}...")
  try:
   pr=f"Yangi Python funksiya: {p[0].strip()}\nVazifa: {p[1].strip()}\nFaqat kod ```python ... ```"
   r=await g.chat.completions.create(model=TMx,messages=[{"role":"user","content":pr}],max_tokens=1000,temperature=0.2)
   code=r.choices[0].message.content
   if "```python" in code: code=code.split("```python")[1].split("```")[0].strip()
   elif "```" in code: code=code.split("```")[1].split("```")[0].strip()
   skills[p[0].strip()]={"code":code,"desc":p[1].strip()}
   json.dump(skills,open(SK,"w"))
   await m.answer(f"✅ `{p[0].strip()}`\n\n```python\n{code[:1200]}\n```",parse_mode="Markdown")
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("skills"))
 async def h_skills(m):
  if not ok(m): return
  if not skills: return await m.answer("Qobiliyat yo'q.")
  out=["🧠 Qobiliyatlar:\n"]
  for name,info in skills.items(): out.append(f"• `{name}` — {info['desc'][:80]}")
  await m.answer("\n".join(out),parse_mode="Markdown")

 @dp.message(Command("rules"))
 async def h_rules(m):
  if not ok(m): return
  rules=await get_rules()
  if not rules: return await m.answer("Hali qoida yo'q.")
  await m.answer("🧠 Qoidalar:\n"+"\n".join(f"• {r}" for r in rules))

 @dp.message(Command("forget"))
 async def h_forget(m):
  if not ok(m): return
  await db.execute("DELETE FROM rules"); await db.commit()
  await m.answer("🗑")

 @dp.message(Command("signup"))
 async def h_signup(m):
  if not ok(m): return
  p=m.text.split(maxsplit=2)
  if len(p)<3: return await m.answer("Format: /signup <service> <url>")
  svc=p[1].strip().lower(); url=p[2].strip()
  try:
   sys.path.insert(0,os.path.expanduser("~/jarvis_full"))
   from tools.auto_signup import try_signup
   await m.answer(f"🔍 {svc}...")
   r=await try_signup(url,"auto","auto")
   if r.get("ok"): await m.answer(f"✅ {svc} ro'yxatdan o'tdi")
   else: await m.answer(f"⚠️ {r.get('message','')}\n\n🔗 {url}\n\nQo'lda ro'yxatdan o'tib:\n/give {svc} user:pass:email")
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("give"))
 async def h_give(m):
  if not ok(m): return
  p=m.text.split(maxsplit=2)
  if len(p)<3: return await m.answer("Format: /give <service> <user:pass:email>")
  svc=p[1].strip().lower(); data=p[2].strip()
  try:
   sys.path.insert(0,os.path.expanduser("~/jarvis_full"))
   from tools.auto_signup import save_cred
   parts=data.split(":")
   cred={"raw":data}
   if len(parts)>=2: cred["username"]=parts[0]; cred["password"]=parts[1]
   if len(parts)>=3: cred["email"]=parts[2]
   if save_cred(svc,cred): await m.answer(f"✅ {svc} saqlandi")
   else: await m.answer("❌ Saqlanmadi")
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("creds"))
 async def h_creds(m):
  if not ok(m): return
  try:
   sys.path.insert(0,os.path.expanduser("~/jarvis_full"))
   from tools.auto_signup import list_creds
   cc=list_creds()
   if not cc: return await m.answer("📋 Yo'q")
   await m.answer("📋 Akkauntlar:\n"+"\n".join(f"• {s}" for s in cc))
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("post"))
 async def h_post(m):
  if not ok(m): return
  p=m.text[6:].split("|",1)
  if len(p)<2: return await m.answer("Format: /post instagram | Matn")
  plat=p[0].strip().lower(); text=p[1].strip()
  try:
   sys.path.insert(0,os.path.expanduser("~/jarvis_full"))
   from tools.social import post as sp
   await m.answer(f"📤 {plat}...")
   r=await sp(plat,text)
   await m.answer(r)
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(Command("daily"))
 async def h_daily(m):
  global D
  if not ok(m): return
  p=m.text.split()
  if len(p)<2: return await m.answer(f"Hisobot: {D}")
  if ":" not in p[1]: return await m.answer("Format: /daily 08:00")
  D=p[1]; c["d"]=D; json.dump(c,open(C,"w"))
  await m.answer(f"✅ {D}")

 @dp.message(Command("now"))
 async def h_now(m):
  if not ok(m): return
  await m.answer("📊..."); await daily_report()

 @dp.message(Command("voice"))
 async def h_voice(m):
  global V
  if not ok(m): return
  p=m.text.split()
  if len(p)<2: return await m.answer("Tillar: uz, ru, en. Hozir: "+V)
  if p[1] not in VOICES: return await m.answer("Faqat: uz, ru, en")
  V=p[1]; c["v"]=V; json.dump(c,open(C,"w"))
  await m.answer("✅ "+V)

 @dp.message(Command("remind"))
 async def h_remind(m):
  if not ok(m): return
  p=m.text.split(maxsplit=2)
  if len(p)<3: return await m.answer("Format: /remind 5m Choy")
  sec=parse_dur(p[1])
  if not sec: return await m.answer("Vaqt: 30s, 5m, 2h, 1d")
  await db.execute("INSERT INTO rem(c,at,txt) VALUES(?,?,?)",(m.chat.id,time.time()+sec,p[2]))
  await db.commit()
  await m.answer("✅ "+p[1]+" keyin: "+p[2])

 @dp.message(Command("reminders"))
 async def h_reminders(m):
  if not ok(m): return
  cur=await db.execute("SELECT at,txt FROM rem WHERE c=? AND done=0 ORDER BY at",(m.chat.id,))
  rows=await cur.fetchall()
  if not rows: return await m.answer("Yo'q")
  now=time.time(); out=[f"• {int(at-now)//60}d {int(at-now)%60}s — {txt}" for at,txt in rows if at>now]
  await m.answer("⏰\n"+"\n".join(out))

 @dp.message(Command("clear"))
 async def h_clear(m):
  if not ok(m): return
  await db.execute("DELETE FROM m WHERE c=?",(m.chat.id,)); await db.commit()
  await m.answer("🗑")

 @dp.message(Command("stats"))
 async def h_stats(m):
  if not ok(m): return
  cur=await db.execute("SELECT COUNT(*) FROM m WHERE c=?",(m.chat.id,)); n=(await cur.fetchone())[0]
  cur=await db.execute("SELECT COUNT(*) FROM rem WHERE c=? AND done=0",(m.chat.id,)); r=(await cur.fetchone())[0]
  rules=await get_rules()
  gem="✅" if GEMINI_KEY else "❌"
  await m.answer(f"📊 Xabar: {n}\n⏰ Eslatma: {r}\n🧠 Skill: {len(skills)}\n📚 Qoida: {len(rules)}\n🔊 Til: {V}\n🌅 {D}\n📧 {E or 'yoq'}\n🤖 Gemini: {gem}")

 @dp.message(Command("img"))
 async def h_img(m):
  if not ok(m): return
  p=m.text[5:].strip()
  if not p: return await m.answer("Format: /img mushuk")
  await m.answer("🎨...")
  path=await gen_img(p)
  if path:
   with open(path,"rb") as f: await m.answer_photo(f,caption=p)
   os.remove(path)
  else: await m.answer("❌")

 @dp.message(F.voice)
 async def h_v(m):
  if not ok(m): return
  await bot.send_chat_action(m.chat.id,ChatAction.TYPING)
  p=os.path.join(tempfile.gettempdir(),"v.ogg")
  try:
   f=await bot.get_file(m.voice.file_id)
   await bot.download_file(f.file_path,destination=p)
   t=await stt(p)
   if not t: return await m.answer("Tushunmadim.")
   await m.answer("🎤 "+t)
   resp=await ask(m.chat.id,t,from_voice=True)
   await m.answer(resp)
   vp=await tts(resp[:500])
   if vp:
    await m.answer_voice(FSInputFile(vp)); os.remove(vp)
  except Exception as e: await m.answer(f"Xato: {e}")
  finally:
   if os.path.exists(p): os.remove(p)

 @dp.message(F.photo)
 async def h_ph(m):
  if not ok(m): return
  if not GEMINI_KEY: return await m.answer("📸 Gemini yo'q")
  await bot.send_chat_action(m.chat.id,ChatAction.TYPING)
  try:
   f=await bot.get_file(m.photo[-1].file_id)
   pp=os.path.join(tempfile.gettempdir(),"p.jpg")
   await bot.download_file(f.file_path,destination=pp)
   with open(pp,"rb") as fp: bb=base64.b64encode(fp.read()).decode()
   os.remove(pp)
   cap=m.caption or "Bu rasmda nima? O'zbek tilida ayt."
   await m.answer(await gemini_img(bb,cap))
  except Exception as e: await m.answer(f"❌ {e}")

 @dp.message(F.document)
 async def h_doc(m):
  if not ok(m): return
  await bot.send_chat_action(m.chat.id,ChatAction.TYPING)
  try:
   f=await bot.get_file(m.document.file_id)
   ext=os.path.splitext(m.document.file_name or "")[1]
   pp=os.path.join(tempfile.gettempdir(),"doc"+ext)
   await bot.download_file(f.file_path,destination=pp)
   txt=read_file(pp); os.remove(pp)
   if not txt: return await m.answer("PDF/DOCX/TXT yuboring")
   q=(m.caption or "Faylni tahlil qil")+f"\n\n--- Fayl ---\n{txt}"
   await m.answer(await ask(m.chat.id,q))
  except Exception as e: await m.answer(str(e))

 @dp.message(F.text)
 async def h_text(m):
  global GEMINI_KEY
  if not ok(m): return
  txt=m.text.strip()
  if txt.startswith("AIza") or (len(txt)>30 and " " not in txt and "/" not in txt and "@" not in txt and len(txt)<100):
   GEMINI_KEY=txt; c["g"]=GEMINI_KEY; json.dump(c,open(C,"w"))
   await m.answer("✅ Gemini saqlandi!")
   return
  await bot.send_chat_action(m.chat.id,ChatAction.TYPING)
  try: await m.answer(await ask(m.chat.id,txt))
  except Exception as e: await m.answer(f"❌ {e}")

 log.info("Bot ishga tushdi")
 await bot.delete_webhook(drop_pending_updates=True)
 await dp.start_polling(bot)

asyncio.run(main())
