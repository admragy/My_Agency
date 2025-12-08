"""
Smart Hunt Service
AI-powered conversational lead hunting for ANY business type
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import re
import app.core.database as db_module
from app.core.database import LOCAL_DB


class SmartHuntSession:
    """AI-driven hunting sessions that understand any business context"""
    
    _sessions: Dict[str, Dict] = {}
    
    SMART_SYSTEM_PROMPT = """أنت مساعد ذكي لاصطياد العملاء المحتملين.

مهمتك:
1. فهم نوع عمل/مهنة المستخدم من كلامه
2. سؤال أسئلة ذكية ومناسبة لمجاله (مش أسئلة ثابتة)
3. تجميع معلومات كافية للبحث عن عملاء

قواعد مهمة:
- لو قال "أنا دكتور أسنان" → اسأل: أي تخصص؟ أي منطقة؟ كام عميل؟
- لو قال "أنا محامي" → اسأل: أي نوع قضايا؟ أي منطقة؟
- لو قال "عندي مطعم" → اسأل: أي نوع أكل؟ أي منطقة؟
- لو قال "سمسار عقارات" → اسأل: شقق ولا فيلات؟ أي منطقة؟ ميزانية العملاء؟

الأسئلة تكون:
- قصيرة ومباشرة
- مناسبة للمجال
- بالعامية المصرية
- سؤال واحد في كل مرة

لما تجمع المعلومات الكافية، قول: [READY] وملخص الطلب"""
    
    @classmethod
    def start_session(cls, user_id: str, initial_message: str = "") -> Dict:
        """Start a new smart hunt session"""
        cls._sessions[user_id] = {
            "messages": [],
            "context": {},
            "started_at": datetime.now().isoformat(),
            "active": True,
            "ready": False
        }
        
        if initial_message:
            return cls.process_message(user_id, initial_message)
        
        return {
            "message": "🎯 **أهلاً! أنا مساعدك الذكي**\n\nقولي إنت بتشتغل إيه أو عندك بيزنس إيه، وهجيبلك عملاء مناسبين!\n\n💡 مثال: \"أنا دكتور أسنان\" أو \"عندي مطعم\" أو \"محامي\"",
            "is_smart_hunt": True,
            "step": "start"
        }
    
    @classmethod
    def get_session(cls, user_id: str) -> Optional[Dict]:
        """Get active session for user"""
        session = cls._sessions.get(user_id)
        if session and session.get("active"):
            return session
        return None
    
    @classmethod
    def process_message(cls, user_id: str, message: str) -> Dict:
        """Process user message with AI understanding"""
        session = cls.get_session(user_id)
        if not session:
            return cls.start_session(user_id, message)
        
        session["messages"].append({"role": "user", "content": message})
        
        from app.services.ai_service import AIService
        
        conversation = "\n".join([
            f"{'المستخدم' if m['role'] == 'user' else 'المساعد'}: {m['content']}" 
            for m in session["messages"]
        ])
        
        prompt = f"""المحادثة السابقة:
{conversation}

بناءً على المحادثة:
1. إذا عندك معلومات كافية (نوع العمل + المنطقة + عدد العملاء المطلوب)، قول [READY] ثم ملخص الطلب
2. إذا محتاج معلومات أكتر، اسأل سؤال واحد مناسب للمجال

ملاحظة: لو المستخدم قال رقم للعملاء (مثلاً 10 أو 20)، يبقى عنده كل المعلومات المطلوبة"""
        
        response = AIService.generate(prompt, cls.SMART_SYSTEM_PROMPT, use_cache=False)
        
        session["messages"].append({"role": "assistant", "content": response})
        
        if "[READY]" in response:
            session["ready"] = True
            clean_response = response.replace("[READY]", "").strip()
            
            context = cls._extract_context(session["messages"])
            session["context"] = context
            
            summary = f"""✅ **تمام! فهمت طلبك:**

{clean_response}

هل أبدأ البحث عن العملاء دلوقتي؟
1️⃣ ابدأ الصيد
2️⃣ تعديل"""
            
            return {
                "message": summary,
                "is_smart_hunt": True,
                "ready_to_hunt": True,
                "hunt_context": context
            }
        
        return {
            "message": response,
            "is_smart_hunt": True,
            "step": "gathering"
        }
    
    @classmethod
    def _extract_context(cls, messages: List[Dict]) -> Dict:
        """Extract hunt context from conversation using AI"""
        from app.services.ai_service import AIService
        
        conversation = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
        
        prompt = f"""من المحادثة التالية، استخرج المعلومات بصيغة JSON:
{conversation}

أخرج JSON فقط بهذا الشكل:
{{"business_type": "نوع العمل/المهنة", "service": "الخدمة المحددة", "location": "المنطقة/المدينة", "count": رقم العملاء المطلوب, "extra_info": "أي معلومات إضافية"}}"""
        
        response = AIService.generate(prompt, "أخرج JSON فقط بدون أي نص إضافي", use_cache=False)
        
        try:
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "business_type": "خدمات",
            "service": "",
            "location": "مصر",
            "count": 20,
            "extra_info": conversation
        }
    
    @classmethod
    def confirm_hunt(cls, user_id: str, confirm: str) -> Optional[Dict]:
        """Confirm and prepare hunt data"""
        session = cls.get_session(user_id)
        if not session or not session.get("ready"):
            return None
        
        if confirm.strip() in ["1", "ابدأ", "نعم", "اه", "أيوه", "تمام", "يلا", "اوك", "ok"]:
            context = session["context"].copy()
            cls.end_session(user_id)
            return context
        elif confirm.strip() in ["2", "تعديل", "لا", "غير"]:
            cls._sessions[user_id] = {
                "messages": [],
                "context": {},
                "started_at": datetime.now().isoformat(),
                "active": True,
                "ready": False
            }
            return {"restart": True}
        
        return None
    
    @classmethod
    def end_session(cls, user_id: str):
        """End user session"""
        if user_id in cls._sessions:
            cls._sessions[user_id]["active"] = False


def build_smart_query(context: Dict) -> tuple:
    """Build search query from smart context"""
    business = context.get("business_type", "")
    service = context.get("service", "")
    location = context.get("location", "مصر")
    count = int(context.get("count", 20))
    extra = context.get("extra_info", "")
    
    search_term = service if service else business
    
    if not search_term and extra:
        search_term = extra[:50]
    
    return search_term, location, min(max(count, 5), 50)


def detect_hunt_intent(message: str) -> bool:
    """Detect if user wants to hunt for leads"""
    hunt_keywords = [
        "اصطاد", "صيد", "ابحث", "دور", "جيب", "هات",
        "عملاء", "عميل", "زباين", "زبون", "leads",
        "محتاج عملاء", "عايز عملاء", "ابحث عن",
        "جيبلي", "هاتلي", "دورلي", "لاقيلي",
        "أنا دكتور", "انا دكتور", "أنا محامي", "انا محامي",
        "عندي مطعم", "عندي شركة", "عندي محل",
        "أنا سمسار", "انا سمسار", "عقارات"
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in hunt_keywords)


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


class DuplicateChecker:
    """Prevents duplicate leads"""
    
    @staticmethod
    def get_existing_phones(user_id: str) -> set:
        """Get ALL phone numbers in database (global check for unique constraint)"""
        phones = set()
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT phone_number FROM leads 
                    WHERE phone_number IS NOT NULL AND phone_number != ''
                """)
                phones = {row["phone_number"] for row in cur.fetchall()}
                cur.close()
            except Exception as e:
                print(f"Get phones error: {e}")
        else:
            for uid, user_leads in LOCAL_DB.get("leads", {}).items():
                for l in user_leads:
                    if l.get("phone"):
                        phones.add(l.get("phone"))
        
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
        """Filter out duplicate leads (global check + within batch)"""
        existing_phones = cls.get_existing_phones(user_id)
        existing_emails = cls.get_existing_emails(user_id)
        
        unique_leads = []
        new_phones = set()
        new_emails = set()
        
        for lead in leads:
            phone = lead.get("phone", "")
            if phone:
                phone = cls._normalize_phone(phone)
                lead["phone"] = phone
            
            email = (lead.get("email", "") or "").lower().strip()
            
            if phone:
                if phone in existing_phones or phone in new_phones:
                    print(f"⚠️ Duplicate phone skipped: {phone}")
                    continue
                new_phones.add(phone)
            elif email:
                if email in existing_emails or email in new_emails:
                    print(f"⚠️ Duplicate email skipped: {email}")
                    continue
                new_emails.add(email)
            else:
                continue
            
            unique_leads.append(lead)
        
        print(f"✅ Filtered: {len(leads)} → {len(unique_leads)} unique leads")
        return unique_leads
    
    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Normalize phone number for comparison"""
        import re
        phone = re.sub(r'[\s\-\.\(\)]', '', str(phone))
        if phone.startswith('+2'):
            phone = phone[2:]
        elif phone.startswith('002'):
            phone = phone[3:]
        return phone
