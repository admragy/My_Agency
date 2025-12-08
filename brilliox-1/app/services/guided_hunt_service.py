"""
Guided Hunt Service
Smart conversational lead hunting with self-learning
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re
import app.core.database as db_module
from app.core.database import LOCAL_DB


class GuidedHuntSession:
    """Manages guided hunting sessions for users"""
    
    STEPS = [
        {
            "id": "target_type",
            "question": "🎯 **أهلاً! أنا مساعدك الذكي للصيد**\n\nإيه نوع العملاء اللي بتدور عليهم؟\n\n1️⃣ مشترين عقارات\n2️⃣ بايعين عقارات\n3️⃣ مستثمرين\n4️⃣ شركات عقارية\n5️⃣ نوع تاني (اكتبه)",
            "key": "target_type",
            "options": {"1": "مشترين عقارات", "2": "بايعين عقارات", "3": "مستثمرين", "4": "شركات عقارية"}
        },
        {
            "id": "property_type", 
            "question": "🏠 **تمام! إيه نوع العقار؟**\n\n1️⃣ شقق سكنية\n2️⃣ فيلات\n3️⃣ أراضي\n4️⃣ محلات تجارية\n5️⃣ مكاتب\n6️⃣ كل الأنواع",
            "key": "property_type",
            "options": {"1": "شقق", "2": "فيلات", "3": "أراضي", "4": "محلات", "5": "مكاتب", "6": "عقارات"}
        },
        {
            "id": "location",
            "question": "📍 **فين المنطقة؟**\n\nاكتب اسم المدينة أو المنطقة\n(مثال: القاهرة، التجمع الخامس، الرياض، دبي)",
            "key": "location",
            "options": None
        },
        {
            "id": "budget",
            "question": "💰 **الميزانية المتوقعة؟**\n\n1️⃣ أقل من مليون\n2️⃣ 1-3 مليون\n3️⃣ 3-5 مليون\n4️⃣ أكثر من 5 مليون\n5️⃣ أي ميزانية",
            "key": "budget",
            "options": {"1": "اقتصادي", "2": "متوسط", "3": "فاخر", "4": "سوبر لوكس", "5": ""}
        },
        {
            "id": "count",
            "question": "👥 **كام عميل تحتاج؟**\n\nاكتب الرقم (من 5 لـ 50)",
            "key": "count",
            "options": None
        },
        {
            "id": "confirm",
            "question": None,
            "key": "confirm",
            "options": {"1": "ابدأ", "2": "تعديل"}
        }
    ]
    
    _sessions: Dict[str, Dict] = {}
    
    @classmethod
    def start_session(cls, user_id: str) -> Dict:
        """Start a new guided hunt session"""
        cls._sessions[user_id] = {
            "step": 0,
            "data": {},
            "started_at": datetime.now().isoformat(),
            "active": True
        }
        return {
            "message": cls.STEPS[0]["question"],
            "step": 0,
            "is_guided_hunt": True
        }
    
    @classmethod
    def get_session(cls, user_id: str) -> Optional[Dict]:
        """Get active session for user"""
        session = cls._sessions.get(user_id)
        if session and session.get("active"):
            return session
        return None
    
    @classmethod
    def process_response(cls, user_id: str, response: str) -> Dict:
        """Process user response and advance to next step"""
        session = cls.get_session(user_id)
        if not session:
            return cls.start_session(user_id)
        
        current_step = session["step"]
        step_config = cls.STEPS[current_step]
        
        if step_config["options"]:
            value = step_config["options"].get(response.strip(), response.strip())
        else:
            value = response.strip()
        
        if step_config["key"] == "count":
            try:
                count = int(re.sub(r'\D', '', value))
                value = max(5, min(50, count))
            except:
                value = 20
        
        session["data"][step_config["key"]] = value
        session["step"] += 1
        
        if session["step"] >= len(cls.STEPS) - 1:
            summary = cls._build_summary(session["data"])
            return {
                "message": summary,
                "step": session["step"],
                "is_guided_hunt": True,
                "ready_to_hunt": True,
                "hunt_data": session["data"]
            }
        
        next_step = cls.STEPS[session["step"]]
        return {
            "message": next_step["question"],
            "step": session["step"],
            "is_guided_hunt": True
        }
    
    @classmethod
    def _build_summary(cls, data: Dict) -> str:
        """Build confirmation summary"""
        return f"""📋 **ملخص طلبك:**

🎯 نوع العميل: **{data.get('target_type', 'غير محدد')}**
🏠 نوع العقار: **{data.get('property_type', 'غير محدد')}**
📍 المنطقة: **{data.get('location', 'غير محدد')}**
💰 الميزانية: **{data.get('budget', 'أي ميزانية') or 'أي ميزانية'}**
👥 العدد: **{data.get('count', 20)} عميل**

هل تريد البدء في الصيد؟
1️⃣ ابدأ الصيد الآن
2️⃣ تعديل البيانات"""
    
    @classmethod
    def confirm_hunt(cls, user_id: str, confirm: str) -> Optional[Dict]:
        """Confirm and prepare hunt data"""
        session = cls.get_session(user_id)
        if not session or not session.get("data"):
            return None
        
        if confirm.strip() in ["1", "ابدأ", "نعم", "اه", "أيوه", "تمام", "يلا"]:
            hunt_data = session["data"].copy()
            cls.end_session(user_id)
            return hunt_data
        elif confirm.strip() in ["2", "تعديل", "لا"]:
            cls._sessions[user_id] = {
                "step": 0,
                "data": {},
                "started_at": datetime.now().isoformat(),
                "active": True
            }
            return {"restart": True}
        
        return None
    
    @classmethod
    def end_session(cls, user_id: str):
        """End user session"""
        if user_id in cls._sessions:
            cls._sessions[user_id]["active"] = False


class LeadFeedbackService:
    """Tracks lead quality feedback for learning"""
    
    @staticmethod
    def report_bad_lead(user_id: str, lead_id: str, reason: str, search_params: Dict) -> bool:
        """Report a bad/wrong lead for learning"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS lead_feedback (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(100),
                        lead_id VARCHAR(100),
                        reason TEXT,
                        search_params JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    INSERT INTO lead_feedback (user_id, lead_id, reason, search_params)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, lead_id, reason, json.dumps(search_params)))
                db_module.pg_conn.commit()
                cur.close()
                return True
            except Exception as e:
                print(f"Lead feedback error: {e}")
                db_module.pg_conn.rollback()
        
        if "lead_feedback" not in LOCAL_DB:
            LOCAL_DB["lead_feedback"] = []
        LOCAL_DB["lead_feedback"].append({
            "user_id": user_id,
            "lead_id": lead_id,
            "reason": reason,
            "search_params": search_params,
            "created_at": datetime.now().isoformat()
        })
        return True
    
    @staticmethod
    def get_bad_patterns(user_id: str) -> List[str]:
        """Get patterns to avoid based on feedback"""
        patterns = []
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT DISTINCT reason FROM lead_feedback
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 50
                """, (user_id,))
                patterns = [row["reason"] for row in cur.fetchall()]
                cur.close()
            except:
                pass
        else:
            feedback_list = LOCAL_DB.get("lead_feedback", [])
            patterns = [f["reason"] for f in feedback_list if f["user_id"] == user_id][-50:]
        
        return patterns


class DuplicateChecker:
    """Prevents duplicate leads"""
    
    @staticmethod
    def get_existing_phones(user_id: str) -> set:
        """Get all phone numbers for user's existing leads"""
        phones = set()
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT phone_number FROM leads 
                    WHERE user_id = %s AND phone_number IS NOT NULL AND phone_number != ''
                """, (user_id,))
                phones = {row["phone_number"] for row in cur.fetchall()}
                cur.close()
            except Exception as e:
                print(f"Get phones error: {e}")
        else:
            leads = LOCAL_DB.get("leads", {}).get(user_id, [])
            phones = {l.get("phone", "") for l in leads if l.get("phone")}
        
        return phones
    
    @staticmethod
    def get_existing_emails(user_id: str) -> set:
        """Get all emails for user's existing leads"""
        emails = set()
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT email FROM leads 
                    WHERE user_id = %s AND email IS NOT NULL AND email != ''
                """, (user_id,))
                emails = {row["email"].lower() for row in cur.fetchall()}
                cur.close()
            except Exception as e:
                print(f"Get emails error: {e}")
        else:
            leads = LOCAL_DB.get("leads", {}).get(user_id, [])
            emails = {l.get("email", "").lower() for l in leads if l.get("email")}
        
        return emails
    
    @classmethod
    def filter_duplicates(cls, user_id: str, leads: List[Dict]) -> List[Dict]:
        """Filter out duplicate leads"""
        existing_phones = cls.get_existing_phones(user_id)
        existing_emails = cls.get_existing_emails(user_id)
        
        unique_leads = []
        new_phones = set()
        new_emails = set()
        
        for lead in leads:
            phone = lead.get("phone", "")
            email = (lead.get("email", "") or "").lower()
            
            if phone:
                if phone in existing_phones or phone in new_phones:
                    continue
                new_phones.add(phone)
            elif email:
                if email in existing_emails or email in new_emails:
                    continue
                new_emails.add(email)
            else:
                continue
            
            unique_leads.append(lead)
        
        return unique_leads


def detect_hunt_intent(message: str) -> bool:
    """Detect if user wants to hunt for leads"""
    hunt_keywords = [
        "اصطاد", "صيد", "ابحث", "دور", "جيب", "هات",
        "عملاء", "عميل", "زباين", "زبون", "leads",
        "محتاج عملاء", "عايز عملاء", "ابحث عن",
        "جيبلي", "هاتلي", "دورلي", "لاقيلي"
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in hunt_keywords)


def build_search_query(hunt_data: Dict) -> tuple:
    """Build optimized search query from hunt data"""
    target = hunt_data.get("target_type", "عقارات")
    property_type = hunt_data.get("property_type", "")
    location = hunt_data.get("location", "القاهرة")
    budget = hunt_data.get("budget", "")
    
    query_parts = []
    
    if "مشتر" in target:
        query_parts.append("محتاج")
        query_parts.append("عايز")
    elif "بايع" in target:
        query_parts.append("للبيع")
    elif "مستثمر" in target:
        query_parts.append("استثمار")
    elif "شركات" in target:
        query_parts.append("شركة عقارات")
    
    if property_type and property_type != "عقارات":
        query_parts.append(property_type)
    else:
        query_parts.append("عقارات")
    
    if budget:
        query_parts.append(budget)
    
    query = " ".join(query_parts)
    count = int(hunt_data.get("count", 20))
    
    return query, location, count
