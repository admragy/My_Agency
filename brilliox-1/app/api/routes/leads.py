"""
Lead Routes
Lead management endpoints
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from app.schemas.requests import ShareLeadRequest, FeedbackRequest
from app.services.lead_service import LeadService
from app.services.user_service import UserService

router = APIRouter(prefix="/api", tags=["leads"])


@router.get("/leads/{user_id}")
async def get_leads(user_id: str, status: Optional[str] = None):
    """Get user leads"""
    leads = LeadService.get_user_leads(user_id)
    
    if status:
        leads = [l for l in leads if l.get("status") == status]
    
    return {
        "leads": leads,
        "count": len(leads)
    }


@router.post("/leads/{user_id}/share")
async def share_lead(user_id: str, data: ShareLeadRequest):
    """Share lead with another user"""
    success = LeadService.share_lead(user_id, data.share_with, data.lead_id)
    
    if success:
        return {"success": True, "message": f"تم مشاركة العميل مع {data.share_with}"}
    
    raise HTTPException(status_code=500, detail="فشل في مشاركة العميل")


@router.get("/leads/{user_id}/shared")
async def get_shared_leads(user_id: str):
    """Get leads shared with user"""
    leads = LeadService.get_shared_leads(user_id)
    return {
        "leads": leads,
        "count": len(leads)
    }


@router.delete("/leads/{user_id}/{lead_id}")
async def delete_lead(user_id: str, lead_id: int):
    """Delete a lead"""
    success = LeadService.delete_lead(lead_id, user_id)
    
    if success:
        return {"success": True, "message": "تم حذف العميل"}
    
    raise HTTPException(status_code=404, detail="العميل غير موجود")


@router.put("/leads/{user_id}/{lead_id}")
async def update_lead(user_id: str, lead_id: int, updates: dict):
    """Update lead data"""
    lead = LeadService.update_lead(lead_id, user_id, updates)
    
    if lead:
        return {"success": True, "lead": lead}
    
    raise HTTPException(status_code=404, detail="العميل غير موجود")
