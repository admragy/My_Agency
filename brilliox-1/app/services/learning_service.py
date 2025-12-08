"""
Self-Learning AI Service
Learns from successful conversations to improve responses
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import re
from app.core.database import DB_TYPE, pg_conn, LOCAL_DB


class LearningService:
    """AI Self-Learning Service"""
    
    BAIT_TEMPLATES = {
        "curiosity": {
            "ar": "هل سمعت عن الفرصة الجديدة في {location}؟ 🏠",
            "templates": [
                "هل سمعت عن الفرصة الجديدة في {location}؟",
                "عندي حاجة مهمة جداً لازم تعرفها...",
                "شوف اللي حصل النهارده في السوق العقاري 👀"
            ]
        },
        "problem": {
            "ar": "هل بتواجه مشكلة في إيجاد {property_type} مناسب؟",
            "templates": [
                "هل بتواجه صعوبة في إيجاد شقة بسعر معقول؟",
                "زهقت من البحث عن عقار كويس؟",
                "المشكلة اللي الكل بيشتكي منها في العقارات..."
            ]
        },
        "urgency": {
            "ar": "آخر فرصة! العرض ينتهي خلال {hours} ساعات فقط ⏰",
            "templates": [
                "آخر 3 وحدات متبقية بالسعر ده!",
                "العرض ينتهي بكرة - لازم تتحرك دلوقتي",
                "الأسعار هتزيد الأسبوع الجاي 📈"
            ]
        },
        "social_proof": {
            "ar": "أكثر من {count} عميل اختاروا نفس المشروع هذا الشهر",
            "templates": [
                "50+ عميل حجزوا الشهر ده في نفس المشروع",
                "كل اللي شافوا المكان ده اتبهروا",
                "العملاء بيرجعوا يحجزوا وحدة تانية 🔄"
            ]
        },
        "question": {
            "ar": "إيه اللي بتدور عليه في {property_type}؟",
            "templates": [
                "إيه أهم حاجة بتدور عليها في الشقة؟",
                "عايز استثمار ولا سكن؟",
                "إيه الميزانية اللي ناوي عليها؟ 💰"
            ]
        },
        "value": {
            "ar": "احصل على {benefit} مجاناً مع أي حجز هذا الأسبوع",
            "templates": [
                "تشطيب كامل هدية مع الحجز 🎁",
                "أقساط بدون فوائد لمدة 10 سنين",
                "مقدم 10% فقط والباقي على 7 سنين"
            ]
        }
    }
    
    FUNNEL_STAGES = [
        {"id": "new", "name": "جديد", "order": 0},
        {"id": "bait_sent", "name": "تم إرسال الطعم", "order": 1},
        {"id": "replied", "name": "رد", "order": 2},
        {"id": "interested", "name": "مهتم", "order": 3},
        {"id": "negotiating", "name": "في التفاوض", "order": 4},
        {"id": "hot", "name": "ساخن", "order": 5},
        {"id": "closed", "name": "تم البيع", "order": 6},
        {"id": "lost", "name": "خسارة", "order": -1}
    ]
    
    @staticmethod
    def get_bait_templates() -> Dict:
        """Get all bait message templates"""
        return LearningService.BAIT_TEMPLATES
    
    @staticmethod
    def get_funnel_stages() -> List[Dict]:
        """Get all funnel stages"""
        return LearningService.FUNNEL_STAGES
    
    @staticmethod
    def generate_bait_message(template_type: str, variables: Dict = None) -> str:
        """Generate a bait message from template"""
        if template_type not in LearningService.BAIT_TEMPLATES:
            template_type = "curiosity"
        
        templates = LearningService.BAIT_TEMPLATES[template_type]["templates"]
        import random
        template = random.choice(templates)
        
        if variables:
            for key, value in variables.items():
                template = template.replace(f"{{{key}}}", str(value))
        
        return template
    
    @staticmethod
    def save_pattern(user_id: str, pattern_data: Dict) -> bool:
        """Save a learned pattern to database"""
        if DB_TYPE == "replit_pg" and pg_conn:
            try:
                cur = pg_conn.cursor()
                cur.execute("""
                    INSERT INTO ai_patterns (user_id, pattern_type, trigger_text, response_text, stage, confidence)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    user_id,
                    pattern_data.get("type", "reply"),
                    pattern_data.get("trigger", ""),
                    pattern_data.get("response", ""),
                    pattern_data.get("stage", "interested"),
                    pattern_data.get("confidence", 0.5)
                ))
                pg_conn.commit()
                cur.close()
                return True
            except Exception as e:
                print(f"Save pattern error: {e}")
                return False
        
        LOCAL_DB.setdefault("ai_patterns", []).append({
            "user_id": user_id,
            **pattern_data,
            "created_at": datetime.now().isoformat()
        })
        return True
    
    @staticmethod
    def get_patterns(user_id: str, stage: str = None) -> List[Dict]:
        """Get learned patterns for user"""
        if DB_TYPE == "replit_pg" and pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = pg_conn.cursor(cursor_factory=RealDictCursor)
                
                if stage:
                    cur.execute("""
                        SELECT * FROM ai_patterns 
                        WHERE user_id = %s AND stage = %s
                        ORDER BY confidence DESC, success_count DESC
                    """, (user_id, stage))
                else:
                    cur.execute("""
                        SELECT * FROM ai_patterns 
                        WHERE user_id = %s
                        ORDER BY confidence DESC, success_count DESC
                    """, (user_id,))
                
                patterns = [dict(row) for row in cur.fetchall()]
                cur.close()
                return patterns
            except Exception as e:
                print(f"Get patterns error: {e}")
                return []
        
        patterns = LOCAL_DB.get("ai_patterns", [])
        filtered = [p for p in patterns if p.get("user_id") == user_id]
        if stage:
            filtered = [p for p in filtered if p.get("stage") == stage]
        return filtered
    
    @staticmethod
    def update_pattern_success(pattern_id: int, is_success: bool) -> bool:
        """Update pattern success/fail count"""
        if DB_TYPE == "replit_pg" and pg_conn:
            try:
                cur = pg_conn.cursor()
                if is_success:
                    cur.execute("""
                        UPDATE ai_patterns 
                        SET success_count = success_count + 1,
                            confidence = (success_count + 1.0) / (success_count + fail_count + 1.0),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (pattern_id,))
                else:
                    cur.execute("""
                        UPDATE ai_patterns 
                        SET fail_count = fail_count + 1,
                            confidence = success_count / (success_count + fail_count + 1.0),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (pattern_id,))
                pg_conn.commit()
                cur.close()
                return True
            except Exception as e:
                print(f"Update pattern error: {e}")
                return False
        return False
    
    @staticmethod
    def import_conversation(user_id: str, platform: str, messages: List[Dict], rating: int) -> Dict:
        """Import and analyze a conversation"""
        patterns_found = []
        
        for i, msg in enumerate(messages):
            if msg.get("is_mine") and i > 0:
                prev_msg = messages[i-1]
                if not prev_msg.get("is_mine"):
                    pattern = {
                        "type": "reply",
                        "trigger": prev_msg.get("text", "")[:200],
                        "response": msg.get("text", "")[:500],
                        "stage": LearningService._detect_stage(prev_msg.get("text", "")),
                        "confidence": min(0.3 + (rating * 0.1), 0.9)
                    }
                    patterns_found.append(pattern)
                    LearningService.save_pattern(user_id, pattern)
        
        if DB_TYPE == "replit_pg" and pg_conn:
            try:
                cur = pg_conn.cursor()
                cur.execute("""
                    INSERT INTO conversation_imports (user_id, platform, conversation_data, rating, is_successful, patterns_extracted)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    platform,
                    json.dumps(messages, ensure_ascii=False),
                    rating,
                    rating >= 4,
                    len(patterns_found)
                ))
                pg_conn.commit()
                cur.close()
            except Exception as e:
                print(f"Import conversation error: {e}")
        
        return {
            "patterns_found": len(patterns_found),
            "is_successful": rating >= 4
        }
    
    @staticmethod
    def _detect_stage(text: str) -> str:
        """Detect conversation stage from text"""
        text_lower = text.lower() if text else ""
        
        if any(w in text_lower for w in ["سعر", "كام", "ثمن", "تكلفة", "مبلغ"]):
            return "interested"
        if any(w in text_lower for w in ["موافق", "تمام", "أوكي", "ماشي", "حاضر"]):
            return "negotiating"
        if any(w in text_lower for w in ["مش مهتم", "لا شكرا", "مش عايز"]):
            return "lost"
        if any(w in text_lower for w in ["هحجز", "خلاص", "اتفقنا", "done", "تم"]):
            return "closed"
        if any(w in text_lower for w in ["طيب", "خلينا نشوف", "ممكن", "عايز اعرف"]):
            return "replied"
        
        return "bait_sent"
    
    @staticmethod
    def generate_smart_reply(user_id: str, customer_message: str, stage: str) -> str:
        """Generate a smart reply based on learned patterns"""
        patterns = LearningService.get_patterns(user_id, stage)
        
        if patterns:
            import random
            best_patterns = [p for p in patterns if p.get("confidence", 0) > 0.5]
            if best_patterns:
                pattern = random.choice(best_patterns[:5])
                return pattern.get("response_text", "")
        
        default_replies = {
            "new": "أهلاً بيك! 👋 إزيك؟ عندي عرض مميز جداً ممكن يعجبك...",
            "bait_sent": "تمام، أنا تحت أمرك. إيه اللي تحب تعرفه أكتر؟",
            "replied": "جميل جداً! 😊 خليني أوضحلك التفاصيل...",
            "interested": "ممتاز! 🔥 ده فعلاً أحسن وقت للحجز. عايز أبعتلك الكتالوج؟",
            "negotiating": "طبعاً نقدر نتفاهم. إيه اللي يناسبك بالظبط؟",
            "hot": "خلاص كده! 🎉 أمتى نقدر نعمل المعاينة؟",
            "closed": "مبروك عليك! 🎊 هتستمتع جداً.",
            "lost": "تمام، لو احتجت أي حاجة في المستقبل أنا موجود."
        }
        
        return default_replies.get(stage, default_replies["replied"])
    
    @staticmethod
    def get_learning_stats(user_id: str) -> Dict:
        """Get learning statistics for user"""
        patterns = LearningService.get_patterns(user_id)
        
        total_patterns = len(patterns)
        avg_confidence = sum(p.get("confidence", 0) for p in patterns) / max(total_patterns, 1)
        
        stage_counts = {}
        for p in patterns:
            stage = p.get("stage", "unknown")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
        
        conversations_imported = 0
        if DB_TYPE == "replit_pg" and pg_conn:
            try:
                cur = pg_conn.cursor()
                cur.execute("SELECT COUNT(*) FROM conversation_imports WHERE user_id = %s", (user_id,))
                result = cur.fetchone()
                conversations_imported = result[0] if result else 0
                cur.close()
            except:
                pass
        
        return {
            "total_patterns": total_patterns,
            "avg_confidence": round(avg_confidence * 100, 1),
            "patterns_by_stage": stage_counts,
            "conversations_imported": conversations_imported,
            "improvement_level": "مبتدئ" if total_patterns < 10 else "متوسط" if total_patterns < 50 else "متقدم"
        }
