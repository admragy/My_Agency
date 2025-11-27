import os
import json
import re
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from langchain_groq import ChatGroq

# --- الإعدادات والمفاتيح ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# تنظيف مفاتيح Serper من أي شوائب
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY") or ""
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Hunter V19 (Map Master) --- Active Keys: {len(SERPER_KEYS)}")

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
    time_filter: str = "qdr:m" # الافتراضي آخر شهر

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- 1. إدارة مفاتيح البحث (Rotation) ---
key_index = 0
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    k = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

# --- 2. خريطة مصر الذكية (Smart Geo-Splitter) ---
def get_sub_locations(city):
    city = city.lower().strip()
    
    # أ: لو العميل طلب "مصر كلها"
    if city in ["مصر", "egypt", "الجمهورية", "جميع المحافظات", "كل مصر"]:
        return [
            "القاهرة", "الجيزة", "الإسكندرية", "الدقهلية", "الشرقية", 
            "المنوفية", "الغربية", "البحيرة", "كفر الشيخ", "دمياط", 
            "بورسعيد", "الإسماعيلية", "السويس", "المنيا", "أسيوط", 
            "سوهاج", "قنا", "الأقصر", "أسوان", "بني سويف"
        ]

    # ب: لو العميل كتب مدن متعددة (القاهرة, طنطا)
    if "," in city or "،" in city:
        clean_city = city.replace("،", ",")
        return [c.strip() for c in clean_city.split(",") if c.strip()]

    # ج: تقسيم المدن الكبرى لزيادة الكثافة
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "وسط البلد", "شبرا", "حدائق القبة", "المقطم"]
    if "الجيزة" in city:
        return ["المهندسين", "الدقي", "6 أكتوبر", "الشيخ زايد", "الهرم", "فيصل", "إمbaba"]
    if "الإسكندرية" in city:
        return ["سموحة", "ميامي", "المنتزه", "سيدي جابر", "العجمي", "محطة الرمل"]
        
    # د: لو مدينة عادية (زي طنطا أو المنصورة) رجعها زي ما هي
    return [city]

# --- 3. تقييم الجودة (The Judge) ---
def judge_lead(text):
    text = text.lower()
    # كلمات القوة
    if any(x in text for x in ["مطلوب", "شراء", "كاش", "buy", "urgent", "محتاج", "عايز"]): return "Excellent 🔥"
    if any(x in text for x in ["سعر", "تفاصيل", "price", "details", "بكام"]): return "Very Good ⭐"
    # كلمات المنافسين
    if any(x in text for x in ["للبيع", "sale", "offer", "متاح"]): return "Competitor ❌"
    return "Good ✅"

# --- 4. الحفظ في الخزنة ---
def save_lead(phone, email, keyword, link, quality):
    data = {"source": f"Hunter: {keyword}", "status": "NEW", "notes": f"Link: {link}", "quality": quality}
    
    saved = False
    # أولوية للموبايل
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED PHONE: {phone}")
            saved = True
        except: pass
    # ثم الإيميل
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

# --- 5. المحرك الرئيسي (The Core) ---
def run_hydra_process(intent: str, main_city: str, time_filter: str):
    if not SERPER_KEYS: 
        print("❌ CRITICAL: NO KEYS FOUND!")
        return
    
    # تقسيم المنطقة
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Targeting Map: {sub_cities}")
    
    total_found = 0

    for area in sub_cities:
        # معادلات البحث (تشمل فيسبوك، أوليكس، والبحث العام)
        queries = [
            f'site:facebook.com {intent} {area} 010',
            f'site:olx.com.eg {intent} {area} 010',
            f'"{intent}" {area} "010" -site:youtube.com'
        ]
        
        for q in queries:
            # الحفر العميق (أول 4 صفحات)
            for start_page in range(0, 40, 10):
                api_key = get_active_key()
                if not api_key: break
                
                # إعداد الطلب (بدون قيود صارمة عشان نجيب نتايج)
                payload = json.dumps({
                    "q": q, "start": start_page, "num": 20, "tbs": time_filter
                })
                headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
                
                try:
                    print(f"🚀 Scanning: {q} (Page {int(start_page/10)+1})")
                    response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                    results = response.json().get("organic", [])
                    
                    if not results: break # الصفحة فاضية، اقلب

                    for res in results:
                        snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                        quality = judge_lead(snippet)
                        
                        if quality == "Competitor ❌": continue 

                        # استخراج الأرقام (أي صيغة)
                        phones = re.findall(r'(01[0125][0-9 \-]{8,15})', snippet)
                        for raw in phones:
                            clean = raw.replace(" ", "").replace("-", "")
                            if len(clean) == 11:
                                if save_lead(clean, None, intent, res.get('link'), quality):
                                    total_found += 1

                        # استخراج الإيميلات
                        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                        for mail in emails:
                            save_lead(None, mail, intent, res.get('link'), quality)
                                
                except Exception as e:
                    print(f"   ⚠️ Error: {e}")

    print(f"🏁 Empire Hunt Finished. Total Saved: {total_found}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V19 Map Master"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city, req.time_filter)
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

