import os
import json
import re
import random
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

print("--- System Starting: Hunter V5 (Lite Mode) ---")

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

def save_lead(phone, email, keyword, source_link, platform):
    data = {"source": f"{platform}: {keyword}", "status": "NEW", "notes": f"Link: {source_link}"}
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ SAVED: {phone}")
            return True
        except: return False
    elif email:
        data["phone_number"] = f"email_{email}"
        data["email"] = email
        data["status"] = "EMAIL_ONLY"
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 SAVED EMAIL: {email}")
            return True
        except: return False
    return False

def run_hunter_process(keyword: str, city: str):
    print(f"🕵️‍♂️ [HUNTER LITE] Searching for: {keyword}")
    if not supabase: return

    queries = [
        f'site:facebook.com "{keyword}" "{city}" "010"',
        f'site:olx.com.eg "{keyword}" "010"',
        f'"{keyword}" "{city}" "010" OR "011"'
    ]
    
    count = 0
    
    for q in queries:
        print(f"🔎 Trying: {q}")
        try:
            # التغيير هنا: backend='lite' (أسرع ومش بيتبلك)
            results = DDGS().text(q, max_results=25, backend='lite')
            
            if not results:
                print("   ⚠️ No results from DDG Lite.")
                continue

            for res in list(results):
                content = str(res.get('body', '')) + " " + str(res.get('title', ''))
                platform = "Web"
                if "facebook" in res.get('href', ''): platform = "Facebook"
                
                # استخراج أرقام
                phones = re.findall(r'(01[0125][0-9 \-]{8,15})', content)
                for raw in phones:
                    clean = raw.replace(" ", "").replace("-", "")
                    if len(clean) == 11:
                        if save_lead(clean, None, keyword, res.get('href'), platform): count += 1
                        
        except Exception as e:
            print(f"   ⚠️ Search Error: {e}")

    # --- كود الاختبار (عشان نتأكد إن الداتابيس شغالة) ---
    if count == 0:
        print("⚠️ لم نجد نتائج حقيقية، جاري إضافة عميل تجريبي للتأكد من النظام...")
        test_phone = f"010{random.randint(10000000, 99999999)}"
        save_lead(test_phone, "test@example.com", "TEST_RUN", "System Check", "TEST")
        print(f"🧪 تمت إضافة عميل تجريبي: {test_phone}")
    
    print(f"🏁 Finished. Total: {count}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Hunter V5 Lite Online"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Deployed"}

# ... (باقي كود analyze_intent و chat زي ما هو - متتغيرش)
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
