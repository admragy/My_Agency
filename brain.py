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

# جلب المفاتيح
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

print("--- Start Up Logs ---")
if not SUPABASE_URL: print("❌ Supabase URL missing")
if not SUPABASE_KEY: print("❌ Supabase KEY missing")
if not GROQ_API_KEY: print("❌ Groq KEY missing")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
    print("✅ Database & AI Connected Successfully!")
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

# --- وظيفة الصياد المحدثة (DuckDuckGo) ---
def run_hunter_process(keyword: str, city: str):
    print(f"🕵️‍♂️ [HUNTER STARTED] Searching for: {keyword} in {city}")
    
    if not supabase:
        print("❌ Hunter stopped: Database not connected.")
        return

    # بحث واسع يشمل منصات التواصل
    query = f'{keyword} {city} "010" OR "011" OR "012" OR "015" (site:facebook.com OR site:instagram.com OR site:linkedin.com)'
    
    try:
        # استخدام DuckDuckGo السريع
        results = DDGS().text(query, max_results=20)
        count = 0
        
        if not results:
            print("⚠️ No results found.")
            return

        for res in results:
            # دمج العنوان والوصف للبحث عن الرقم
            text_blob = str(res.get('body', '')) + " " + str(res.get('title', ''))
            
            # استخراج أرقام الموبايل المصرية
            phones = re.findall(r'(01[0125][0-9]{8})', text_blob)
            
            for phone in phones:
                # حفظ الرقم في الداتابيس
                try:
                    data = {
                        "phone_number": phone,
                        "source": f"Hunter: {keyword}",
                        "status": "NEW",
                        "notes": f"Source: {res.get('href', 'Google')}"
                    }
                    supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
                    print(f"✅ Saved Lead: {phone}")
                    count += 1
                except Exception as db_err:
                    print(f"⚠️ DB Error for {phone}: {db_err}")
                    
        print(f"🏁 Hunter Finished. Total saved: {count}")
        
    except Exception as e:
        print(f"❌ Hunter Crash: {e}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Brain Online 🧠", "hunter": "DuckDuckGo"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    print(f"📩 Received Hunt Order: {req.keyword}")
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Hunter Deployed"}

# ... (باقي كود analyze_intent و chat زي ما هو، لو محتاجه قولي أنسخهولك تاني)
@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest):
    if not supabase: return {"action": "STOP", "reply": "DB Error"}
    settings = supabase.table("project_settings").select("*").limit(1).execute()
    allowed = settings.data[0]['allowed_cities'] if settings.data else "القاهرة"
    
    prompt = f"""حلل: "{req.message}". المسموح: {allowed}. JSON: {{"loc": "INSIDE/OUTSIDE", "intent": "INTERESTED/NOT"}}"""
    try:
        res = json.loads(StrOutputParser().invoke(ChatPromptTemplate.from_template(prompt).invoke({}, llm=llm)).replace("```json","").replace("```","").strip())
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
