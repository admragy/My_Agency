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

# جلب المفاتيح
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SERPER_API_KEY = os.environ.get("SERPER_API_KEY") # المفتاح الجديد

print("--- Hunter V6 (Google Serper API) ---")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
    print("✅ System Connected!")
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

# --- الصياد النووي (Serper Google Search) ---
def run_hunter_process(keyword: str, city: str):
    print(f"🕵️‍♂️ [SERPER HUNTER] Targeting: {keyword} in {city}")
    
    if not supabase or not SERPER_API_KEY:
        print("❌ Missing Config (DB or Serper Key)")
        return

    # استراتيجيات البحث القوية
    queries = [
        f'site:facebook.com "{keyword}" "{city}" "010"',
        f'site:instagram.com "{keyword}" "{city}" "010"',
        f'site:olx.com.eg "{keyword}" "010"',
        f'"{keyword}" "{city}" "010" OR "011" OR "012"'
    ]
    
    url = "https://google.serper.dev/search"
    total_saved = 0

    for q in queries:
        print(f"🚀 Launching Query: {q}")
        payload = json.dumps({"q": q, "num": 50}) # هات 50 نتيجة في المرة الواحدة
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            results = response.json().get("organic", [])
            
            if not results:
                print("   ⚠️ No results from Google.")
                continue

            print(f"   -> Google returned {len(results)} pages. Scanning...")

            for res in results:
                # دمج العنوان والوصف (Snippet)
                content = str(res.get('title', '')) + " " + str(res.get('snippet', ''))
                
                # استخراج الأرقام
                phones = re.findall(r'(01[0125][0-9 \-]{8,15})', content)
                
                for raw_phone in phones:
                    phone = raw_phone.replace(" ", "").replace("-", "")
                    
                    if len(phone) == 11:
                        try:
                            data = {
                                "phone_number": phone,
                                "source": f"Google: {keyword}",
                                "status": "NEW",
                                "notes": f"Link: {res.get('link')}"
                            }
                            supabase.table("leads").upsert(data, on_conflict="phone_number").execute()
                            print(f"   ✅ CAUGHT: {phone}")
                            total_saved += 1
                        except: pass
                        
        except Exception as e:
            print(f"   ❌ API Error: {e}")

    print(f"🏁 Mission Complete. Total Fresh Leads: {total_saved}")

# --- Endpoints ---
@app.get("/")
def home(): return {"status": "Hunter V6 (Nuclear) Online ☢️"}

@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Deployed"}

# ... (باقي كود analyze_intent و chat زي ما هو، سيبه تحت الكود ده)
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
