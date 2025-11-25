import os
import json
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client
from googlesearch import search
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. إعدادات الاتصال (للسحابة) ---
# الموديل بيحاول يجيب المفاتيح من بيئة السيرفر
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    # استخدام Llama 3 السريع والمجاني
    llm = ChatGroq(model="llama3-70b-8192", temperature=0.3, api_key=GROQ_API_KEY)
except:
    print("⚠️ تحذير: المفاتيح غير موجودة، النظام يعمل في وضع Offline")
    supabase = None
    llm = None

app = FastAPI()

# --- 2. أنواع البيانات ---
class HuntRequest(BaseModel):
    keyword: str
    city: str

class ChatRequest(BaseModel):
    phone_number: str
    message: str

# --- 3. كود الصياد (يجيب عملاء من جوجل) ---
def run_hunter_process(keyword: str, city: str):
    if not supabase: return
    print(f"🕵️‍♂️ الصياد يبحث عن: {keyword} في {city}")
    
    # معادلة البحث (X-Ray Search)
    query = f'site:facebook.com OR site:instagram.com OR site:linkedin.com "{keyword}" "{city}" "010" OR "011" OR "012"'
    
    try:
        # بنبحث عن أول 15 نتيجة
        results = search(query, num_results=15, advanced=True)
        count = 0
        
        for res in results:
            text_blob = res.description + " " + res.title
            if "01" in text_blob:
                try:
                    # محاولة استخراج رقم مصري (01xxxxxxxxx)
                    import re
                    match = re.search(r'01\d{9}', text_blob)
                    if match:
                        phone = match.group(0)
                        # حفظ العميل في قاعدة البيانات
                        supabase.table("leads").upsert({
                            "phone_number": phone,
                            "source": f"Hunter: {keyword}",
                            "status": "NEW",
                            "notes": f"Source: {res.url}"
                        }, on_conflict="phone_number").execute()
                        count += 1
                except:
                    continue
        print(f"✅ انتهى الصيد. تم حفظ {count} عميل.")
    except Exception as e:
        print(f"❌ خطأ في الصيد: {e}")

# --- 4. روابط التحكم (Endpoints) ---

@app.get("/")
def home():
    return {"status": "Brain is Online 🧠", "model": "Llama 3"}

# رابط تشغيل الصياد
@app.post("/start_hunt")
async def start_hunt(req: HuntRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_hunter_process, req.keyword, req.city)
    return {"status": "Hunter Deployed 🚀"}

# رابط تحليل النية (الفلتر)
@app.post("/analyze_intent")
async def analyze_intent(req: ChatRequest):
    if not supabase: return {"action": "STOP", "reply": "DB Error"}
    
    # جلب إعدادات المناطق
    settings = supabase.table("project_settings").select("*").limit(1).execute()
    allowed = settings.data[0]['allowed_cities'] if settings.data else "القاهرة"
    
    # سؤال الذكاء الاصطناعي
    prompt = f"""
    حلل رسالة العميل: "{req.message}"
    هل هو داخل المناطق المسموحة ({allowed})؟ (INSIDE / OUTSIDE / UNKNOWN)
    هل هو مهتم؟ (INTERESTED / NOT_INTERESTED)
    رد بـ JSON فقط: {{"loc": "...", "intent": "..."}}
    """
    try:
        chain = ChatPromptTemplate.from_template(prompt) | llm | StrOutputParser()
        res_txt = chain.invoke({}).replace("```json", "").replace("```", "").strip()
        if "{" in res_txt: # تنظيف إضافي
            res_txt = res_txt[res_txt.find("{"):res_txt.rfind("}")+1]
        res = json.loads(res_txt)
    except:
        res = {"loc": "UNKNOWN", "intent": "INTERESTED"} # افتراضي

    # اتخاذ القرار
    if res.get('loc') == 'OUTSIDE':
        return {"action": "STOP", "reply": "نعتذر، الخدمة غير متاحة في منطقتك."}
    
    if res.get('intent') == 'NOT_INTERESTED':
        supabase.table("leads").upsert({"phone_number": req.phone_number, "status": "STOPPED"}, on_conflict="phone_number").execute()
        return {"action": "STOP", "reply": "شكراً لك."}

    return {"action": "PROCEED", "intent": res.get('intent')}

# رابط الشات (الرد الذكي)
@app.post("/chat")
async def chat(req: ChatRequest):
    # جلب تفاصيل المنتج
    camp = supabase.table("campaigns").select("*").eq("is_active", True).limit(1).execute()
    info = camp.data[0]['product_description'] if camp.data else "لا توجد حملة نشطة"
    
    prompt = f"""
    أنت بائع محترف باللهجة المصرية.
    المنتج: {info}
    العميل يسأل: {req.message}
    رد باختصار وإقناع لإتمام البيع.
    """
    response = llm.invoke(prompt).content
    
    # تسجيل المحادثة
    supabase.table("interactions").insert({
        "phone_number": req.phone_number,
        "user_query": req.message,
        "ai_response": response
    }).execute()
    
    return {"response": response}
