import os
import json
import re
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from langchain_groq import ChatGroq

# الإعدادات
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY") or ""
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Brain V23 (Hydra + Sniper) --- Active Keys: {len(SERPER_KEYS)}")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
    print("✅ System Connected!")
except:
    supabase = None
    llm = None

app = FastAPI()

class HuntRequest(BaseModel):
    intent_sentence: str
    city: str
    time_filter: str = "qdr:m"
    user_id: str = "admin"
    mode: str = "general" # general OR sniper

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- الأدوات ---
key_index = 0
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    k = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

def get_sub_locations(city):
    if city in ["مصر", "egypt", "الجمهورية"]:
        return ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "الشرقية", "الغربية", "المنوفية"]
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "وسط البلد"]
    if "," in city:
        return [c.strip() for c in city.split(",")]
    return [city]

def save_lead(phone, email, keyword, link, quality, user_id, source_type):
    data = {
        "source": f"{source_type}: {keyword}",
        "status": "NEW",
        "notes": f"Link: {link}",
        "quality": quality,
        "user_id": user_id
    }
    saved = False
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED PHONE: {phone}")
            saved = True
        except: pass
    elif email:
        data["phone_number"] = f"email_{email}"
        data["email"] = email
        data["status"] = "EMAIL_ONLY"
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 SAVED EMAIL: {email}")
            saved = True
        except: pass
    return saved

def judge_lead(text):
    text = text.lower()
    if any(x in text for x in ["مطلوب", "شراء", "كاش", "buy", "urgent"]): return "Excellent 🔥"
    if any(x in text for x in ["سعر", "تفاصيل", "price"]): return "Very Good ⭐"
    return "Good ✅"

# --- المحرك الرئيسي ---
def run_hydra_process(intent: str, main_city: str, time_filter: str, user_id: str, mode: str):
    if not SERPER_KEYS: return
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Hunting ({mode}) for {user_id} in {sub_cities}")
    
    for area in sub_cities:
        queries = []
        
        # استراتيجية القناص (Sniper Mode)
        if mode == "sniper":
            # البحث عن اسم المنافس + رقم تليفون
            queries = [
                f'site:facebook.com "{intent}" "{area}" "010"',
                f'site:instagram.com "{intent}" "{area}" "010"',
                f'"{intent}" "{area}" "010"'
            ]
        # استراتيجية الصيد العام (General Mode)
        else:
            queries = [
                f'site:facebook.com {intent} {area} 010',
                f'site:olx.com.eg {intent} {area} 010',
                f'{intent} {area} 010'
            ]
        
        for q in queries:
            for start_page in range(0, 40, 10):
                api_key = get_active_key()
                if not api_key: break
                
                payload = json.dumps({"q": q, "start": start_page, "num": 20, "tbs": time_filter})
                headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
                
                try:
                    response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                    results = response.json().get("organic", [])
                    if not results: break

                    for res in results:
                        snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                        quality = judge_lead(snippet)
                        
                        # في وضع القناص، كل النتائج تعتبر ممتازة
                        if mode == "sniper": quality = "Target 🎯"

                        phones = re.findall(r'(01[0125][0-9 \-]{8,15})', snippet)
                        for raw in phones:
                            clean = raw.replace(" ", "").replace("-", "")
                            if len(clean) == 11:
                                save_lead(clean, None, intent, res.get('link'), quality, user_id, "Sniper" if mode=="sniper" else "Hunter")

                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                        for mail in emails:
                            save_lead(None, mail, intent, res.get('link'), quality, user_id, "Sniper" if mode=="sniper" else "Hunter")
                except: pass

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V23 Online"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city, req.time_filter, req.user_id, req.mode)
    return {"status": "Started"}

@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest): return {"action": "PROCEED", "intent": "INTERESTED"}

@app.post("/chat")
async def chat(req: ChatRequest):
    return {"response": "اهلا"}
