"""
Authentication Routes
User login and registration endpoints
"""
from fastapi import APIRouter, HTTPException
from app.schemas.requests import UserCreate
from app.services.user_service import UserService

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login")
async def login(data: UserCreate):
    """User login/registration"""
    try:
        user = UserService.get_or_create(data.username)
        return {
            "success": True,
            "user_id": data.username,
            "wallet_balance": user.get("wallet_balance", 100),
            "is_admin": user.get("is_admin", False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallet/{user_id}")
async def get_wallet(user_id: str):
    """Get user wallet balance"""
    user = UserService.get_or_create(user_id)
    return {
        "user_id": user_id,
        "wallet_balance": user.get("wallet_balance", 0),
        "is_admin": user.get("is_admin", False)
    }
