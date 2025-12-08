"""Internationalization (i18n) System"""
import json
import os
from typing import Dict, Any, Optional
from functools import lru_cache
from .config import settings

LOCALES_DIR = "locales"
_translations: Dict[str, Dict[str, Any]] = {}


@lru_cache(maxsize=10)
def load_translations(lang: str) -> Dict[str, Any]:
    """Load translations for a language"""
    file_path = os.path.join(LOCALES_DIR, f"{lang}.json")
    
    if not os.path.exists(file_path):
        # Fallback to default language
        file_path = os.path.join(LOCALES_DIR, f"{settings.DEFAULT_LANGUAGE}.json")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def t(key: str, lang: str = "ar", **kwargs) -> str:
    """Get translation by key (dot notation: 'chat.welcome')"""
    translations = load_translations(lang)
    
    # Navigate nested keys
    keys = key.split(".")
    value = translations
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k, "")
        else:
            return key
    
    # Format with kwargs if provided
    if isinstance(value, str) and kwargs:
        try:
            value = value.format(**kwargs)
        except Exception:
            pass
    
    return value if value else key


def get_all_translations(lang: str = "ar") -> Dict[str, Any]:
    """Get all translations for a language"""
    return load_translations(lang)


def get_direction(lang: str) -> str:
    """Get text direction for language"""
    return "rtl" if lang == "ar" else "ltr"


def get_font(lang: str) -> str:
    """Get appropriate font for language"""
    return "Cairo" if lang == "ar" else "Inter"
