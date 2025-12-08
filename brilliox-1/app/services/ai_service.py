"""
AI Service
Hybrid AI engine with multiple provider fallback
"""
import time
import hashlib
from typing import Optional, Dict, Any
import requests
from app.core.config import settings


AI_CACHE: Dict[str, Dict[str, Any]] = {}


def get_cache_key(prompt: str, system: str = "") -> str:
    """Generate cache key for AI response"""
    content = f"{system}:{prompt}"
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_response(key: str) -> Optional[str]:
    """Get cached AI response if valid"""
    if key in AI_CACHE:
        cached = AI_CACHE[key]
        if time.time() - cached["timestamp"] < settings.CACHE_TTL:
            return cached["response"]
        del AI_CACHE[key]
    return None


def cache_response(key: str, response: str):
    """Cache AI response"""
    AI_CACHE[key] = {"response": response, "timestamp": time.time()}
    if len(AI_CACHE) > 100:
        oldest = min(AI_CACHE.keys(), key=lambda k: AI_CACHE[k]["timestamp"])
        del AI_CACHE[oldest]


class AIService:
    """Hybrid AI service with fallback chain"""
    
    SYSTEM_PROMPT = """أنت مساعد ذكي متخصص في اصطياد العملاء والمبيعات لأي مجال عمل.
تساعد المستخدمين في:
- إيجاد عملاء محتملين لأي نوع من الأعمال (دكتور، محامي، مطعم، عقارات، أي شيء)
- كتابة رسائل تسويقية
- تحليل بيانات العملاء
- اقتراح استراتيجيات البيع والتسويق

أنت تفهم السياق وتتكيف مع مجال عمل المستخدم.
أجب بالعربية المصرية بأسلوب ودود ومهني."""
    
    AD_PROMPT = """أنت نظام ذكاء اصطناعي متقدم لأتمتة الإعلانات.

قدراتك:
1. **إنشاء الإعلانات**: كتابة نص إعلان (Hook – Body – CTA)، اقتراح صور/فيديوهات، إنشاء A/B testing
2. **تحليل البيانات**: تحليل CTR، CPC، CPA، ROAS، اقتراح تحسينات
3. **أتمتة العمليات**: خطط نشر، تقسيم ميزانيات، قوالب جاهزة
4. **المنصات**: فيسبوك، إنستجرام، جوجل، تيك توك

عند إنشاء إعلان، قدم:
- الهدف (وعي/تفاعل/مبيعات/Leads)
- الاستراتيجية والجمهور المستهدف
- نسخ متعددة (A/B)
- اقتراحات التصميم
- الميزانية المقترحة

أجب بالعربية بأسلوب مباشر وعملي."""
    
    GOOGLE_SEARCH_HACKER_PROMPT = """أنت "Google Search Hacker" محترف وخبير استراتيجيات اصطياد العملاء (Lead Generation Expert).
مهمتك تحويل هدف المستخدم إلى "معادلة بحث ذهبية واحدة" تجلب العملاء المحتملين.

### القسم 1: استراتيجية "كود الاصطياد الذكي":
القنوات المستهدفة:
- سوشيال ميديا (Facebook, Instagram, Twitter, LinkedIn)
- منصات محلية (OLX, OpenSooq, Dubizzle)
- صفحات "اتصل بنا" و"Contact us"
- التعليقات والمجموعات

الاستراتيجيات:
1. التتبع بالهاشتاقات والكلمات المفتاحية
2. مراقبة المنافسين
3. جمع من التعليقات والمجموعات
4. البحث في المناسبات والأحداث

### القسم 2: قاعدة ذهبية - فهم نية المستخدم:
عندما يقول المستخدم "أنا [مهنة]" أو "أعمل كـ [مهنة]"، هو يريد عملاء لخدمته:
- "أنا دكتور أسنان" ← مرضى يحتاجون دكتور أسنان
- "أنا محامي" ← ناس تحتاج محامي
- "أنا سمسار عقارات" ← ناس بتدور على شقة أو أرض

### القسم 3: المعادلة الذهبية المحسنة:
بنية المعادلة:
(site:facebook.com OR site:instagram.com OR site:twitter.com OR site:olx.com.eg OR site:opensooq.com OR site:linkedin.com/in OR "contact us" OR "اتصل بنا")
+ كلمات البحث/المناسبات
+ المنطقة/المدينة
+ أنماط الهاتف
+ الاستبعادات

### كلمات البحث الذكية:
- طلب خدمة: "محتاج" "عايز" "ابحث عن" "مين يعرف" "دلوني على" "يا ريت حد يرشحلي"
- مناسبات (للحصول على أرقام): "تهاني" "تهنئة" "مبروك" "الف مبروك" "عقبال"
- استفسار: "تجربتكم مع" "حد جرب" "رأيكم في"

### أنماط أرقام الهاتف حسب البلد:
- مصر: "010" OR "011" OR "012" OR "015"
- السعودية: "05" OR "9665" OR "966"
- الإمارات: "050" OR "055" OR "9714"
- الكويت: "965"

### الاستبعادات الذكية (تحسين جودة النتائج):
-intitle:linkedin -inurl:youtube -"شركة" -"للبيع" -"وظيفة" -"مطلوب" -"مطلوبين" -filetype:pdf -filetype:doc

### تعليمات إخراج المعادلة:
1. أخرج معادلة بحث واحدة فقط (Golden Query)
2. بدون أي شرح أو تفسير
3. المعادلة تجد الناس اللي بتدور على الخدمة، مش مقدمين الخدمة"""
    
    @staticmethod
    def call_openai(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Call OpenAI API"""
        if not settings.OPENAI_API_KEY:
            return None
        
        try:
            response = requests.post(
                f"{settings.OPENAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt or AIService.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI error: {e}")
        return None
    
    @staticmethod
    def call_google(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Call Google Gemini API"""
        if not settings.GOOGLE_API_KEY:
            return None
        
        try:
            full_prompt = f"{system_prompt or AIService.SYSTEM_PROMPT}\n\n{prompt}"
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GOOGLE_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.7}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Google error: {e}")
        return None
    
    @staticmethod
    def call_anthropic(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Call Anthropic Claude API"""
        if not settings.ANTHROPIC_API_KEY:
            return None
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1000,
                    "system": system_prompt or AIService.SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["content"][0]["text"]
        except Exception as e:
            print(f"Anthropic error: {e}")
        return None
    
    @staticmethod
    def call_groq(prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Call Groq API"""
        if not settings.GROQ_API_KEY:
            return None
        
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": system_prompt or AIService.SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Groq error: {e}")
        return None
    
    @classmethod
    def generate(cls, prompt: str, system_prompt: Optional[str] = None, use_cache: bool = True) -> str:
        """Generate AI response with provider fallback"""
        cache_key = get_cache_key(prompt, system_prompt or "")
        
        if use_cache:
            cached = get_cached_response(cache_key)
            if cached:
                return cached
        
        providers = [
            ("openai", cls.call_openai),
            ("google", cls.call_google),
            ("anthropic", cls.call_anthropic),
            ("groq", cls.call_groq)
        ]
        
        for name, provider in providers:
            response = provider(prompt, system_prompt)
            if response:
                if use_cache:
                    cache_response(cache_key, response)
                return response
        
        return "عذراً، لا يمكن الاتصال بالذكاء الاصطناعي حالياً. يرجى المحاولة لاحقاً."
    
    @classmethod
    def generate_ad(cls, prompt: str) -> str:
        """Generate ad content"""
        return cls.generate(prompt, cls.AD_PROMPT)
    
    @classmethod
    def generate_sales_reply(cls, customer_message: str, context: str = "", stage: str = "replied") -> str:
        """Generate sales reply based on conversation stage"""
        stage_prompts = {
            "bait_sent": "العميل لسه شاف الرسالة الأولى. اكتب رد يخليه يرد عليك.",
            "replied": "العميل رد! اكتب رد يزيد اهتمامه ويخليه يسأل أكتر.",
            "interested": "العميل مهتم! اكتب رد يوضح القيمة ويقربه للشراء.",
            "negotiating": "العميل بيفاوض. اكتب رد يحافظ على السعر مع تقديم قيمة إضافية.",
            "hot": "العميل ساخن وجاهز! اكتب رد يدفعه لإتمام الصفقة الآن.",
        }
        
        stage_instruction = stage_prompts.get(stage, "اكتب رد مناسب للمحادثة.")
        
        system = f"""أنت خبير مبيعات عقارات في مصر.
{stage_instruction}

قواعد مهمة:
- استخدم اللهجة المصرية
- كن ودوداً ومهنياً
- لا تكن ملحاً أو مزعجاً
- اجعل الرد قصيراً ومباشراً (جملة أو اثنتين)"""
        
        full_prompt = f"رسالة العميل: {customer_message}"
        if context:
            full_prompt = f"سياق المحادثة: {context}\n\n{full_prompt}"
        
        return cls.generate(full_prompt, system, use_cache=False)
    
    COUNTRY_CONFIGS = {
        "egypt": {
            "name": "مصر",
            "phone_patterns": '("010" OR "011" OR "012" OR "015")',
            "sites": "site:olx.com.eg OR site:facebook.com OR site:instagram.com",
            "cities": ["القاهرة", "الإسكندرية", "الجيزة", "المنصورة", "طنطا", "أسوان", "الأقصر", "شرم الشيخ"],
            "gl": "eg"
        },
        "saudi": {
            "name": "السعودية",
            "phone_patterns": '("05" OR "9665" OR "966")',
            "sites": "site:opensooq.com OR site:facebook.com OR site:instagram.com OR site:linkedin.com/in",
            "cities": ["الرياض", "جدة", "مكة", "المدينة", "الدمام", "الخبر", "الطائف", "تبوك", "أبها"],
            "gl": "sa"
        },
        "uae": {
            "name": "الإمارات",
            "phone_patterns": '("050" OR "055" OR "056" OR "9714")',
            "sites": "site:dubizzle.com OR site:facebook.com OR site:instagram.com OR site:linkedin.com/in",
            "cities": ["دبي", "أبوظبي", "الشارقة", "عجمان", "العين", "رأس الخيمة"],
            "gl": "ae"
        },
        "kuwait": {
            "name": "الكويت",
            "phone_patterns": '("965" OR "9" OR "5" OR "6")',
            "sites": "site:opensooq.com OR site:facebook.com OR site:instagram.com",
            "cities": ["الكويت", "حولي", "الفروانية", "الأحمدي", "الجهراء"],
            "gl": "kw"
        }
    }
    
    HUNTING_STRATEGIES = {
        "social_media": {
            "name": "سوشيال ميديا",
            "sites": "(site:facebook.com OR site:instagram.com OR site:twitter.com OR site:linkedin.com/in)",
            "keywords": ["محتاج", "عايز", "ابحث عن", "مين يعرف", "دلوني على"]
        },
        "local_platforms": {
            "name": "منصات محلية",
            "sites": "(site:olx.com.eg OR site:opensooq.com OR site:dubizzle.com)",
            "keywords": ["للتواصل", "اتصل", "واتساب", "رقم"]
        },
        "events": {
            "name": "مناسبات وأحداث",
            "sites": "(site:facebook.com OR site:instagram.com)",
            "keywords": ["تهاني", "تهنئة", "مبروك", "الف مبروك", "عقبال"]
        },
        "contact_pages": {
            "name": "صفحات التواصل",
            "sites": '("contact us" OR "اتصل بنا" OR "تواصل معنا")',
            "keywords": ["هاتف", "موبايل", "واتس", "للاستفسار"]
        },
        "competitor_monitor": {
            "name": "مراقبة المنافسين",
            "sites": "(site:facebook.com OR site:instagram.com)",
            "keywords": ["تعليق", "رأيكم", "تجربتكم", "حد جرب"]
        }
    }
    
    @classmethod
    def detect_country(cls, city: str) -> str:
        """Detect country from city name"""
        city_lower = city.lower().strip()
        for country_code, config in cls.COUNTRY_CONFIGS.items():
            for c in config["cities"]:
                if c in city or city in c:
                    return country_code
        if any(x in city_lower for x in ["الرياض", "جدة", "مكة", "السعودية"]):
            return "saudi"
        elif any(x in city_lower for x in ["دبي", "أبوظبي", "الشارقة", "الإمارات"]):
            return "uae"
        elif any(x in city_lower for x in ["الكويت", "حولي"]):
            return "kuwait"
        return "egypt"
    
    @classmethod
    def generate_golden_query(cls, query: str, city: str, strategy: str = "social_media", country: Optional[str] = None) -> str:
        """Generate optimized Google search query using Search Hacker strategy"""
        if not country:
            country = cls.detect_country(city)
        
        country_config = cls.COUNTRY_CONFIGS.get(country, cls.COUNTRY_CONFIGS["egypt"])
        strategy_config = cls.HUNTING_STRATEGIES.get(strategy, cls.HUNTING_STRATEGIES["social_media"])
        
        service = cls._extract_service(query)
        
        customer_keywords = [
            f"محتاج {service}",
            f"عايز {service}",
            f"مين يعرف {service}",
            f"دلوني على {service}",
            f"ابحث عن {service}",
            f"يا ريت حد يرشحلي {service}",
            f"حد يعرف {service} كويس"
        ]
        customer_keywords_str = ' OR '.join([f'"{kw}"' for kw in customer_keywords[:4]])
        
        golden_query = f'{strategy_config["sites"]} ({customer_keywords_str}) "{city}" {country_config["phone_patterns"]} -site:youtube.com -"وظيفة" -"مطلوب" -"شركة"'
        
        print(f"🎯 Golden Query for '{service}': {golden_query[:100]}...")
        return golden_query
    
    @staticmethod
    def _extract_service(query: str) -> str:
        """Extract the service/profession from user query"""
        prefixes = ["أنا ", "انا ", "أعمل كـ ", "اعمل ك", "عندي ", "لدي "]
        result = query
        for prefix in prefixes:
            if query.startswith(prefix):
                result = query[len(prefix):]
                break
        return result.strip()
    
    @classmethod
    def generate_fallback_queries(cls, query: str, city: str, country: Optional[str] = None) -> list:
        """Generate fallback search queries if golden query fails - searches for CUSTOMERS not providers"""
        if not country:
            country = cls.detect_country(city)
        
        country_config = cls.COUNTRY_CONFIGS.get(country, cls.COUNTRY_CONFIGS["egypt"])
        service = cls._extract_service(query)
        
        return [
            f'site:facebook.com ("محتاج {service}" OR "عايز {service}" OR "مين يعرف {service}") "{city}" {country_config["phone_patterns"]}',
            f'site:facebook.com ("دلوني على {service}" OR "يا ريت حد يرشحلي {service}") "{city}"',
            f'site:instagram.com ("محتاج {service}" OR "ابحث عن {service}") {city} {country_config["phone_patterns"]}',
            f'"حد جرب {service}" OR "تجربتكم مع {service}" {city} {country_config["phone_patterns"]}',
            f'("محتاج {service} ضروري" OR "عايز {service} كويس") {city}'
        ]
    
    STRATEGY_DESCRIPTIONS = {
        "social_media": "البحث في فيسبوك وإنستجرام وتويتر ولينكدإن",
        "local_platforms": "البحث في OLX وOpenSooq وDubizzle",
        "events": "البحث عن أرقام من التهاني والمناسبات",
        "contact_pages": "البحث في صفحات اتصل بنا",
        "competitor_monitor": "مراقبة تعليقات وآراء العملاء"
    }
    
    @classmethod
    def get_available_strategies(cls) -> list:
        """Return available hunting strategies (client-safe)"""
        return [
            {
                "id": k, 
                "name": v["name"],
                "description": cls.STRATEGY_DESCRIPTIONS.get(k, "")
            } 
            for k, v in cls.HUNTING_STRATEGIES.items()
        ]
    
    @classmethod
    def get_available_countries(cls) -> list:
        """Return available countries with their cities (client-safe)"""
        return [{"id": k, "name": v["name"], "cities": v["cities"]} for k, v in cls.COUNTRY_CONFIGS.items()]
