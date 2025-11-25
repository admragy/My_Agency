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

print("--- Hunter v4 (Phone + Email) ---")
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
    print("✅ System Ready!")
except Exception as e:
    print(f"❌ Error: {e}")
    supabase = None
    llm = None

app = FastAPI()

class HuntRequest(BaseModel):
    keyword: str
    city: str

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- الصياد المزدوج (موبايل + إيميل) ---
def run_hunter_process(keyword: str, city: str):
    print(f"🕵️‍♂️ [HUNTER] Targeting: {keyword} in {city}")
    
    if not supabase: return

    # بنبحث في كل حتة
    queries = [
        f'site:facebook.com "{keyword}" "{city}" "010"',
        f'site:instagram.com "{keyword}" "{city}" "010"',
        f'site:linkedin.com "{keyword}" "{city}" "@gmail.com"', # لينكد إن مليان إيميلات
        f'"{keyword}" "{city}" "@gmail.com" OR "@yahoo.com"'
    ]
    
    total_phones = 0
    total_emails = 0
    
    for q in queries:
        try:
            results = DDGS().text(q, max_results=25)
            
            for res in list(results):
                content = str(res.get('body', '')) + " " + str(res.get('title', ''))
                
                # 1. صيد الأرقام
                phones = re.findall(r'(01[0125][0-9 \-]{8,15})', content)
                for raw_phone in phones:
                    phone = raw_phone.replace(" ", "").replace("-", "")
                    if len(phone) == 11:
                        save_lead(phone, None, keyword, res.get('href'))
                        total_phones += 1

                # 2. صيد الإيميلات (لو ملقيناش رقم، أو حتى لو لقينا)
                # المعادلة دي بتجيب أي إيميل ينتهي بـ .com أو .net
                emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                for email in emails:
                    # بنسجل الإيميل، ولو مفيش رقم بنستخدم الإيميل كمعرف مؤقت
                    save_lead(None, email, keyword, res.get('href'))
                    total_emails += 1
                    
        except Exception as e:
            print(f"⚠️ Search Error: {e}")

    print(f"🏁 Done. Phones: {total_phones} | Emails: {total_emails}")

def save_lead(phone, email, keyword, source_link):
    data = {
        "source": f"Hunter: {keyword}",
        "status": "NEW",
        "notes": f"Source: {source_link}"
    }
    
    # لو معانا رقم، هو ده الأساس
    if phone:
        data["phone_number"] = phone
        if email: data["email"] = email # لو لقينا الاتنين، خير وبركة
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   ✅ Saved Phone: {phone}")
        except: pass

    # لو معانا إيميل بس (ومفيش رقم)، هنسجله برضه
    elif email:
        # عشان الجدول بيحتاج phone_number وممنوع التكرار
        # هنحط الإيميل في خانة الرقم مؤقتاً لحد ما نكلمه
        data["phone_number"] = f"email_{email}" 
        data["email"] = email
        data["status"] = "EMAIL_ONLY" # عشان نعرف إن ده محتاج يتبعتله إيميل
        try:
            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
            print(f"   📧 Saved Email: {email}")
        except: pass

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Hunter v4 Online 🧠"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Deployed"}

# ... (باقي كود analyze_intent و chat زي ما هو بالضبط)
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
