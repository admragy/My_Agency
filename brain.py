import os
import json
import re
import requests
import time
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from langchain_groq import ChatGroq

# --- الإعدادات ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY") or ""
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Brain V25 (The Vacuum 🧹) --- Active Keys: {len(SERPER_KEYS)}")

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
    mode: str = "general"

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- إدارة المفاتيح ---
key_index = 0
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    k = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

# --- تقسيم المناطق (لزيادة الكثافة) ---
def get_sub_locations(city):
    if city in ["مصر", "egypt"]:
        return ["القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "الشرقية"]
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "الهرم", "شبرا"]
    if "," in city:
        return [c.strip() for c in city.split(",")]
    return [city]

# --- الحفظ (بدون شروط معقدة) ---
def save_lead(phone, email, keyword, link, user_id, source_type):
    # تقييم مبدئي بسيط جداً
    quality = "Good ✅" 
    
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
            print(f"   ✅ STORED: {phone}")
            saved = True
        except: pass
    elif email:
        data["phone_number"] = f"email_{email}"
        data["email"] = email
        data["status"] = "EMAIL_ONLY"
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 STORED EMAIL: {email}")
            saved = True
        except: pass
    return saved

# --- المحرك الرئيسي (الشفاط) ---
def run_hydra_process(intent: str, main_city: str, time_filter: str, user_id: str, mode: str):
    if not SERPER_KEYS: 
        print("❌ NO KEYS")
        return
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Vacuuming in: {sub_cities}")
    
    total_found = 0

    for area in sub_cities:
        # معادلات بحث واسعة جداً (OR) عشان تلم كله
        queries = [
            f'site:facebook.com "{intent}" "{area}" "010"',
            f'site:olx.com.eg "{intent}" "{area}" "010"',
            f'"{intent}" "{area}" "010" -site:youtube.com'
        ]
        
        for q in queries:
            api_key = get_active_key()
            if not api_key: break
            
            # التغيير الجذري: طلبنا 100 نتيجة في الصفحة الواحدة
            # وهنجرب صفحتين (يعني 200 نتيجة لكل منطقة)
            for start_index in [0, 100]: 
                
                payload = json.dumps({
                    "q": q,
                    "num": 100, # هات أقصى عدد ممكن
                    "start": start_index,
                    "tbs": time_filter
                })
                
                headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
                
                try:
                    print(f"🚀 Scanning ({area}): {q} | Offset: {start_index}")
                    response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                    results = response.json().get("organic", [])
                    
                    if not results: 
                        print("   ⚠️ Empty page, checking next...")
                        continue # كمل متقفش

                    print(f"   -> Found {len(results)} raw results.")

                    for res in results:
                        # دمج العنوان والوصف
                        blob = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                        
                        # استخراج أي رقم مصري يقابلنا
                        phones = re.findall(r'(01[0125][0-9 \-]{8,15})', blob)
                        
                        for raw in phones:
                            clean = raw.replace(" ", "").replace("-", "")
                            if len(clean) == 11:
                                if save_lead(clean, None, intent, res.get('link'), user_id, "Hunter"):
                                    total_found += 1

                        # استخراج إيميلات
                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', blob)
                        for mail in emails:
                            save_lead(None, mail, intent, res.get('link'), user_id, "Hunter")
                            
                except Exception as e:
                    print(f"   ⚠️ Err: {e}")
                    time.sleep(1)

    print(f"🏁 VACUUM FINISHED. Total Stored: {total_found}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V25 Vacuum"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city, req.time_filter, req.user_id, req.mode)
    return {"status": "Started"}

@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest): return {"action": "PROCEED", "intent": "INTERESTED"}

@app.post("/chat")
async def chat(req: ChatRequest):
    return {"response": "اهلا"}
