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

print("--- System Starting v3 (Wide Net) ---")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
    print("✅ All Systems Connected!")
except Exception as e:
    print(f"❌ Init Error: {e}")
    supabase = None
    llm = None

app = FastAPI()

class HuntRequest(BaseModel):
    keyword: str
    city: str

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- صياد بوضع "الشبكة العملاقة" ---
def run_hunter_process(keyword: str, city: str):
    print(f"🕵️‍♂️ [START] Hunting for: {keyword} in {city}")
    
    if not supabase: return

    # قائمة أماكن البحث (استراتيجيات متنوعة)
    queries = [
        # 1. تيليجرام (كنز الجروبات)
        f'site:t.me "{keyword}" "{city}" "010"',
        
        # 2. أوليكس والسوق المفتوح (للتجار والعقارات)
        f'site:olx.com.eg "{keyword}" "010"',
        f'site:opensooq.com "{keyword}" "010"',
        
        # 3. فيسبوك وإنستجرام (الأساسي)
        f'site:facebook.com "{keyword}" "{city}" "010"',
        
        # 4. بحث عام (أي منتدى أو موقع)
        f'"{keyword}" "{city}" "010" OR "011" OR "012" -site:facebook.com' 
    ]
    
    total_found = 0
    
    for q in queries:
        print(f"🔎 Casting Net: {q}")
        try:
            # بنجيب 20 نتيجة من كل منصة (الإجمالي ممكن يوصل 80 نتيجة)
            results = DDGS().text(q, max_results=20)
            
            for res in list(results):
                # دمج النص
                content = str(res.get('body', '')) + " " + str(res.get('title', ''))
                
                # استخراج الأرقام (بياخد أي 11 رقم ورا بعض حتى لو بينهم مسافات)
                # النمط ده بيمسك: 010xxxxxxxxx أو 010 xxxx xxxx
                phones = re.findall(r'(01[0125][0-9 \-]{8,15})', content)
                
                for raw_phone in phones:
                    # تنظيف
                    phone = raw_phone.replace(" ", "").replace("-", "")
                    
                    if len(phone) == 11:
                        try:
                            # تحديد المصدر بدقة (عشان تعرف الرقم جه منين)
                            source_platform = "Web"
                            if "t.me" in res.get('href', ''): source_platform = "Telegram"
                            elif "olx" in res.get('href', ''): source_platform = "OLX"
                            elif "facebook" in res.get('href', ''): source_platform = "Facebook"
                            
                            data = {
                                "phone_number": phone,
                                "source": f"{source_platform}: {keyword}",
                                "status": "NEW",
                                "notes": f"Link: {res.get('href')}"
                            }
                            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
                            print(f"   ✅ CAUGHT ({source_platform}): {phone}")
                            total_found += 1
                        except: pass
                    
        except Exception as e:
            print(f"   ⚠️ Network Error: {e}")

    print(f"🏁 Mission Complete. Total Leads: {total_found}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain Online (Wide Net) 🧠"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Deployed"}

# ... (باقي كود Analyze Intent و Chat زي ما هو)
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
