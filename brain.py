import os
import json
import re
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from duckduckgo_search import DDGS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

print("--- Start Up Logs ---")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
    print("✅ System Connected!")
except Exception as e:
    print(f"❌ Connection Error: {e}")
    supabase = None
    llm = None

app = FastAPI()

class HuntRequest(BaseModel):
    keyword: str
    city: str

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- الصياد المطور (شبكة واسعة) ---
def run_hunter_process(keyword: str, city: str):
    print(f"🕵️‍♂️ [HUNTER] Searching for: {keyword} in {city}")
    
    if not supabase:
        print("❌ DB Not connected")
        return

    # استراتيجية البحث: بنستخدم backend='html' عشان نجيب نتايج أكتر
    query = f'{keyword} {city} "010" OR "011" OR "012" OR "015"'
    
    try:
        # بنجيب 30 نتيجة بدل 20
        results = DDGS().text(query, max_results=30, backend='html') 
        count = 0
        
        if not results:
            print("⚠️ الصياد رجع وايده فاضية (مفيش نتايج من جوجل). جرب كلمات تانية.")
            return

        print(f"🔎 وجدنا {len(results)} نتيجة بحث.. جاري فحص الأرقام...")

        for res in results:
            # دمج العنوان والوصف
            text_blob = str(res.get('body', '')) + " " + str(res.get('title', ''))
            
            # شبكة صيد ذكية (بتقفش الأرقام حتى لو فيها مسافات أو شرط)
            # بياخد أي رقم يبدأ بـ 01 وبعده 9 أرقام (سواء لازقين أو بينهم مسافة)
            raw_phones = re.findall(r'(01[0125][0-9 \-]{8,15})', text_blob)
            
            for raw_phone in raw_phones:
                # تنظيف الرقم (شيل المسافات والشرط عشان يتسجل صح)
                clean_phone = raw_phone.replace(" ", "").replace("-", "")
                
                # التأكد إن طول الرقم 11 (رقم مصري صحيح)
                if len(clean_phone) == 11:
                    try:
                        data = {
                            "phone_number": clean_phone,
                            "source": f"Hunter: {keyword}",
                            "status": "NEW",
                            "notes": f"Source: {res.get('href', 'Search')}"
                        }
                        # Upsert عشان لو الرقم موجود قبل كده ميعملش خطأ
                        supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
                        print(f"✅ تم صيد العميل: {clean_phone}")
                        count += 1
                    except Exception as db_err:
                        print(f"⚠️ خطأ داتابيس: {db_err}")
                        pass
                    
        print(f"🏁 انتهت المهمة. الحصيلة النهائية: {count} عميل.")
        
    except Exception as e:
        print(f"❌ Hunter Crash: {e}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain Online v2 🧠"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    print(f"📩 Order Received: {req.keyword}")
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Hunter Deployed"}

@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest):
    if not supabase: return {"action": "STOP", "reply": "DB Error"}
    settings = supabase.table("project_settings").select("*").limit(1).execute()
    allowed = settings.data[0]['allowed_cities'] if settings.data else "القاهرة"
    
    prompt = f"""حلل: "{req.message}". المسموح: {allowed}. JSON: {{"loc": "INSIDE/OUTSIDE", "intent": "INTERESTED/NOT"}}"""
    try:
        chain = ChatPromptTemplate.from_template(prompt) | llm | StrOutputParser()
        res_txt = chain.invoke({}).replace("```json", "").replace("```", "").strip()
        if "{" in res_txt: res_txt = res_txt[res_txt.find("{"):res_txt.rfind("}")+1]
        res = json.loads(res_txt)
    except: res = {"loc": "UNKNOWN", "intent": "INTERESTED"}

    if res.get('loc') == 'OUTSIDE': return {"action": "STOP", "reply": "خارج النطاق"}
    if res.get('intent') == 'NOT_INTERESTED': return {"action": "STOP", "reply": "شكراً"}
    return {"action": "PROCEED", "intent": res.get('intent')}

@app.post("/chat")
async def chat(req: ChatRequest):
    camp = supabase.table("campaigns").select("*").eq("is_active", True).limit(1).execute()
    info = camp.data[0]['product_description'] if camp.data else "لا توجد حملة"
    res = llm.invoke(f"بائع مصري. المنتج: {info}. العميل: {req.message}. رد باختصار:").content
    supabase.table("interactions").insert({"phone_number": req.phone_number, "user_query": req.message, "ai_response": res}).execute()
    return {"response": res}
