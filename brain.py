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
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY")
SERPER_KEYS = [k.strip() for k in SERPER_KEYS_RAW.split(',') if k.strip()] if SERPER_KEYS_RAW else []

print(f"--- Hunter V13 (Mass Hunter) --- Keys: {len(SERPER_KEYS)}")

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

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- دوال المساعدة ---
key_index = 0
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    k = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

# --- 1. التقسيم الإجباري (عشان يغطي مساحة أكبر) ---
def get_sub_locations(city):
    # لو القاهرة، بنجبره يدور في الأحياء دي
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "وسط البلد"]
    if "الجيزة" in city:
        return ["المهندسين", "الدقي", "6 أكتوبر", "الشيخ زايد", "الهرم"]
    
    # لو مدينة تانية، نسأل الـ AI
    try:
        prompt = f"أعطني قائمة بـ 5 أحياء حيوية داخل '{city}' مفصولة بفاصلة فقط."
        res = llm.invoke(prompt).content
        return [x.strip() for x in res.split(',') if x.strip()]
    except: return [city]

def judge_lead(text):
    text = text.lower()
    if any(x in text for x in ["مطلوب", "شراء", "كاش", "buy", "urgent"]): return "Excellent 🔥"
    if any(x in text for x in ["سعر", "تفاصيل", "price"]): return "Very Good ⭐"
    return "Good ✅"

def save_lead(phone, email, keyword, link, quality):
    data = {"source": f"MassHunt: {keyword}", "status": "NEW", "notes": f"Link: {link}", "quality": quality}
    
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED PHONE: {phone}")
        except: pass
    elif email:
        data["phone_number"] = f"email_{email}"
        data["email"] = email
        data["status"] = "EMAIL_ONLY"
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 SAVED EMAIL: {email}")
        except: pass

# --- المحرك الرئيسي (Mass Hunter) ---
def run_hydra_process(intent: str, main_city: str):
    if not supabase or not SERPER_KEYS: return
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Targeting Expanded: {sub_cities}")
    
    for area in sub_cities:
        # معادلات البحث
        queries = [
            f'site:facebook.com "{intent}" "{area}" "010"',
            f'site:olx.com.eg "{intent}" "{area}" "010"',
            f'"{intent}" "{area}" "010" OR "011"'
        ]
        
        for q in queries:
            api_key = get_active_key()
            if not api_key: break
            
            # التغيير هنا: بنجيب 50 نتيجة في الضربة الواحدة
            payload = json.dumps({"q": q, "num": 50, "gl": "eg", "hl": "ar"})
            headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
            
            try:
                response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                results = response.json().get("organic", [])
                
                print(f"   -> Found {len(results)} results for {area}...")

                for res in results:
                    snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                    quality = judge_lead(snippet)
                    
                    phones = re.findall(r'(01[0125][0-9 \-]{8,15})', snippet)
                    for raw in phones:
                        clean = raw.replace(" ", "").replace("-", "")
                        if len(clean) == 11:
                            save_lead(clean, None, intent, res.get('link'), quality)

                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                    for mail in emails:
                        save_lead(None, mail, intent, res.get('link'), quality)
                        
            except Exception as e:
                print(f"   ⚠️ Error: {e}")

    print(f"🏁 Mass Hunt Finished.")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V13 Online"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city)
    return {"status": "Started"}

@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest): return {"action": "PROCEED", "intent": "INTERESTED"}

@app.post("/chat")
async def chat(req: ChatRequest): return {"response": "أهلاً"}
