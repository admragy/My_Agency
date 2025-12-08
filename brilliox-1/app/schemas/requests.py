"""
Request Schemas
Pydantic models for API request validation
"""
import re
import html
from typing import Optional, List
from pydantic import BaseModel, field_validator


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not text:
        return ""
    text = html.escape(str(text)[:max_length])
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    return text.strip()


def validate_username(username: str) -> str:
    """Validate and sanitize username"""
    username = re.sub(r'[^\w\u0600-\u06FF\s-]', '', username)[:50]
    if len(username) < 2:
        raise ValueError("اسم المستخدم قصير جداً")
    return username


class ChatRequest(BaseModel):
    message: str
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or len(v.strip()) < 1:
            raise ValueError("الرسالة فارغة")
        return sanitize_input(v, 5000)


class HuntRequest(BaseModel):
    query: str
    city: str = "القاهرة"
    max_results: int = 20
    
    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        return sanitize_input(v, 500)
    
    @field_validator('max_results')
    @classmethod
    def validate_max(cls, v):
        return min(max(1, v), 50)


class UserCreate(BaseModel):
    username: str
    password: str = ""
    
    @field_validator('username')
    @classmethod
    def validate_user(cls, v):
        return validate_username(v)


class AdminCreateUser(BaseModel):
    username: str
    password: str = ""
    initial_balance: int = 100
    is_admin: bool = False
    
    @field_validator('initial_balance')
    @classmethod
    def validate_balance(cls, v):
        return min(max(0, v), 100000)


class DistributeTokens(BaseModel):
    user_id: str
    amount: int
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        return min(max(1, v), 50000)


class AdRequest(BaseModel):
    ad_type: str = "create"
    platform: str = "facebook"
    business_type: str = ""
    goal: str = "awareness"
    target_audience: str = ""
    budget: Optional[float] = None
    description: str = ""
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        allowed = ["facebook", "instagram", "google", "tiktok", "linkedin", "twitter"]
        return v if v in allowed else "facebook"
    
    @field_validator('description')
    @classmethod
    def validate_desc(cls, v):
        return sanitize_input(v, 3000)


class CampaignRequest(BaseModel):
    name: str
    platform: str = "facebook"
    goal: str = "leads"
    budget: float = 100
    duration_days: int = 7
    
    @field_validator('budget')
    @classmethod
    def validate_budget(cls, v):
        return min(max(10, v), 1000000)
    
    @field_validator('duration_days')
    @classmethod
    def validate_duration(cls, v):
        return min(max(1, v), 365)


class ShareLeadRequest(BaseModel):
    lead_id: int
    share_with: str
    
    @field_validator('share_with')
    @classmethod
    def validate_share_with(cls, v):
        return validate_username(v)


class FeedbackRequest(BaseModel):
    lead_id: int
    rating: int = 5
    comment: str = ""
    client_name: str = ""
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        return min(max(1, v), 5)
    
    @field_validator('comment')
    @classmethod
    def validate_comment(cls, v):
        return sanitize_input(v, 1000)


class FunnelUpdateRequest(BaseModel):
    lead_id: int
    stage: str
    
    @field_validator('stage')
    @classmethod
    def validate_stage(cls, v):
        allowed = ["bait_sent", "replied", "interested", "negotiating", "hot", "closed", "lost"]
        if v not in allowed:
            raise ValueError("مرحلة غير صالحة")
        return v


class AIReplyRequest(BaseModel):
    lead_id: int
    customer_message: str
    conversation_context: str = ""
    
    @field_validator('customer_message')
    @classmethod
    def validate_message(cls, v):
        return sanitize_input(v, 2000)


class BaitMessageRequest(BaseModel):
    lead_id: int
    template_type: str = "curiosity"
    
    @field_validator('template_type')
    @classmethod
    def validate_type(cls, v):
        allowed = ["curiosity", "problem", "urgency", "social_proof", "question", "value"]
        return v if v in allowed else "curiosity"


class LearningImportRequest(BaseModel):
    conversation_text: str
    platform: str = "whatsapp"
    outcome: str = "unknown"
    
    @field_validator('conversation_text')
    @classmethod
    def validate_text(cls, v):
        if len(v) < 10:
            raise ValueError("المحادثة قصيرة جداً")
        return sanitize_input(v, 10000)
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v):
        allowed = ["whatsapp", "messenger", "instagram", "other"]
        return v if v in allowed else "whatsapp"


class LearningPatternRequest(BaseModel):
    customer_message: str
    successful_reply: str
    context: str = ""
    
    @field_validator('customer_message', 'successful_reply')
    @classmethod
    def validate_texts(cls, v):
        return sanitize_input(v, 2000)


class LearningRateRequest(BaseModel):
    conversation_id: int
    rating: int
    outcome: str = "unknown"
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        return min(max(1, v), 5)
    
    @field_validator('outcome')
    @classmethod
    def validate_outcome(cls, v):
        allowed = ["converted", "lost", "pending", "unknown"]
        return v if v in allowed else "unknown"


class SmartReplyRequest(BaseModel):
    customer_message: str
    lead_id: Optional[int] = None
    use_patterns: bool = True
    
    @field_validator('customer_message')
    @classmethod
    def validate_message(cls, v):
        return sanitize_input(v, 2000)
