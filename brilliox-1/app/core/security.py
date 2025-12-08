"""Security Utilities - Rate Limiting, Password Hashing, Sanitization"""
import re
import html
import time
import bcrypt
from typing import Dict, List, Tuple
from collections import defaultdict
from .config import settings

# Rate limiting storage
rate_limits: Dict[str, List[float]] = defaultdict(list)
blocked_ips: Dict[str, float] = {}


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def rate_limit(ip: str) -> Tuple[bool, str]:
    """Check if IP should be rate limited. Returns (is_allowed, message)"""
    current_time = time.time()
    
    # Check if blocked
    if ip in blocked_ips:
        if current_time < blocked_ips[ip]:
            return False, "تم حظرك مؤقتاً"
        else:
            del blocked_ips[ip]
    
    # Clean old requests
    rate_limits[ip] = [
        t for t in rate_limits[ip] 
        if current_time - t < settings.RATE_LIMIT_WINDOW
    ]
    
    # Check limit
    if len(rate_limits[ip]) >= settings.RATE_LIMIT_REQUESTS:
        blocked_ips[ip] = current_time + settings.BLOCK_DURATION
        return False, "طلبات كثيرة، حاول لاحقاً"
    
    rate_limits[ip].append(current_time)
    return True, ""


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Sanitize user input to prevent XSS and injection"""
    if not text:
        return ""
    
    # Truncate and escape
    text = html.escape(str(text)[:max_length])
    
    # Remove dangerous patterns
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


def validate_phone(phone: str) -> str:
    """Validate and clean phone number"""
    phone = re.sub(r'[^\d]', '', phone)
    if len(phone) < 10:
        return ""
    return phone
