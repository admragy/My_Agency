import os
import json
import re
import requests
import time
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from langchain_groq import ChatGroq

# الإعدادات
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# تنظيف المفاتيح
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY") or ""
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Hunter V17 (Deep Digger) --- Active Keys: {len(SERPER_KEYS)}")

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

def get_sub_locations(city):
    # تقسيم إجباري للمدن الكبرى لضمان الكثافة
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "حدائق الاهرام", "المقطم", "شبرا"]
    if "الجيزة" in city:
        return ["المهندسين", "الدقي", "6 أكتوبر", "الشيخ زايد", "الهرم", "فيصل"]
    if "الإسكندرية" in city:
        return ["سموحة", "ميامي", "المنتزه", "سيدي جابر", "العجمي"]
    return [city]

def save_lead(phone, email, keyword, link, quality):
    data = {"source": f"DeepHunt: {keyword}", "status": "NEW", "notes": f"Link: {link}", "quality": quality}
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED: {phone}")
            return True
        except: pass
    elif email:
        data["phone_number"] = f"email_{email}"
        data["email"] = email
        data["status"] = "EMAIL_ONLY"
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 SAVED EMAIL: {email}")
            return True
        except: pass
    return False

# --- المحرك الرئيسي (الحفر العميق) ---
def run_hydra_process(intent: str, main_city: str):
    if not SERPER_KEYS: 
        print("❌ NO KEYS FOUND!")
        return
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Targeting Deeply: {sub_cities}")
    
    total_found = 0

    for area in sub_cities:
        # معادلات بحث مخصصة للمهن والخدمات والعقارات
        queries = [
            f'site:facebook.com {intent} {area} 010',
            f'site:olx.com.eg {intent} {area} 010',
            f'"{intent}" {area} "رقم الهاتف" 010', # صيغة قوية للمهن
            f'"{intent}" {area} "تواصل معنا" 010',
            f'{intent} {area} 010 -site:youtube.com'
        ]
        
        for q in queries:
            # التكرار للتقليب في الصفحات (Pagination)
            # هنلف 4 مرات (0, 10, 20, 30) يعني هنجيب أول 4 صفحات نتائج
            for start_page in range(0, 40, 10):
                
                api_key = get_active_key()
                if not api_key: break
                
                # طلب 20 نتيجة في الصفحة الواحدة
                payload = json.dumps({
                    "q": q,
                    "start": start_page, 
                    "num": 20,
                    "gl": "eg", 
                    "hl": "ar"
                })
                
                headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
                
                try:
                    print(f"🚀 Digging Page {int(start_page/10)+1} for: {q} ...")
                    response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                    data = response.json()
                    
                    results = data.get("organic", [])
                    if not results: 
                        print("   ⚠️ End of results for this query.")
                        break # لو الصفحة فاضية، وقف تدوير في الكلمة دي وخش عالي بعدها

                    for res in results:
                        snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                        
                        # تقييم الجودة
                        quality = "Good ✅"
                        if any(x in snippet for x in ["مطلوب", "شراء", "كاش", "buy"]): quality = "Excellent 🔥"
                        if any(x in snippet for x in ["صيانة", "تصليح", "تركيب", "فني"]): quality = "Service PRO 🛠️" # للمهن

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
                    
                    # استراحة محارب عشان السيرفر ميهنجش
                    # time.sleep(0.5) 
                        
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")

    print(f"🏁 Deep Hunt Finished. Total Saved: {total_found}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V17 Deep Digger"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city)
    return {"status": "Started"}

@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest): return {"action": "PROCEED", "intent": "INTERESTED"}

@app.post("/chat")
async def chat(req: ChatRequest):
    camp = supabase.table("campaigns").select("*").eq("is_active", True).limit(1).execute()
    info = camp.data[0]['product_description'] if camp.data else "عام"
    res = llm.invoke(f"بائع مصري. المنتج: {info}. العميل: {req.message}. رد باختصار:").content
    supabase.table("interactions").insert({"phone_number": req.phone_number, "user_query": req.message, "ai_response": res}).execute()
    return {"response": res}
