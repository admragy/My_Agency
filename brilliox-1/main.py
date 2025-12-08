"""
Hunter Pro CRM - Main Entry Point
Version 3.0.0 - Modular Architecture
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import init_db, get_db, LOCAL_DB
import app.core.database as db_module
from app.core.security import rate_limit, sanitize_input
from app.core.i18n import t, get_all_translations, get_direction
from app.services.ai_service import AIService
from app.services.search_service import SearchService
from app.services.user_service import UserService
from app.services.lead_service import LeadService

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("static/css", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/images", exist_ok=True)


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        allowed, msg = rate_limit(client_ip)
        
        if not allowed:
            return JSONResponse({"error": msg}, status_code=429)
        
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


from pydantic import BaseModel, field_validator
from typing import Optional, List
import re
import html


def clean_input(text: str, max_len: int = 2000) -> str:
    if not text:
        return ""
    text = html.escape(str(text)[:max_len])
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


class ChatRequest(BaseModel):
    message: str
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("الرسالة فارغة")
        return clean_input(v, 5000)


class HuntRequest(BaseModel):
    query: str
    city: str = "القاهرة"
    max_results: int = 20
    strategy: str = "social_media"
    country: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AdminSetPasswordRequest(BaseModel):
    username: str
    new_password: str


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve main page"""
    if os.path.exists("templates/index.html"):
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hunter Pro CRM</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { font-family: 'Cairo', sans-serif; }
        body { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); min-height: 100vh; }
        .glass { background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
        .gold { color: #fbbf24; }
        .btn-gold { background: linear-gradient(135deg, #f59e0b, #d97706); }
        .btn-gold:hover { background: linear-gradient(135deg, #d97706, #b45309); }
    </style>
</head>
<body class="text-white">
    <div class="container mx-auto px-4 py-8">
        <div class="text-center mb-8">
            <h1 class="text-4xl font-bold gold mb-2">🎯 Hunter Pro CRM</h1>
            <p class="text-gray-400">نظام الذكاء الاصطناعي لاصطياد العملاء</p>
        </div>
        
        <div class="glass rounded-2xl p-6 max-w-2xl mx-auto">
            <div class="mb-6">
                <label class="block text-sm mb-2">اسم المستخدم</label>
                <input type="text" id="username" placeholder="أدخل اسمك..." 
                    class="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 focus:border-amber-500 outline-none">
            </div>
            
            <button onclick="login()" class="btn-gold w-full py-3 rounded-lg font-bold text-slate-900">
                🚀 ابدأ مجاناً - 100 توكن هدية
            </button>
            
            <div id="result" class="mt-6 hidden glass rounded-lg p-4"></div>
        </div>
        
        <div class="text-center mt-8 text-gray-500 text-sm">
            <p>✨ نسخة 3.0 - بنية جديدة ومنظمة</p>
        </div>
    </div>
    
    <script>
        async function login() {
            const username = document.getElementById('username').value.trim();
            if (!username) { alert('أدخل اسمك'); return; }
            
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username})
                });
                const data = await res.json();
                
                if (data.success) {
                    document.getElementById('result').innerHTML = `
                        <p class="text-green-400">✅ مرحباً ${data.user_id}!</p>
                        <p class="text-amber-400">💰 رصيدك: ${data.wallet_balance} توكن</p>
                    `;
                    document.getElementById('result').classList.remove('hidden');
                }
            } catch(e) {
                alert('خطأ في الاتصال');
            }
        }
    </script>
</body>
</html>
    """)


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "app": settings.APP_NAME,
        "database": db_module.DB_TYPE
    }


@app.get("/api/translations/{lang}")
async def get_translations(lang: str):
    """Get translations for language"""
    return {
        "translations": get_all_translations(lang),
        "direction": get_direction(lang),
        "lang": lang
    }


@app.post("/api/login")
async def login(data: UserCreate):
    """User login/registration with optional password"""
    if data.password:
        user = UserService.login_with_password(data.username, data.password)
        if not user:
            return JSONResponse(status_code=401, content={"error": "اسم المستخدم أو كلمة المرور غير صحيحة"})
    else:
        user = UserService.get_or_create(data.username)
    
    has_password = bool(user.get("password", ""))
    
    return {
        "success": True,
        "user_id": data.username,
        "wallet_balance": user.get("wallet_balance", 100),
        "is_admin": user.get("is_admin", False),
        "has_password": has_password
    }


@app.post("/api/user/{user_id}/change-password")
async def change_password(user_id: str, data: ChangePasswordRequest):
    """Change user password"""
    if len(data.new_password) < 4:
        return JSONResponse(status_code=400, content={"error": "كلمة المرور يجب أن تكون 4 أحرف على الأقل"})
    
    success, message = UserService.change_password(user_id, data.old_password, data.new_password)
    
    if success:
        return {"success": True, "message": message}
    return JSONResponse(status_code=400, content={"error": message})


@app.post("/api/user/{user_id}/set-password")
async def set_user_password(user_id: str, data: ChangePasswordRequest):
    """Set password for first time (when user has no password)"""
    if len(data.new_password) < 4:
        return JSONResponse(status_code=400, content={"error": "كلمة المرور يجب أن تكون 4 أحرف على الأقل"})
    
    success = UserService.set_password(user_id, data.new_password)
    
    if success:
        return {"success": True, "message": "تم تعيين كلمة المرور بنجاح"}
    return JSONResponse(status_code=400, content={"error": "فشل في تعيين كلمة المرور"})


@app.post("/api/admin/set-password")
async def admin_set_password(admin_id: str, data: AdminSetPasswordRequest):
    """Admin sets password for any user"""
    if not UserService.is_admin(admin_id):
        return JSONResponse(status_code=403, content={"error": "غير مصرح لك"})
    
    if len(data.new_password) < 4:
        return JSONResponse(status_code=400, content={"error": "كلمة المرور يجب أن تكون 4 أحرف على الأقل"})
    
    success = UserService.set_password(data.username, data.new_password)
    
    if success:
        return {"success": True, "message": f"تم تعيين كلمة مرور {data.username}"}
    return JSONResponse(status_code=400, content={"error": "فشل في تعيين كلمة المرور"})


@app.get("/api/wallet/{user_id}")
async def get_wallet(user_id: str):
    """Get wallet balance"""
    user = UserService.get_or_create(user_id)
    return {
        "user_id": user_id,
        "wallet_balance": user.get("wallet_balance", 0),
        "is_admin": user.get("is_admin", False)
    }


from app.services.unified_chat_service import UnifiedChatService
from app.services.smart_hunt_service import DuplicateChecker


@app.post("/api/chat/{user_id}")
async def chat(user_id: str, data: ChatRequest):
    """AI chat endpoint - unified system for all features"""
    message = data.message.strip()
    is_admin = UserService.is_admin(user_id)
    
    try:
        result = await UnifiedChatService.process_message(user_id, message, is_admin)
        
        user = UserService.get_or_create(user_id)
        result["remaining_balance"] = user.get("wallet_balance", 0)
        
        return result
    except Exception as e:
        print(f"Chat error: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "حدث خطأ، حاول مرة أخرى", "tokens_used": 0}
        )


@app.post("/api/hunt/{user_id}")
async def hunt(user_id: str, data: HuntRequest):
    """Lead hunting endpoint with strategy and country support"""
    can_afford, balance = UserService.check_balance(user_id, settings.HUNT_COST)
    
    if not can_afford:
        return JSONResponse(
            status_code=402,
            content={"error": f"رصيدك غير كافي ({balance} توكن). المطلوب: {settings.HUNT_COST} توكن"}
        )
    
    try:
        leads = SearchService.hunt_leads(
            query=data.query, 
            city=data.city, 
            max_results=data.max_results,
            strategy=data.strategy,
            country=data.country
        )
        
        if leads:
            LeadService.add_leads_batch(user_id, leads)
            UserService.deduct_balance(user_id, settings.HUNT_COST)
        
        user = UserService.get_or_create(user_id)
        detected_country = AIService.detect_country(data.city) if not data.country else data.country
        
        return {
            "leads": leads,
            "count": len(leads),
            "tokens_used": settings.HUNT_COST if leads else 0,
            "remaining_balance": user.get("wallet_balance", 0),
            "strategy": data.strategy,
            "country": detected_country
        }
    except Exception as e:
        print(f"Hunt error: {e}")
        user = UserService.get_or_create(user_id)
        return {
            "leads": [],
            "count": 0,
            "tokens_used": 0,
            "remaining_balance": user.get("wallet_balance", 0),
            "error": "حدث خطأ في البحث، حاول مرة أخرى"
        }


@app.get("/api/hunt/strategies")
async def get_hunting_strategies():
    """Get available hunting strategies"""
    return {
        "strategies": AIService.get_available_strategies(),
        "default": "social_media"
    }


@app.get("/api/hunt/countries")
async def get_available_countries():
    """Get available countries with their cities"""
    return {
        "countries": AIService.get_available_countries(),
        "default": "egypt"
    }


@app.get("/api/leads/{user_id}")
async def get_leads(user_id: str, status: Optional[str] = None):
    """Get user leads"""
    leads = LeadService.get_user_leads(user_id)
    
    if status:
        leads = [l for l in leads if l.get("status") == status]
    
    return {"leads": leads, "count": len(leads)}


@app.get("/api/stats/{user_id}")
async def get_stats(user_id: str):
    """Get user statistics"""
    user = UserService.get_or_create(user_id)
    lead_stats = LeadService.get_lead_stats(user_id)
    
    return {
        "user_id": user_id,
        "wallet_balance": user.get("wallet_balance", 0),
        "leads": lead_stats
    }


class AddLeadRequest(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    status: str = "new"
    notes: Optional[str] = None


class ImportLeadsRequest(BaseModel):
    leads: List[dict]


@app.post("/api/leads/{user_id}/add")
async def add_lead(user_id: str, data: AddLeadRequest):
    """Add a single lead manually"""
    try:
        lead_data = {
            "name": clean_input(data.name),
            "phone": clean_input(data.phone),
            "email": clean_input(data.email) if data.email else None,
            "status": data.status,
            "notes": clean_input(data.notes) if data.notes else None,
            "source": "manual"
        }
        
        LeadService.add_lead(user_id, lead_data)
        
        return {"success": True, "message": "تم إضافة العميل بنجاح"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/leads/{user_id}/import")
async def import_leads(user_id: str, data: ImportLeadsRequest):
    """Import leads from Excel/CSV"""
    try:
        imported = 0
        for lead in data.leads:
            if lead.get("name") or lead.get("phone"):
                lead_data = {
                    "name": clean_input(str(lead.get("name", ""))),
                    "phone": clean_input(str(lead.get("phone", ""))),
                    "email": clean_input(str(lead.get("email", ""))) if lead.get("email") else None,
                    "status": "new",
                    "source": "import"
                }
                LeadService.add_lead(user_id, lead_data)
                imported += 1
        
        return {"success": True, "imported": imported, "message": f"تم استيراد {imported} عميل"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


class ShareLeadRequest(BaseModel):
    lead_id: str
    share_with: str
    status: Optional[str] = "new"
    notes: Optional[str] = ""


class ShareLeadsBatchRequest(BaseModel):
    lead_ids: List[str]
    share_with: str
    status: Optional[str] = "new"
    notes: Optional[str] = ""


class UpdateSharedStatusRequest(BaseModel):
    share_id: str
    status: str
    notes: Optional[str] = None


class UpdateLeadRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


@app.post("/api/leads/{user_id}/share")
async def share_lead(user_id: str, data: ShareLeadRequest):
    """Share lead with another user including status"""
    try:
        success = LeadService.share_lead(user_id, data.share_with, data.lead_id, data.status or "new", data.notes or "")
        if success:
            return {"success": True, "message": f"تم مشاركة العميل مع {data.share_with}"}
        return JSONResponse(status_code=500, content={"error": "فشل في مشاركة العميل"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/leads/{user_id}/share-batch")
async def share_leads_batch(user_id: str, data: ShareLeadsBatchRequest):
    """Share multiple leads with another user"""
    try:
        result = LeadService.share_leads_batch(user_id, data.share_with, data.lead_ids, data.status or "new", data.notes or "")
        return {
            "success": True, 
            "message": f"تم مشاركة {result['success']} عميل مع {data.share_with}",
            "details": result
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.put("/api/leads/{user_id}/shared/status")
async def update_shared_status(user_id: str, data: UpdateSharedStatusRequest):
    """Update shared lead status - both sender and receiver can update"""
    try:
        success = LeadService.update_shared_lead_status(data.share_id, user_id, data.status, data.notes or "")
        if success:
            return {"success": True, "message": "تم تحديث حالة العميل"}
        return JSONResponse(status_code=404, content={"error": "العميل المشترك غير موجود"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/leads/{user_id}/shared")
async def get_shared_leads(user_id: str):
    """Get leads shared with user"""
    leads = LeadService.get_shared_leads(user_id)
    return {"leads": leads, "count": len(leads)}


@app.get("/api/leads/{user_id}/shared/sent")
async def get_sent_shared_leads(user_id: str):
    """Get leads that user has shared with others"""
    leads = LeadService.get_sent_shared_leads(user_id)
    return {"leads": leads, "count": len(leads)}


@app.get("/api/users/list")
async def get_users_list():
    """Get list of users for sharing leads"""
    try:
        users = UserService.get_all_users()
        return {"users": [{"username": u.get("username"), "id": u.get("id")} for u in users], "count": len(users)}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.delete("/api/leads/{user_id}/{lead_id}")
async def delete_lead(user_id: str, lead_id: str):
    """Delete a lead"""
    success = LeadService.delete_lead(lead_id, user_id)
    if success:
        return {"success": True, "message": "تم حذف العميل"}
    return JSONResponse(status_code=404, content={"error": "العميل غير موجود"})


@app.put("/api/leads/{user_id}/{lead_id}")
async def update_lead(user_id: str, lead_id: str, data: UpdateLeadRequest):
    """Update lead data"""
    updates = {}
    if data.name is not None:
        updates["name"] = clean_input(data.name)
    if data.phone is not None:
        updates["phone"] = clean_input(data.phone)
    if data.email is not None:
        updates["email"] = clean_input(data.email)
    if data.status is not None:
        updates["status"] = data.status
    if data.notes is not None:
        updates["notes"] = clean_input(data.notes)
    
    if updates:
        lead = LeadService.update_lead(lead_id, user_id, updates)
        if lead:
            return {"success": True, "lead": lead}
    return JSONResponse(status_code=404, content={"error": "العميل غير موجود"})


class FeedbackRequest(BaseModel):
    lead_id: Optional[str] = None
    rating: int
    notes: Optional[str] = None


@app.post("/api/feedback/{user_id}")
async def submit_feedback(user_id: str, data: FeedbackRequest):
    """Submit feedback for a lead"""
    try:
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            from psycopg2.extras import RealDictCursor
            cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                INSERT INTO feedback (user_id, lead_id, rating, notes)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING *
            """, (user_id, data.lead_id, data.rating, clean_input(data.notes) if data.notes else None))
            db_module.pg_conn.commit()
            cur.close()
        
        return {"success": True, "message": "تم حفظ التقييم بنجاح"}
    except Exception as e:
        print(f"Feedback error: {e}")
        return {"success": True, "message": "تم حفظ التقييم"}


@app.get("/api/admin/users")
async def get_all_users(admin_id: str):
    """Get all users (admin only)"""
    if not UserService.is_admin(admin_id):
        return JSONResponse(status_code=403, content={"error": "غير مصرح لك"})
    
    users = UserService.get_all_users()
    return {"users": users, "count": len(users)}


class UpdateBalanceRequest(BaseModel):
    user_id: str
    amount: int
    action: str = "add"


@app.get("/api/admin/stats")
async def get_admin_stats(admin_id: str):
    """Get system statistics (admin only)"""
    if not UserService.is_admin(admin_id):
        return JSONResponse(status_code=403, content={"error": "غير مصرح لك"})
    
    stats = {
        "total_users": 0,
        "total_leads": 0,
        "total_tokens_spent": 0,
        "active_users_today": 0
    }
    
    if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
        try:
            from psycopg2.extras import RealDictCursor
            cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
            
            cur.execute("SELECT COUNT(*) as count FROM users")
            stats["total_users"] = cur.fetchone()["count"]
            
            cur.execute("SELECT COUNT(*) as count FROM leads")
            stats["total_leads"] = cur.fetchone()["count"]
            
            cur.execute("SELECT COALESCE(SUM(100 - wallet_balance), 0) as spent FROM users WHERE wallet_balance < 100")
            stats["total_tokens_spent"] = cur.fetchone()["spent"] or 0
            
            cur.close()
        except Exception as e:
            print(f"Admin stats error: {e}")
    
    return {"stats": stats}


@app.get("/api/admin/leads")
async def get_all_leads(admin_id: str, limit: int = 100):
    """Get all leads across all users (admin only)"""
    if not UserService.is_admin(admin_id):
        return JSONResponse(status_code=403, content={"error": "غير مصرح لك"})
    
    leads = []
    
    if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
        try:
            from psycopg2.extras import RealDictCursor
            cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT id, user_id, full_name as name, phone_number as phone, email, status, funnel_stage, created_at 
                FROM leads 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (limit,))
            leads = [dict(row) for row in cur.fetchall()]
            cur.close()
        except Exception as e:
            print(f"Admin leads error: {e}")
    
    return {"leads": leads, "count": len(leads)}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: str, admin_id: str):
    """Delete a user (admin only)"""
    if not UserService.is_admin(admin_id):
        return JSONResponse(status_code=403, content={"error": "غير مصرح لك"})
    
    success, message = UserService.delete_user(user_id)
    if success:
        return {"success": True, "message": message}
    return JSONResponse(status_code=400, content={"error": message})


@app.post("/api/admin/balance")
async def update_user_balance(admin_id: str, data: UpdateBalanceRequest):
    """Update user balance (admin only)"""
    if not UserService.is_admin(admin_id):
        return JSONResponse(status_code=403, content={"error": "غير مصرح لك"})
    
    try:
        if data.action == "add":
            success = UserService.add_balance(data.user_id, data.amount)
        elif data.action == "set":
            UserService.get_or_create(data.user_id)
            if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
                cur = db_module.pg_conn.cursor()
                cur.execute("UPDATE users SET wallet_balance = %s WHERE username = %s", (data.amount, data.user_id))
                success = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
            else:
                current_balance = UserService.get_or_create(data.user_id).get("wallet_balance", 0)
                diff = data.amount - current_balance
                if diff > 0:
                    success = UserService.add_balance(data.user_id, diff)
                elif diff < 0:
                    success = UserService.deduct_balance(data.user_id, -diff)
                else:
                    success = True
        else:
            return JSONResponse(status_code=400, content={"error": "إجراء غير صالح"})
        
        if success:
            user = UserService.get_or_create(data.user_id)
            return {"success": True, "new_balance": user.get("wallet_balance", 0), "message": f"تم تحديث رصيد {data.user_id}"}
        return JSONResponse(status_code=500, content={"error": "فشل في تحديث الرصيد"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


from app.services.learning_service import LearningService


class BaitMessageRequest(BaseModel):
    template_type: str
    variables: Optional[dict] = None


class ImportConversationRequest(BaseModel):
    platform: str
    messages: List[dict]
    rating: int


class SmartReplyRequest(BaseModel):
    customer_message: str
    stage: str


@app.get("/api/funnel/stages")
async def get_funnel_stages():
    """Get all funnel stages"""
    return {"stages": LearningService.get_funnel_stages()}


@app.get("/api/funnel/bait-templates")
async def get_bait_templates():
    """Get all bait message templates"""
    return {"templates": LearningService.get_bait_templates()}


@app.post("/api/funnel/generate-bait")
async def generate_bait(data: BaitMessageRequest):
    """Generate a bait message"""
    message = LearningService.generate_bait_message(data.template_type, data.variables or {})
    return {"message": message, "template_type": data.template_type}


@app.post("/api/learning/{user_id}/import-conversation")
async def import_conversation(user_id: str, data: ImportConversationRequest):
    """Import a conversation for learning"""
    result = LearningService.import_conversation(user_id, data.platform, data.messages, data.rating)
    return {
        "success": True,
        "patterns_found": result["patterns_found"],
        "message": f"تم استخراج {result['patterns_found']} نمط من المحادثة"
    }


@app.post("/api/learning/{user_id}/smart-reply")
async def get_smart_reply(user_id: str, data: SmartReplyRequest):
    """Get AI-powered smart reply"""
    can_afford, balance = UserService.check_balance(user_id, settings.CHAT_COST)
    
    if not can_afford:
        return JSONResponse(
            status_code=402,
            content={"error": f"رصيدك غير كافي ({balance} توكن)"}
        )
    
    reply = LearningService.generate_smart_reply(user_id, data.customer_message, data.stage)
    UserService.deduct_balance(user_id, settings.CHAT_COST)
    user = UserService.get_or_create(user_id)
    
    return {
        "reply": reply,
        "stage": data.stage,
        "tokens_used": settings.CHAT_COST,
        "remaining_balance": user.get("wallet_balance", 0)
    }


@app.get("/api/learning/{user_id}/stats")
async def get_learning_stats(user_id: str):
    """Get learning statistics"""
    stats = LearningService.get_learning_stats(user_id)
    return {"stats": stats}


@app.get("/api/learning/{user_id}/patterns")
async def get_patterns(user_id: str, stage: Optional[str] = None):
    """Get learned patterns"""
    patterns = LearningService.get_patterns(user_id, stage or "")
    return {"patterns": patterns, "count": len(patterns)}


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    db_type = init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.VERSION}")
    print(f"📦 Database: {db_type}")
    print(f"🔗 Running on http://{settings.HOST}:{settings.PORT}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
