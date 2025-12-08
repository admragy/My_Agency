"""
Chat Routes
AI chat and search endpoints
"""
from fastapi import APIRouter, HTTPException
from app.schemas.requests import ChatRequest, HuntRequest
from app.services.ai_service import AIService
from app.services.search_service import SearchService
from app.services.user_service import UserService
from app.services.lead_service import LeadService
from app.core.config import settings

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/{user_id}")
async def chat(user_id: str, data: ChatRequest):
    """AI chat endpoint"""
    can_afford, balance = UserService.check_balance(user_id, settings.CHAT_COST)
    
    if not can_afford:
        raise HTTPException(
            status_code=402,
            detail=f"رصيدك غير كافي ({balance} توكن). المطلوب: {settings.CHAT_COST} توكن"
        )
    
    response = AIService.generate(data.message)
    
    UserService.deduct_balance(user_id, settings.CHAT_COST)
    
    user = UserService.get_or_create(user_id)
    
    return {
        "response": response,
        "tokens_used": settings.CHAT_COST,
        "remaining_balance": user.get("wallet_balance", 0)
    }


@router.post("/hunt/{user_id}")
async def hunt(user_id: str, data: HuntRequest):
    """Lead hunting endpoint"""
    can_afford, balance = UserService.check_balance(user_id, settings.HUNT_COST)
    
    if not can_afford:
        raise HTTPException(
            status_code=402,
            detail=f"رصيدك غير كافي ({balance} توكن). المطلوب: {settings.HUNT_COST} توكن"
        )
    
    leads = SearchService.hunt_leads(data.query, data.city, data.max_results)
    
    if leads:
        LeadService.add_leads_batch(user_id, leads)
        UserService.deduct_balance(user_id, settings.HUNT_COST)
    
    user = UserService.get_or_create(user_id)
    
    return {
        "leads": leads,
        "count": len(leads),
        "tokens_used": settings.HUNT_COST if leads else 0,
        "remaining_balance": user.get("wallet_balance", 0)
    }


@router.get("/stats/{user_id}")
async def get_stats(user_id: str):
    """Get user statistics"""
    user = UserService.get_or_create(user_id)
    lead_stats = LeadService.get_lead_stats(user_id)
    
    return {
        "user_id": user_id,
        "wallet_balance": user.get("wallet_balance", 0),
        "leads": lead_stats
    }
