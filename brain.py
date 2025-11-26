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
# تنظيف المفاتيح من أي مسافات أو علامات تنصيص خفية (ده كان سبب مشاكل كتير)
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY") or ""
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Hunter V16 (Mass Hunter Fixed) --- Active Keys: {len(SERPER_KEYS)}")

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

# تقسيم المناطق (لو فشل الـ AI، بنستخدم مناطق افتراضية للقاهرة)
def get_sub_locations(city):
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "وسط البلد"]
    try:
        # محاولة استخدام الـ AI للتقسيم
        return [city] 
    except: return [city]

def save_lead(phone, email, keyword, link, quality):
    data = {"source": f"Hunter V16: {keyword}", "status": "NEW", "notes": f"Link: {link}", "quality": quality}
    
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

# --- المحرك الرئيسي ---
def run_hydra_process(intent: str, main_city: str):
    if not SERPER_KEYS: 
        print("❌ NO KEYS FOUND!")
        return
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Targeting: {sub_cities}")
    
    total_found = 0

    for area in sub_cities:
        # معادلات بحث مبسطة عشان نضمن نتايج
        queries = [
            f'site:facebook.com {intent} {area} 010',
            f'site:olx.com.eg {intent} {area} 010',
            f'{intent} {area} 010 -site:youtube.com'
        ]
        
        for q in queries:
            api_key = get_active_key()
            
            # التغيير هنا: شيلنا قيود اللغة والموقع الصارمة عشان نجيب نتايج أكتر
            payload = json.dumps({"q": q, "num": 20}) 
            headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
            
            try:
                print(f"🚀 Searching: {q} ...")
                response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                data = response.json()
                
                # طباعة رسالة الخطأ لو المفتاح بايظ
                if "message" in data:
                    print(f"⚠️ API Error: {data['message']}")

                results = data.get("organic", [])
                print(f"   -> Found {len(results)} results.")

                for res in results:
                    snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                    
                    # تقييم بسيط
                    quality = "Good ✅"
                    if "مطلوب" in snippet or "شراء" in snippet: quality = "Excellent 🔥"

                    # استخراج
                    phones = re.findall(r'(01[0125][0-9 \-]{8,15})', snippet)
                    for raw in phones:
                        clean = raw.replace(" ", "").replace("-", "")
                        if len(clean) == 11:
                            if save_lead(clean, None, intent, res.get('link'), quality):
                                total_found += 1

                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                    for mail in emails:
                        save_lead(None, mail, intent, res.get('link'), quality)
                        
            except Exception as e:
                print(f"   ⚠️ Error: {e}")

    print(f"🏁 Mission Finished. Total Saved: {total_found}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V16 Online"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city)
    return {"status": "Started"}

# ... (باقي الكود analyze و chat زي ما هو)
@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest): return {"action": "PROCEED", "intent": "INTERESTED"}

@app.post("/chat")
async def chat(req: ChatRequest):
    camp = supabase.table("campaigns").select("*").eq("is_active", True).limit(1).execute()
    info = camp.data[0]['product_description'] if camp.data else "عام"
    res = llm.invoke(f"بائع مصري. المنتج: {info}. العميل: {req.message}. رد باختصار:").content
    supabase.table("interactions").insert({"phone_number": req.phone_number, "user_query": req.message, "ai_response": res}).execute()
    return {"response": res}
