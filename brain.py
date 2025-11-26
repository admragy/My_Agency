import os
import json
import re
import requests
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- الإعدادات والمفاتيح ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS") or os.environ.get("SERPER_API_KEY") or ""
SERPER_KEYS = [k.strip().replace('"', '') for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Ultimate Hunter V18 (Reverse + Deep + Time) --- Keys: {len(SERPER_KEYS)}")

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

# --- 1. إدارة المفاتيح ---
key_index = 0
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    k = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

# --- 2. تقسيم المناطق (تفتيت المدينة) ---
def get_sub_locations(city):
    if "القاهرة" in city:
        return ["المعادي", "التجمع الخامس", "مدينة نصر", "مصر الجديدة", "الزمالك", "وسط البلد", "حدائق القبة", "شبرا"]
    if "الجيزة" in city:
        return ["المهندسين", "الدقي", "6 أكتوبر", "الشيخ زايد", "الهرم", "فيصل"]
    if "الإسكندرية" in city:
        return ["سموحة", "ميامي", "المنتزه", "سيدي جابر", "العجمي"]
    try:
        # محاولة ذكية لباقي المدن
        return [city, f"مركز {city}", f"قرى {city}"]
    except: return [city]

# --- 3. العاكس الذكي (Reverse Engineer) ---
def reverse_engineer_intent(user_sentence):
    print(f"🧠 Analyzing: {user_sentence}")
    # لو المستخدم كاتب "مطلوب" أصلاً، مش محتاجين نعكس
    if "مطلوب" in user_sentence or "أبحث" in user_sentence:
        return [user_sentence]
        
    prompt = f"""
    المستخدم يقول: "{user_sentence}".
    حول هذه الجملة إلى ما يكتبه "الزبون" الذي يبحث عن هذه الخدمة.
    أعطني 3 جمل بحثية بصيغة "مطلوب" أو "أبحث عن" أو وصف مشكلة.
    الرد قائمة مفصولة بفاصلة فقط.
    """
    try:
        res = llm.invoke(prompt).content
        keywords = [k.strip() for k in res.split(',') if k.strip()]
        print(f"💡 Converted to: {keywords}")
        return keywords
    except: return [user_sentence]

# --- 4. تقييم الجودة ---
def judge_lead(text):
    text = text.lower()
    if any(x in text for x in ["مطلوب", "شراء", "كاش", "buy", "urgent", "محتاج"]): return "Excellent 🔥"
    if any(x in text for x in ["سعر", "تفاصيل", "price", "details", "بكام"]): return "Very Good ⭐"
    if any(x in text for x in ["للبيع", "sale", "offer"]): return "Competitor ❌"
    return "Good ✅"

# --- 5. الحفظ في الذاكرة ---
def save_lead(phone, email, keyword, link, quality):
    data = {"source": f"V18: {keyword}", "status": "NEW", "notes": f"Link: {link}", "quality": quality}
    
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED: {phone} ({quality})")
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

# --- 6. المحرك الرئيسي (The Core) ---
def run_hydra_process(raw_intent: str, main_city: str, time_filter: str):
    if not SERPER_KEYS: 
        print("❌ NO KEYS!")
        return
    
    # أ: عكس النية (فهم لغة الزبون)
    target_keywords = reverse_engineer_intent(raw_intent)
    
    # ب: تقسيم المدينة
    sub_cities = get_sub_locations(main_city)
    
    print(f"🌍 Full Scope: {len(target_keywords)} keywords x {len(sub_cities)} areas")
    
    total_found = 0

    for area in sub_cities:
        for intent in target_keywords:
            # ج: مصادر البحث المتعددة
            queries = [
                f'site:facebook.com "{intent}" "{area}" "010"',
                f'site:olx.com.eg "{intent}" "{area}" "010"',
                f'"{intent}" "{area}" "010" -site:youtube.com'
            ]
            
            for q in queries:
                # د: الحفر العميق (Pagination - 3 صفحات)
                for start_page in range(0, 30, 10):
                    api_key = get_active_key()
                    if not api_key: break
                    
                    # هـ: الفلتر الزمني (tbs)
                    payload = json.dumps({
                        "q": q, "start": start_page, "num": 20, "tbs": time_filter
                    })
                    headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
                    
                    try:
                        response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                        results = response.json().get("organic", [])
                        
                        if not results: break 

                        for res in results:
                            snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                            quality = judge_lead(snippet)
                            
                            if quality == "Competitor ❌": continue # تجاهل المنافسين

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
                        print(f"   ⚠️ Err: {e}")

    print(f"🏁 Finished. Total: {total_found}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain V18 Ultimate"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    # تمرير كل الباراميترز (الجملة، المدينة، الزمن)
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
