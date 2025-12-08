"""
Unified Chat Service
AI-powered chat that controls ALL system features
Admin chat = full control | User chat = user features
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import re


class UnifiedChatService:
    """AI chat that understands and executes ANY system action"""
    
    ADMIN_ACTIONS = {
        "add_tokens": {
            "patterns": ["اضف توكنز", "زود رصيد", "add tokens", "اعطي توكنز", "هات توكنز"],
            "description": "إضافة توكنز لمستخدم"
        },
        "delete_user": {
            "patterns": ["احذف يوزر", "امسح يوزر", "delete user", "شيل يوزر", "احذف مستخدم"],
            "description": "حذف مستخدم"
        },
        "list_users": {
            "patterns": ["قائمة اليوزرز", "المستخدمين", "اعرض اليوزرز", "list users", "كل اليوزرز"],
            "description": "عرض قائمة المستخدمين"
        },
        "set_password": {
            "patterns": ["غير باسورد", "عين باسورد", "set password", "كلمة سر"],
            "description": "تعيين كلمة مرور لمستخدم"
        },
        "view_stats": {
            "patterns": ["الإحصائيات", "الاحصائيات", "stats", "أرقام", "تقرير"],
            "description": "عرض إحصائيات النظام"
        },
        "make_admin": {
            "patterns": ["اجعله أدمن", "خليه ادمن", "make admin", "صلاحيات ادمن"],
            "description": "منح صلاحيات أدمن"
        }
    }
    
    USER_ACTIONS = {
        "hunt_leads": {
            "patterns": ["اصطاد", "صيد", "عملاء", "زباين", "جيبلي", "هاتلي", "دورلي", "ابحث", "leads"],
            "description": "البحث عن عملاء جدد"
        },
        "add_lead": {
            "patterns": ["اضف عميل", "سجل عميل", "add lead", "عميل جديد", "زود عميل"],
            "description": "إضافة عميل يدوياً"
        },
        "list_leads": {
            "patterns": ["عملائي", "قائمة العملاء", "اعرض العملاء", "my leads", "list leads"],
            "description": "عرض قائمة العملاء"
        },
        "share_lead": {
            "patterns": ["شارك عميل", "وزع عميل", "share lead", "ابعت عميل"],
            "description": "مشاركة عميل مع مستخدم آخر"
        },
        "view_stats": {
            "patterns": ["إحصائياتي", "احصائياتي", "رصيدي", "my stats", "حالتي"],
            "description": "عرض إحصائياتك"
        },
        "change_password": {
            "patterns": ["غير الباسورد", "غير كلمة السر", "change password", "باسورد جديد"],
            "description": "تغيير كلمة المرور"
        },
        "export_leads": {
            "patterns": ["صدر العملاء", "export leads", "نزل العملاء", "حفظ العملاء"],
            "description": "تصدير العملاء"
        }
    }
    
    SYSTEM_PROMPT = """أنت مساعد ذكي متكامل لنظام Hunter Pro CRM.
تستطيع فهم وتنفيذ أي أمر في النظام من خلال المحادثة.

{role_context}

عند فهم طلب المستخدم، حدد:
1. نوع الإجراء المطلوب
2. البيانات اللازمة
3. نفذ الإجراء أو اطلب معلومات إضافية

أجب بالعامية المصرية بشكل مختصر ومباشر.
إذا لم تفهم، اسأل للتوضيح."""
    
    _sessions: Dict[str, Dict] = {}
    
    @classmethod
    def get_session(cls, user_id: str) -> Dict:
        """Get or create session for user"""
        if user_id not in cls._sessions:
            cls._sessions[user_id] = {
                "context": {},
                "pending_action": None,
                "pending_data": {},
                "history": []
            }
        return cls._sessions[user_id]
    
    @classmethod
    def detect_action(cls, message: str, is_admin: bool) -> Tuple[Optional[str], Optional[Dict]]:
        """Detect which action user wants to perform"""
        message_lower = message.lower().strip()
        
        if is_admin:
            for action, config in cls.ADMIN_ACTIONS.items():
                for pattern in config["patterns"]:
                    if pattern in message_lower:
                        return action, config
        
        for action, config in cls.USER_ACTIONS.items():
            for pattern in config["patterns"]:
                if pattern in message_lower:
                    return action, config
        
        return None, None
    
    @classmethod
    async def process_message(cls, user_id: str, message: str, is_admin: bool = False) -> Dict:
        """Process message and execute appropriate action"""
        from app.services.user_service import UserService
        from app.services.lead_service import LeadService
        from app.services.ai_service import AIService
        from app.services.search_service import SearchService
        from app.core.config import settings
        
        session = cls.get_session(user_id)
        message = message.strip()
        
        action, config = cls.detect_action(message, is_admin)
        
        if session.get("pending_action"):
            if action and action != session.get("pending_action"):
                session["pending_action"] = None
                session["pending_data"] = {}
            else:
                return await cls._handle_pending_action(user_id, message, is_admin, session)
        
        if action == "add_tokens" and is_admin:
            session["pending_action"] = "add_tokens"
            session["pending_data"] = {}
            return {
                "response": "💰 **إضافة توكنز**\n\nاكتب اسم المستخدم والمبلغ\nمثال: `احمد 100`",
                "action": "add_tokens",
                "needs_input": True
            }
        
        elif action == "delete_user" and is_admin:
            session["pending_action"] = "delete_user"
            return {
                "response": "🗑️ **حذف مستخدم**\n\nاكتب اسم المستخدم المراد حذفه:",
                "action": "delete_user",
                "needs_input": True
            }
        
        elif action == "list_users" and is_admin:
            users = UserService.get_all_users()
            if users:
                text = "👥 **قائمة المستخدمين:**\n\n"
                for i, u in enumerate(users[:20], 1):
                    admin_badge = "👑" if u.get("is_admin") else ""
                    text += f"{i}. **{u.get('username', u.get('user_id', 'N/A'))}** {admin_badge}\n"
                    text += f"   💰 {u.get('wallet_balance', 0)} توكن\n"
                if len(users) > 20:
                    text += f"\n... و {len(users) - 20} مستخدم آخر"
                return {"response": text, "action": "list_users", "data": users}
            return {"response": "لا يوجد مستخدمين حالياً", "action": "list_users"}
        
        elif action == "set_password" and is_admin:
            session["pending_action"] = "set_password"
            return {
                "response": "🔐 **تعيين كلمة مرور**\n\nاكتب اسم المستخدم وكلمة المرور الجديدة\nمثال: `احمد 1234`",
                "action": "set_password",
                "needs_input": True
            }
        
        elif action == "make_admin" and is_admin:
            session["pending_action"] = "make_admin"
            return {
                "response": "👑 **منح صلاحيات أدمن**\n\nاكتب اسم المستخدم:",
                "action": "make_admin",
                "needs_input": True
            }
        
        elif action == "hunt_leads":
            business_match = cls._extract_business_from_message(message)
            if business_match:
                session["pending_action"] = "hunt_leads"
                session["pending_data"] = {"step": "location", "business": business_match}
                return {
                    "response": f"🎯 **تمام! فهمت إنك {business_match}**\n\n📍 إيه المنطقة/المدينة اللي عايز عملاء فيها؟",
                    "action": "hunt_leads",
                    "needs_input": True
                }
            
            session["pending_action"] = "hunt_leads"
            session["pending_data"] = {"step": "business"}
            return {
                "response": "🎯 **صيد العملاء**\n\nقولي إنت شغال إيه؟\n\n💡 مثال: دكتور أسنان، محامي، مهندس، مطعم، صالون...",
                "action": "hunt_leads",
                "needs_input": True
            }
        
        elif action == "add_lead":
            session["pending_action"] = "add_lead"
            session["pending_data"] = {"step": "name"}
            return {
                "response": "➕ **إضافة عميل جديد**\n\nاكتب اسم العميل:",
                "action": "add_lead",
                "needs_input": True
            }
        
        elif action == "list_leads":
            leads = LeadService.get_user_leads(user_id)
            if leads:
                text = f"📋 **عملائك ({len(leads)}):**\n\n"
                for i, lead in enumerate(leads[:15], 1):
                    text += f"{i}. **{lead.get('name', 'بدون اسم')[:30]}**\n"
                    if lead.get('phone') or lead.get('phone_number'):
                        text += f"   📱 {lead.get('phone') or lead.get('phone_number')}\n"
                if len(leads) > 15:
                    text += f"\n... و {len(leads) - 15} عميل آخر"
                return {"response": text, "action": "list_leads", "data": leads}
            return {"response": "ما عندكش عملاء لسه. اكتب 'صيد' عشان نجيبلك عملاء!", "action": "list_leads"}
        
        elif action == "share_lead":
            session["pending_action"] = "share_lead"
            session["pending_data"] = {"step": "select"}
            leads = LeadService.get_user_leads(user_id)
            if leads:
                text = "🔗 **مشاركة عميل**\n\nاختار رقم العميل:\n\n"
                for i, lead in enumerate(leads[:10], 1):
                    text += f"{i}. {lead.get('name', 'بدون اسم')[:25]}\n"
                session["pending_data"]["leads"] = leads[:10]
                return {"response": text, "action": "share_lead", "needs_input": True}
            return {"response": "ما عندكش عملاء للمشاركة", "action": "share_lead"}
        
        elif action == "view_stats":
            user = UserService.get_or_create(user_id)
            lead_stats = LeadService.get_lead_stats(user_id)
            text = f"""📊 **إحصائياتك:**

💰 **الرصيد:** {user.get('wallet_balance', 0)} توكن
👥 **العملاء:** {lead_stats.get('total', 0)}
✅ **المغلقين:** {lead_stats.get('closed', 0)}
🔥 **الساخنين:** {lead_stats.get('hot', 0)}
🆕 **الجدد:** {lead_stats.get('new', 0)}"""
            return {"response": text, "action": "view_stats", "data": {"user": user, "leads": lead_stats}}
        
        elif action == "change_password":
            session["pending_action"] = "change_password"
            session["pending_data"] = {"step": "old"}
            return {
                "response": "🔐 **تغيير كلمة المرور**\n\nاكتب كلمة المرور الحالية\n(أو 'جديد' لو مفيش باسورد):",
                "action": "change_password",
                "needs_input": True
            }
        
        elif action == "export_leads":
            leads = LeadService.get_user_leads(user_id)
            return {
                "response": f"📥 **تصدير العملاء**\n\nتم تجهيز {len(leads)} عميل للتصدير.\nاضغط على زر التصدير في قسم العملاء.",
                "action": "export_leads",
                "data": leads
            }
        
        role_context = "أنت أدمن النظام. تستطيع إدارة كل شيء." if is_admin else "أنت مستخدم عادي. تستطيع إدارة عملائك."
        
        can_afford, balance = UserService.check_balance(user_id, settings.CHAT_COST)
        if not can_afford:
            return {
                "response": f"رصيدك غير كافي ({balance} توكن). محتاج {settings.CHAT_COST} توكن للشات.",
                "error": True
            }
        
        system = cls.SYSTEM_PROMPT.format(role_context=role_context)
        response = AIService.generate(message, system, use_cache=False)
        UserService.deduct_balance(user_id, settings.CHAT_COST)
        
        return {
            "response": response,
            "tokens_used": settings.CHAT_COST,
            "remaining_balance": UserService.get_or_create(user_id).get("wallet_balance", 0)
        }
    
    @classmethod
    async def _handle_pending_action(cls, user_id: str, message: str, is_admin: bool, session: Dict) -> Dict:
        """Handle pending action with user input"""
        from app.services.user_service import UserService
        from app.services.lead_service import LeadService
        from app.services.search_service import SearchService
        from app.services.ai_service import AIService
        from app.core.config import settings
        
        action = session["pending_action"]
        data = session.get("pending_data", {})
        
        if message.lower() in ["الغاء", "cancel", "لا", "خروج"]:
            session["pending_action"] = None
            session["pending_data"] = {}
            return {"response": "✅ تم الإلغاء", "cancelled": True}
        
        if action == "add_tokens":
            parts = message.split()
            if len(parts) >= 2:
                username = parts[0]
                try:
                    amount = int(parts[1])
                    success = UserService.add_balance(username, amount)
                    session["pending_action"] = None
                    if success:
                        return {"response": f"✅ تم إضافة {amount} توكن لـ {username}", "success": True}
                    return {"response": f"❌ فشل - المستخدم {username} غير موجود", "error": True}
                except:
                    pass
            return {"response": "❌ صيغة خاطئة. اكتب: `اسم_المستخدم المبلغ`\nمثال: `ahmed 100`"}
        
        elif action == "delete_user":
            username = message.strip()
            success = UserService.delete_user(username)
            session["pending_action"] = None
            if success:
                return {"response": f"✅ تم حذف المستخدم {username}", "success": True}
            return {"response": f"❌ فشل في حذف {username}", "error": True}
        
        elif action == "set_password":
            parts = message.split()
            if len(parts) >= 2:
                username = parts[0]
                password = parts[1]
                success = UserService.set_password(username, password)
                session["pending_action"] = None
                if success:
                    return {"response": f"✅ تم تعيين كلمة مرور {username}", "success": True}
                return {"response": f"❌ فشل - تأكد من اسم المستخدم", "error": True}
            return {"response": "❌ اكتب: `اسم_المستخدم كلمة_المرور`"}
        
        elif action == "make_admin":
            username = message.strip()
            success = UserService.set_admin(username, True)
            session["pending_action"] = None
            if success:
                return {"response": f"✅ تم منح {username} صلاحيات أدمن 👑", "success": True}
            return {"response": f"❌ فشل - تأكد من اسم المستخدم", "error": True}
        
        elif action == "hunt_leads":
            step = data.get("step", "business")
            
            if step == "business":
                data["business"] = message
                data["step"] = "location"
                return {"response": "📍 **تمام!**\n\nإيه المنطقة/المدينة؟", "needs_input": True}
            
            elif step == "location":
                data["location"] = message
                data["step"] = "count"
                return {"response": "👥 **كام عميل محتاج؟**\n\nاكتب رقم (5 - 50)", "needs_input": True}
            
            elif step == "count":
                try:
                    count = int(re.sub(r'\D', '', message))
                    count = max(5, min(50, count))
                except:
                    count = 20
                data["count"] = count
                
                can_afford, balance = UserService.check_balance(user_id, settings.HUNT_COST)
                if not can_afford:
                    session["pending_action"] = None
                    session["pending_data"] = {}
                    return {"response": f"❌ رصيدك ({balance}) غير كافي. محتاج {settings.HUNT_COST} توكن", "error": True}
                
                business = data.get("business", "")
                location = data.get("location", "مصر")
                
                query = AIService.generate_golden_query(business, location)
                leads = SearchService.hunt_leads(business, location, count)
                
                from app.services.smart_hunt_service import DuplicateChecker
                leads = DuplicateChecker.filter_duplicates(user_id, leads)
                
                session["pending_action"] = None
                session["pending_data"] = {}
                
                if leads:
                    LeadService.add_leads_batch(user_id, leads)
                    UserService.deduct_balance(user_id, settings.HUNT_COST)
                    
                    text = f"🎯 **تم! لقيتلك {len(leads)} عميل في {location}**\n\n"
                    for i, lead in enumerate(leads[:8], 1):
                        text += f"**{i}. {lead.get('name', 'عميل')[:35]}**\n"
                        if lead.get('phone'):
                            text += f"📱 {lead.get('phone')}\n"
                    if len(leads) > 8:
                        text += f"\n... و {len(leads) - 8} تاني\n"
                    text += f"\n✅ محفوظين في عملائك\n💰 تم خصم {settings.HUNT_COST} توكن"
                    
                    user = UserService.get_or_create(user_id)
                    return {
                        "response": text,
                        "leads": leads,
                        "tokens_used": settings.HUNT_COST,
                        "remaining_balance": user.get("wallet_balance", 0)
                    }
                return {"response": "😔 مالقيتش عملاء. جرب منطقة تانية أو مجال مختلف.", "tokens_used": 0}
        
        elif action == "add_lead":
            step = data.get("step", "name")
            
            if step == "name":
                data["name"] = message
                data["step"] = "phone"
                return {"response": "📱 **اكتب رقم الموبايل:**", "needs_input": True}
            
            elif step == "phone":
                data["phone"] = message
                data["step"] = "done"
                
                lead_data = {
                    "name": data.get("name", ""),
                    "phone": data.get("phone", ""),
                    "status": "new",
                    "source": "manual"
                }
                LeadService.add_lead(user_id, lead_data)
                
                session["pending_action"] = None
                session["pending_data"] = {}
                return {"response": f"✅ تم إضافة العميل **{data.get('name')}**", "success": True}
        
        elif action == "share_lead":
            step = data.get("step", "select")
            
            if step == "select":
                try:
                    idx = int(message) - 1
                    leads = data.get("leads", [])
                    if 0 <= idx < len(leads):
                        data["selected_lead"] = leads[idx]
                        data["step"] = "recipient"
                        return {"response": "👤 **اكتب اسم المستخدم اللي عايز تشاركه معاه:**", "needs_input": True}
                except:
                    pass
                return {"response": "❌ اختار رقم صحيح من القائمة", "needs_input": True}
            
            elif step == "recipient":
                recipient = message.strip()
                lead = data.get("selected_lead", {})
                lead_id = lead.get("id", lead.get("lead_id", ""))
                
                success = LeadService.share_lead(user_id, recipient, str(lead_id))
                session["pending_action"] = None
                session["pending_data"] = {}
                
                if success:
                    return {"response": f"✅ تم مشاركة العميل مع {recipient}", "success": True}
                return {"response": "❌ فشل في المشاركة. تأكد من اسم المستخدم", "error": True}
        
        elif action == "change_password":
            step = data.get("step", "old")
            
            if step == "old":
                data["old_password"] = message if message.lower() != "جديد" else ""
                data["step"] = "new"
                return {"response": "🔐 **اكتب كلمة المرور الجديدة:**", "needs_input": True}
            
            elif step == "new":
                new_password = message
                old_password = data.get("old_password", "")
                
                if old_password:
                    success, msg = UserService.change_password(user_id, old_password, new_password)
                else:
                    success = UserService.set_password(user_id, new_password)
                    msg = "تم تعيين كلمة المرور" if success else "فشل"
                
                session["pending_action"] = None
                session["pending_data"] = {}
                
                if success:
                    return {"response": "✅ تم تغيير كلمة المرور بنجاح", "success": True}
                return {"response": f"❌ {msg}", "error": True}
        
        session["pending_action"] = None
        session["pending_data"] = {}
        return {"response": "حصل خطأ. حاول تاني.", "error": True}
    
    @classmethod
    def _extract_business_from_message(cls, message: str) -> Optional[str]:
        """Extract business/profession from user message"""
        import re
        
        specific_patterns = [
            r"مركز\s+صيانة\s+تكييفات",
            r"مركز\s+صيانة\s+تكيفات", 
            r"صيانة\s+تكييفات",
            r"صيانة\s+تكيفات",
            r"مركز\s+صيانة\s+\w+",
            r"شركة\s+صيانة\s+\w+",
        ]
        
        for pattern in specific_patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(0).strip()
        
        profession_patterns = [
            (r"(دكتور|طبيب)\s*(أسنان|عيون|جلدية|أطفال|باطنة|قلب|عظام|مخ|نسا)", 2),
            (r"(دكتور|طبيب)\s+(\w+)", 2),
            (r"(محامي|مهندس|محاسب|مدرس|صيدلي)", 1),
        ]
        
        for pattern, groups in profession_patterns:
            match = re.search(pattern, message)
            if match:
                if groups == 2 and match.lastindex >= 2:
                    return f"{match.group(1)} {match.group(2)}".strip()
                return match.group(1).strip()
        
        business_patterns = [
            (r"(عيادة|مكتب|محل|مطعم|صالون|شركة|مركز|كافيه|جيم|صيدلية)\s+(\w+)\s*(\w*)", 3),
        ]
        
        for pattern, groups in business_patterns:
            match = re.search(pattern, message)
            if match:
                parts = [match.group(1)]
                if match.group(2):
                    parts.append(match.group(2))
                if groups >= 3 and match.lastindex >= 3 and match.group(3):
                    parts.append(match.group(3))
                return " ".join(parts).strip()
        
        simple_keywords = [
            "دكتور", "طبيب", "محامي", "مهندس", "محاسب", "مدرس", "صيدلي",
            "عيادة", "مكتب", "محل", "مطعم", "صالون", "شركة", "مركز",
            "كافيه", "جيم", "نادي", "مستشفى", "صيدلية"
        ]
        
        for keyword in simple_keywords:
            if keyword in message:
                return keyword
        
        return None
    
    @classmethod
    def get_available_commands(cls, is_admin: bool) -> Dict:
        """Get available commands for user role"""
        commands = {"user": [], "admin": []}
        
        for action, config in cls.USER_ACTIONS.items():
            commands["user"].append({
                "action": action,
                "keywords": config["patterns"][:2],
                "description": config["description"]
            })
        
        if is_admin:
            for action, config in cls.ADMIN_ACTIONS.items():
                commands["admin"].append({
                    "action": action,
                    "keywords": config["patterns"][:2],
                    "description": config["description"]
                })
        
        return commands
