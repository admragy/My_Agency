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

# الإعدادات والمفاتيح
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
# مفاتيح Serper المتعددة (لضمان عدم التوقف)
SERPER_KEYS_RAW = os.environ.get("SERPER_KEYS", "") 
SERPER_KEYS = [k.strip() for k in SERPER_KEYS_RAW.split(',') if k.strip()]

print(f"--- Hunter V12 (The Judge) --- Active Keys: {len(SERPER_KEYS)}")

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

# --- 1. أدوات المساعدة (المناطق والمفاتيح) ---
def get_sub_locations(city):
    try:
        prompt = f"أعطني قائمة بـ 5 أحياء حيوية داخل '{city}' مفصولة بفاصلة فقط."
        res = llm.invoke(prompt).content
        return [x.strip() for x in res.split(',') if x.strip()]
    except: return [city]

key_index = 0
def get_active_key():
    global key_index
    if not SERPER_KEYS: return None
    k = SERPER_KEYS[key_index]
    key_index = (key_index + 1) % len(SERPER_KEYS)
    return k

# --- 2. القاضي (Quality Scorer) ⚖️ ---
def judge_lead(text):
    text = text.lower()
    score = 0
    # كلمات تدل على الجودة
    if any(x in text for x in ["مطلوب", "شراء", "كاش", "buy", "urgent"]): score += 5
    if any(x in text for x in ["سعر", "تفاصيل", "price", "details"]): score += 2
    # كلمات سلبية (منافسين)
    if any(x in text for x in ["للبيع", "sale", "offer", "متوفر"]): return "Competitor"
        
    if score >= 5: return "Excellent 🔥"
    if score >= 2: return "Very Good ⭐"
    return "Good ✅"

# --- 3. دالة الحفظ (رقم أو إيميل فقط) ---
def save_lead(phone, email, keyword, link, quality):
    data = {
        "source": f"Hydra: {keyword}",
        "status": "NEW",
        "notes": f"Link: {link}",
        "quality": quality
    }
    
    # الأولوية للرقم
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED PHONE ({quality}): {phone}")
        except: pass
    
    # لو مفيش رقم، ناخد الإيميل
    elif email:
        data["phone_number"] = f"email_{email}"
        data["email"] = email
        data["status"] = "EMAIL_ONLY"
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 SAVED EMAIL ({quality}): {email}")
        except: pass

# --- 4. المحرك الرئيسي ---
def run_hydra_process(intent: str, main_city: str):
    if not supabase or not SERPER_KEYS: return
    
    sub_cities = get_sub_locations(main_city)
    print(f"🌍 Targeting: {sub_cities}")
    
    for area in sub_cities:
        # معادلات البحث
        queries = [
            f'site:facebook.com "{intent}" "{area}" "010"',
            f'site:olx.com.eg "{intent}" "{area}" "010"',
            f'"{intent}" "{area}" "@gmail.com"'
        ]
        
        for q in queries:
            api_key = get_active_key()
            if not api_key: break
            
            payload = json.dumps({"q": q, "num": 20, "gl": "eg", "hl": "ar"})
            headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
            
            try:
                response = requests.post("https://google.serper.dev/search", headers=headers, data=payload)
                results = response.json().get("organic", [])
                
                for res in results:
                    snippet = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                    
                    # تقييم الجودة
                    quality = judge_lead(snippet)
                    if quality == "Competitor": continue # تجاهل المنافسين

                    # استخراج الأرقام
                    phones = re.findall(r'(01[0125][0-9 \-]{8,15})', snippet)
                    for raw in phones:
                        clean = raw.replace(" ", "").replace("-", "")
                        if len(clean) == 11:
                            save_lead(clean, None, intent, res.get('link'), quality)

                    # استخراج الإيميلات
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                    for mail in emails:
                        save_lead(None, mail, intent, res.get('link'), quality)
                            
            except Exception as e:
                print(f"   ⚠️ Search Error: {e}")

    print(f"🏁 Mission Complete.")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain Online"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hydra_process, req.intent_sentence, req.city)
    return {"status": "Started"}

# ... (Analyze & Chat كما هما، لا تغيير)
@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest):
    if not supabase: return {"action": "STOP"}
    # كود تحليل بسيط
    return {"action": "PROCEED", "intent": "INTERESTED"}

@app.post("/chat")
async def chat(req: ChatRequest):
    camp = supabase.table("campaigns").select("*").eq("is_active", True).limit(1).execute()
    info = camp.data[0]['product_description'] if camp.data else "عام"
    res = llm.invoke(f"بائع مصري. المنتج: {info}. العميل: {req.message}. رد باختصار:").content
    supabase.table("interactions").insert({"phone_number": req.phone_number, "user_query": req.message, "ai_response": res}).execute()
    return {"response": res}
