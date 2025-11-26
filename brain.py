# mass_hunter_v14.py
import os
import json
import re
import time
import requests
from typing import List, Optional, Dict
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from langchain_groq import ChatGroq

# ----------------------------
# Config / Env
# ----------------------------
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY")
SERPER_KEYS = [k.strip() for k in SERPER_KEYS_RAW.split(',') if k.strip()] if SERPER_KEYS_RAW else []

# Tunables
SERPER_NUM = 50
SERPER_GL = "eg"
SERPER_HL = "ar"
SERPER_KEY_MIN_INTERVAL = 0.6  # seconds between uses for a single key (simple rate limit)

print(f"--- Mass Hunter V14 --- serper keys: {len(SERPER_KEYS)}")

# ----------------------------
# Clients init
# ----------------------------
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.2, api_key=GROQ_API_KEY) if GROQ_API_KEY else None
    print("✅ System: Supabase/LLM clients init (if keys present).")
except Exception as e:
    print("⚠️ Client init error:", e)
    supabase = None
    llm = None

app = FastAPI()

# ----------------------------
# Pydantic models
# ----------------------------
class HuntRequest(BaseModel):
    intent_sentence: str
    city: str

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# ----------------------------
# Helpers: Key rotation + Rate limiting
# ----------------------------
key_index = 0
key_last_used: Dict[str, float] = {}

def get_active_key() -> Optional[str]:
    global key_index, key_last_used
    if not SERPER_KEYS:
        return None
    attempts = 0
    while attempts < len(SERPER_KEYS):
        k = SERPER_KEYS[key_index]
        now = time.time()
        last = key_last_used.get(k, 0)
        if now - last >= SERPER_KEY_MIN_INTERVAL:
            key_last_used[k] = now
            key_index = (key_index + 1) % len(SERPER_KEYS)
            return k
        else:
            # try next key
            key_index = (key_index + 1) % len(SERPER_KEYS)
            attempts += 1
            time.sleep(0.01)
    # if all keys busy, return the next one anyway (best-effort)
    k = SERPER_KEYS[key_index]
    key_last_used[k] = time.time()
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

# ----------------------------
# Utility functions
# ----------------------------
PHONE_RE = re.compile(r'(?:\+?2)?0?1[0125][0-9\-\s]{7,15}')

def extract_phones(text: str) -> List[str]:
    found = PHONE_RE.findall(text or "")
    cleaned = []
    for ph in found:
        ph2 = re.sub(r'[^\d]', '', ph)
        # Egyptian phone numbers expected length 11 without +2; basic filter
        if ph2.startswith("2") and len(ph2) == 12:
            ph2 = ph2[1:]  # remove leading country code if present as '2'
        if len(ph2) == 11:
            cleaned.append(ph2)
    return list(dict.fromkeys(cleaned))  # unique preserve order

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[A-Za-z]{2,}')

def extract_emails(text: str) -> List[str]:
    return list(dict.fromkeys(EMAIL_RE.findall(text or "")))

def detect_platform(link: Optional[str]) -> str:
    if not link: return "WEB"
    link = link.lower()
    if "facebook.com" in link or "fb." in link: return "FACEBOOK"
    if "olx" in link: return "OLX"
    if "tiktok.com" in link: return "TIKTOK"
    if "instagram.com" in link or "ig." in link: return "INSTAGRAM"
    if "youtube.com" in link or "youtu.be" in link: return "YOUTUBE"
    return "WEB"

def fetch_page_text(url: str, timeout=6) -> str:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "MassHunterBot/1.0"})
        return r.text or ""
    except:
        return ""

# ----------------------------
# Smart Query Generator (LLM)
# ----------------------------
def smart_query_generator(intent: str, city: str, n:int=12) -> List[str]:
    if not llm:
        # fallback simple variants
        variants = [
            f'site:facebook.com "{intent}" "{city}" "010"',
            f'site:olx.com.eg "{intent}" "{city}" "010"',
            f'"{intent}" "{city}" "010" OR "011"',
            f'"{intent}" "{city}" مطلوب',
            f'"{intent}" "{city}" للبيع',
        ]
        return variants[:n]
    try:
        prompt = f"""
أعطني {n} صيغ بحث (search queries) قصيرة ومتكيفة للبحث عن: "{intent}" داخل "{city}".
كل صيغة تكون على سطر جديد، تكون مناسبة للبحث عبر محركات بحث أو لتمريرها كـ q إلى Serper API.
لا تشرح، فقط القائمة.
"""
        res = llm.invoke(prompt).content
        lines = [l.strip() for l in res.splitlines() if l.strip()]
        # keep only up to n
        return lines[:n] if len(lines) >= 1 else []
    except Exception:
        return []

# ----------------------------
# LLM analyzer for snippet -> structured JSON
# ----------------------------
def ai_analyze_snippet(snippet: str) -> Dict:
    # returns dict: { intent, urgency, quality, reason }
    default = {"intent": "OTHER", "urgency": "LOW", "quality": "C", "reason": ""}
    if not llm or not snippet:
        return default
    try:
        prompt = f"""
حلل النص التالي وأعد JSON فقط (بدون كلام إضافي) يحتوي على الحقول:
- intent: (BUY / SELL / PRICE_INQUIRY / SCAM / OTHER)
- urgency: (HIGH / MEDIUM / LOW)
- quality: (A / B / C / F)
- reason: جملة قصيرة توضح لماذا اخترت هذا التصنيف

النص:
\"\"\"{snippet}\"\"\"
"""
        res = llm.invoke(prompt).content
        # try parse json; sometimes LLM returns text + json -> extract first { ... }
        start = res.find('{')
        end = res.rfind('}')
        if start != -1 and end != -1:
            j = json.loads(res[start:end+1])
            return {
                "intent": j.get("intent","OTHER"),
                "urgency": j.get("urgency","LOW"),
                "quality": j.get("quality","C"),
                "reason": j.get("reason","")
            }
    except Exception as e:
        # fallback
        return default
    return default

# ----------------------------
# DB Save + Smart Dedup
# ----------------------------
def upsert_lead_record(record: dict):
    """
    record keys: phone(optional), email(optional), intent_sentence, source_link, snippet, platform, ai_meta
    Dedup by phone if exists -> update notes & sources list. If no phone, dedup by email.
    """
    if not supabase:
        print("⚠️ Supabase not configured - skip save.")
        return

    phone = record.get("phone")
    email = record.get("email")
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    base = {
        "source": f"MassHunterV14: {record.get('intent_sentence')[:80]}",
        "status": "NEW",
        "notes": f"{now} | Snippet: {record.get('snippet')[:300]}",
        "quality": record.get("ai_meta", {}).get("quality", "C"),
        "intent_detected": record.get("ai_meta", {}).get("intent", "OTHER"),
        "urgency": record.get("ai_meta", {}).get("urgency", "LOW"),
        "platform": record.get("platform", "WEB"),
        "sources": [record.get("source_link")] if record.get("source_link") else []
    }
    if phone:
        base["phone_number"] = phone
        if email: base["email"] = email
        # try to find existing
        try:
            resp = supabase.table("leads").select("*").eq("phone_number", phone).execute()
            exists = resp.data and len(resp.data) > 0
            if exists:
                existing = resp.data[0]
                # merge
                new_notes = (existing.get("notes","") or "") + "\n" + base["notes"]
                new_sources = list(dict.fromkeys((existing.get("sources") or []) + base["sources"]))
                supabase.table("leads").update({
                    "notes": new_notes,
                    "quality": base["quality"],
                    "intent_detected": base["intent_detected"],
                    "urgency": base["urgency"],
                    "platform": base["platform"],
                    "sources": new_sources
                }).eq("phone_number", phone).execute()
                print(f"   ♻️ Updated existing phone {phone}")
                return
            else:
                supabase.table("leads").insert(base).execute()
                print(f"   ✅ Inserted new phone {phone}")
                return
        except Exception as e:
            print("DB Save Error (phone):", e)
            return

    if email and not phone:
        base["phone_number"] = f"email_{email}"
        base["email"] = email
        base["status"] = "EMAIL_ONLY"
        try:
            resp = supabase.table("leads").select("*").eq("phone_number", base["phone_number"]).execute()
            exists = resp.data and len(resp.data) > 0
            if exists:
                existing = resp.data[0]
                new_notes = (existing.get("notes","") or "") + "\n" + base["notes"]
                new_sources = list(dict.fromkeys((existing.get("sources") or []) + base["sources"]))
                supabase.table("leads").update({
                    "notes": new_notes,
                    "quality": base["quality"],
                    "intent_detected": base["intent_detected"],
                    "urgency": base["urgency"],
                    "platform": base["platform"],
                    "sources": new_sources
                }).eq("phone_number", base["phone_number"]).execute()
                print(f"   ♻️ Updated existing email lead {email}")
                return
            else:
                supabase.table("leads").insert(base).execute()
                print(f"   📧 Inserted new email lead {email}")
                return
        except Exception as e:
            print("DB Save Error (email):", e)
            return

    # fallback: nothing to save
    print("   ⚠️ No phone/email extracted - skipping DB insert.")

# ----------------------------
# Judge quick fallback (legacy)
# ----------------------------
def quick_judge(snippet: str) -> str:
    text = (snippet or "").lower()
    if any(x in text for x in ["مطلوب", "شراء", "كاش", "urgent", "اريد شراء"]):
        return "A"
    if any(x in text for x in ["سعر", "تفاصيل", "price"]):
        return "B"
    return "C"

# ----------------------------
# The main process (Hydra)
# ----------------------------
def get_sub_locations(city: str) -> List[str]:
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "وسط البلد"]
    if "الجيزة" in city:
        return ["المهندسين", "الدقي", "6 أكتوبر", "الشيخ زايد", "الهرم"]
    # Ask LLM for suggestions
    try:
        if not llm:
            return [city]
        prompt = f"أعطني قائمة بـ 5 أحياء حيوية داخل '{city}' مفصولة بفاصلة فقط."
        res = llm.invoke(prompt).content
        return [x.strip() for x in res.split(',') if x.strip()]
    except:
        return [city]

def run_hydra_process(intent: str, main_city: str):
    if not SERPER_KEYS:
        print("⚠️ No SERPER keys set - aborting hunt.")
        return
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Targeting Expanded: {sub_cities}")

    # generate smart queries
    queries = smart_query_generator(intent, main_city, n=16)
    if not queries:
        # fallback to a couple simple ones
        queries = [
            f'site:facebook.com "{intent}" "{main_city}" "010"',
            f'site:olx.com.eg "{intent}" "{main_city}" "010"',
            f'"{intent}" "{main_city}" "010" OR "011"'
        ]

    for area in sub_cities:
        print(f"--> Area: {area}")
        for q in queries:
            api_key = get_active_key()
            if not api_key:
                print("   ⚠️ No API key available.")
                continue

            payload = json.dumps({"q": q.replace("{city}", area) + f' "{area}"', "num": SERPER_NUM, "gl": SERPER_GL, "hl": SERPER_HL})
            headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
            try:
                resp = requests.post("https://google.serper.dev/search", headers=headers, data=payload, timeout=12)
                data = resp.json()
                results = data.get("organic", []) if isinstance(data, dict) else []
                print(f"   -> Found {len(results)} results for q='{q[:60]}...'")
                for res in results:
                    title = res.get('title','') or ''
                    snippet = (res.get('snippet','') or '') + " " + title
                    link = res.get('link') or res.get('displayed_link') or ""
                    platform = detect_platform(link)
                    # try to fetch page text to extract more phones/emails if link is available
                    page_text = ""
                    if link:
                        page_text = fetch_page_text(link)
                    combined_text = " ".join([snippet, page_text])

                    # extract contacts
                    phones = extract_phones(combined_text)
                    emails = extract_emails(combined_text)

                    # AI analyze snippet for better metadata
                    ai_meta = ai_analyze_snippet(snippet)
                    # fallback quality
                    ai_meta.setdefault("quality", quick_judge(snippet))

                    # Save all found contacts
                    if phones:
                        for ph in phones:
                            rec = {
                                "phone": ph,
                                "email": None,
                                "intent_sentence": intent,
                                "source_link": link,
                                "snippet": snippet,
                                "platform": platform,
                                "ai_meta": ai_meta
                            }
                            upsert_lead_record(rec)
                    if emails:
                        for em in emails:
                            rec = {
                                "phone": None,
                                "email": em,
                                "intent_sentence": intent,
                                "source_link": link,
                                "snippet": snippet,
                                "platform": platform,
                                "ai_meta": ai_meta
                            }
                            upsert_lead_record(rec)
                    # If no direct contact found but AI says high quality -> save as lead with note for manual follow-up
                    if not phones and not emails and ai_meta.get("quality") in ("A","B"):
                        rec = {
                            "phone": None,
                            "email": None,
                            "intent_sentence": intent,
                            "source_link": link,
                            "snippet": snippet,
                            "platform": platform,
                            "ai_meta": ai_meta
                        }
                        upsert_lead_record(rec)
            except Exception as e:
                print("   ⚠️ Search error:", e)
                continue
            # small sleep to avoid aggressive firing
            time.sleep(0.2)

    print("🏁 Mass Hunt V14 finished.")

# ----------------------------
# Endpoints
# ----------------------------
@app.get("/")
def home():
    return {"status": "Mass Hunter V14 Online"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    # no need to wait - starts in background
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city)
    return {"status": "Started", "intent": req.intent_sentence, "city": req.city}

@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest):
    # a simple endpoint: use LLM to analyze incoming free text (if available)
    snippet = req.message
    meta = ai_analyze_snippet(snippet)
    return {"action": "PROCEED", "intent": meta.get("intent"), "urgency": meta.get("urgency"), "quality": meta.get("quality")}

@app.post("/chat")
async def chat(req: ChatRequest):
    return {"response": "أهلاً — كيف أقدر أساعد؟"}
