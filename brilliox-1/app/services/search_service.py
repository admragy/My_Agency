"""
Search Service
Enhanced hybrid search with Golden Query optimization for cost efficiency
"""
import re
from typing import List, Dict, Optional
import requests
from app.core.config import settings
from app.services.ai_service import AIService


class SearchService:
    """Enhanced hybrid search service"""
    
    @staticmethod
    def search_serper(query: str, max_results: int = 20) -> List[Dict]:
        """Search using Serper API"""
        if not settings.SERPER_API_KEY:
            return []
        
        try:
            response = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": settings.SERPER_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "gl": "eg",
                    "hl": "ar",
                    "num": max_results
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("organic", [])[:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "source": "serper"
                    })
                
                return results
        except Exception as e:
            print(f"Serper error: {e}")
        
        return []
    
    @staticmethod
    def search_duckduckgo(query: str, max_results: int = 20) -> List[Dict]:
        """Search using DuckDuckGo (fallback)"""
        try:
            response = requests.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_redirect": 1,
                    "no_html": 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get("RelatedTopics", [])[:max_results]:
                    if "Text" in item:
                        results.append({
                            "title": item.get("Text", "")[:100],
                            "link": item.get("FirstURL", ""),
                            "snippet": item.get("Text", ""),
                            "source": "duckduckgo"
                        })
                
                return results
        except Exception as e:
            print(f"DuckDuckGo error: {e}")
        
        return []
    
    @classmethod
    def search(cls, query: str, max_results: int = 20) -> List[Dict]:
        """Search with fallback chain"""
        results = cls.search_serper(query, max_results)
        
        if not results:
            results = cls.search_duckduckgo(query, max_results)
        
        return results
    
    PHONE_PATTERNS_BY_COUNTRY = {
        "egypt": [
            r'(?:\+?2)?01[0125]\d{8}',
            r'01[0125]\d{8}',
            r'01[0125][-\s]?\d{4}[-\s]?\d{4}',
            r'\+20\s?1[0125]\d{8}',
        ],
        "saudi": [
            r'(?:\+?966)?0?5[0-9]\d{7}',
            r'05[0-9]\d{7}',
            r'05[0-9][-\s]?\d{3}[-\s]?\d{4}',
            r'\+966\s?5[0-9]\d{7}',
            r'9665[0-9]\d{7}',
        ],
        "uae": [
            r'(?:\+?971)?0?5[0-9]\d{7}',
            r'05[0-9]\d{7}',
            r'\+971\s?5[0-9]\d{7}',
            r'9715[0-9]\d{7}',
        ],
        "kuwait": [
            r'(?:\+?965)?[569]\d{7}',
            r'[569]\d{7}',
            r'\+965\s?[569]\d{7}',
        ],
        "all": [
            r'(?:\+?2)?01[0125]\d{8}',
            r'01[0125]\d{8}',
            r'(?:\+?966)?0?5[0-9]\d{7}',
            r'05[0-9]\d{7}',
            r'(?:\+?971)?0?5[0-9]\d{7}',
            r'(?:\+?965)?[569]\d{7}',
        ]
    }
    
    CUSTOMER_INTENT_KEYWORDS = [
        "محتاج", "عايز", "ابحث عن", "مين يعرف", "دلوني على",
        "يا ريت حد", "حد يرشحلي", "حد يعرف", "تجربتكم مع", "حد جرب"
    ]
    
    @classmethod
    def extract_leads_from_results(cls, results: List[Dict], country: str = "all", include_no_phone: bool = True) -> List[Dict]:
        """Extract potential leads from search results - includes customers without phone if they show intent"""
        leads = []
        seen_phones = set()
        seen_urls = set()
        
        phone_patterns = cls.PHONE_PATTERNS_BY_COUNTRY.get(country, cls.PHONE_PATTERNS_BY_COUNTRY["all"])
        if country != "all":
            phone_patterns = phone_patterns + cls.PHONE_PATTERNS_BY_COUNTRY["all"]
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        
        for result in results:
            text = f"{result.get('title', '')} {result.get('snippet', '')}"
            url = result.get("link", "")
            
            phones = []
            for pattern in phone_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    clean_phone = re.sub(r'[\s\-]', '', match)
                    if len(clean_phone) >= 8 and clean_phone not in seen_phones:
                        phones.append(clean_phone)
                        seen_phones.add(clean_phone)
            
            emails = re.findall(email_pattern, text)
            
            has_customer_intent = any(kw in text for kw in cls.CUSTOMER_INTENT_KEYWORDS)
            
            should_include = phones or emails or (include_no_phone and has_customer_intent and url not in seen_urls)
            
            if should_include:
                name = result.get("title", "عميل محتمل")
                name = re.sub(r'\s*[-|–]\s*.*', '', name)[:60]
                
                detected_country = cls._detect_phone_country(phones[0]) if phones else country
                
                lead_type = "with_phone" if phones else ("with_email" if emails else "potential")
                
                leads.append({
                    "name": name,
                    "phone": phones[0] if phones else "",
                    "email": emails[0] if emails else "",
                    "source": url,
                    "notes": result.get("snippet", "")[:300],
                    "status": "new",
                    "country": detected_country,
                    "lead_type": lead_type
                })
                seen_urls.add(url)
        
        return leads
    
    @staticmethod
    def _detect_phone_country(phone: str) -> str:
        """Detect country from phone number format"""
        if not phone:
            return "unknown"
        
        clean = re.sub(r'[\s\-\+]', '', phone)
        
        if clean.startswith('20') or clean.startswith('01'):
            return "egypt"
        elif clean.startswith('966') or clean.startswith('05'):
            return "saudi"
        elif clean.startswith('971') or (clean.startswith('05') and len(clean) == 10):
            return "uae"
        elif clean.startswith('965'):
            return "kuwait"
        
        return "unknown"
    
    @classmethod
    def search_with_country(cls, query: str, country: str = "egypt", max_results: int = 20) -> List[Dict]:
        """Search with country-specific settings"""
        country_gl = {
            "egypt": "eg",
            "saudi": "sa", 
            "uae": "ae",
            "kuwait": "kw"
        }
        gl = country_gl.get(country, "eg")
        
        if settings.SERPER_API_KEY:
            try:
                response = requests.post(
                    "https://google.serper.dev/search",
                    headers={
                        "X-API-KEY": settings.SERPER_API_KEY,
                        "Content-Type": "application/json"
                    },
                    json={
                        "q": query,
                        "gl": gl,
                        "hl": "ar",
                        "num": max_results
                    },
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    for item in data.get("organic", [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "source": "serper"
                        })
                    return results
            except Exception as e:
                print(f"Serper error: {e}")
        
        return cls.search_duckduckgo(query, max_results)
    
    @classmethod
    def hunt_leads(cls, query: str, city: str = "القاهرة", max_results: int = 20, 
                   strategy: str = "social_media", country: Optional[str] = None) -> List[Dict]:
        """Hunt for leads using Golden Query optimization with multi-country and strategy support"""
        all_leads = []
        seen_phones = set()
        seen_emails = set()
        
        if not country:
            country = AIService.detect_country(city)
        
        country_config = AIService.COUNTRY_CONFIGS.get(country, AIService.COUNTRY_CONFIGS["egypt"])
        phone_patterns_map = {
            "egypt": '("010" OR "011" OR "012" OR "015")',
            "saudi": '("05" OR "9665" OR "966")',
            "uae": '("050" OR "055" OR "9714")',
            "kuwait": '("965")'
        }
        phone_patterns = phone_patterns_map.get(country, '("010" OR "011" OR "012" OR "015")')
        
        try:
            golden_query = AIService.generate_golden_query(query, city, strategy, country)
            print(f"🎯 Golden Query ({country}/{strategy}): {golden_query}")
        except Exception as e:
            print(f"⚠️ Golden Query generation failed: {e}")
            strategy_config = AIService.HUNTING_STRATEGIES.get(strategy, AIService.HUNTING_STRATEGIES["social_media"])
            golden_query = f'{strategy_config["sites"]} "{query}" "{city}" {phone_patterns} -site:youtube.com'
        
        if not golden_query:
            golden_query = f'site:facebook.com "{query}" "{city}" {phone_patterns}'
        
        results = cls.search_with_country(golden_query, country, max_results * 3)
        leads = cls.extract_leads_from_results(results, country)
        
        for lead in leads:
            phone = lead.get('phone', '')
            email = lead.get('email', '')
            if phone and phone not in seen_phones:
                all_leads.append(lead)
                seen_phones.add(phone)
            elif email and email not in seen_emails and not phone:
                all_leads.append(lead)
                seen_emails.add(email)
        
        service = AIService._extract_service(query)
        
        phone_heavy_queries = [
            f'site:facebook.com ("محتاج {service}" OR "عايز {service}") "{city}" {phone_patterns}',
            f'site:facebook.com ("مين يعرف {service}" OR "دلوني على {service}") "{city}" {phone_patterns}',
            f'site:instagram.com ("محتاج {service}" OR "ابحث عن {service}") {city} {phone_patterns}',
            f'"يا ريت حد يرشحلي {service}" OR "حد يعرف {service} كويس" {city}',
            f'"{city}" ("محتاج {service} ضروري" OR "عايز {service} كويس") {phone_patterns}',
            f'"حد جرب {service}" OR "تجربتكم مع {service}" {city} {phone_patterns}',
        ]
        
        for search_query in phone_heavy_queries:
            if len(all_leads) >= max_results:
                break
                
            print(f"📍 Fallback search: {search_query[:60]}...")
            results = cls.search_with_country(search_query, country, max_results)
            leads = cls.extract_leads_from_results(results, country)
            
            for lead in leads:
                phone = lead.get('phone', '')
                email = lead.get('email', '')
                if phone and phone not in seen_phones:
                    all_leads.append(lead)
                    seen_phones.add(phone)
                elif email and email not in seen_emails and not phone:
                    all_leads.append(lead)
                    seen_emails.add(email)
        
        if len(all_leads) < max_results:
            fallback_queries = AIService.generate_fallback_queries(query, city, country)
            
            for search_query in fallback_queries:
                if len(all_leads) >= max_results:
                    break
                    
                results = cls.search_with_country(search_query, country, max_results)
                leads = cls.extract_leads_from_results(results, country)
                
                for lead in leads:
                    phone = lead.get('phone', '')
                    email = lead.get('email', '')
                    if phone and phone not in seen_phones:
                        all_leads.append(lead)
                        seen_phones.add(phone)
                    elif email and email not in seen_emails and not phone:
                        all_leads.append(lead)
                        seen_emails.add(email)
        
        if len(all_leads) < max_results:
            country_names = {"egypt": "مصر", "saudi": "السعودية", "uae": "الإمارات", "kuwait": "الكويت"}
            country_name = country_names.get(country, "مصر")
            
            generic_queries = [
                f'"محتاج {service}" {country_name} {phone_patterns}',
                f'"عايز {service}" {city} {phone_patterns}',
                f'"مين يعرف {service} كويس" {city}',
                f'"ابحث عن {service}" {city} {phone_patterns}',
                f'"حد يرشحلي {service}" {country_name}'
            ]
            
            for search_query in generic_queries:
                if len(all_leads) >= max_results:
                    break
                results = cls.search_with_country(search_query, country, max_results)
                leads = cls.extract_leads_from_results(results, country)
                
                for lead in leads:
                    phone = lead.get('phone', '')
                    email = lead.get('email', '')
                    if phone and phone not in seen_phones:
                        all_leads.append(lead)
                        seen_phones.add(phone)
                    elif email and email not in seen_emails and not phone:
                        all_leads.append(lead)
                        seen_emails.add(email)
        
        print(f"✅ Found {len(all_leads)} leads (requested: {max_results})")
        return all_leads[:max_results]
