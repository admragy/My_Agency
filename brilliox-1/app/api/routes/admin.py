"""
Admin Routes
Admin panel and user management
"""
from fastapi import APIRouter, HTTPException
from app.schemas.requests import AdminCreateUser, DistributeTokens
from app.services.user_service import UserService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def get_all_users(admin_id: str):
    """Get all users (admin only)"""
    if not UserService.is_admin(admin_id):
        raise HTTPException(status_code=403, detail="غير مصرح لك")
    
    users = UserService.get_all_users()
    return {"users": users, "count": len(users)}


@router.post("/users/create")
async def create_user(admin_id: str, data: AdminCreateUser):
    """Create new user (admin only)"""
    if not UserService.is_admin(admin_id):
        raise HTTPException(status_code=403, detail="غير مصرح لك")
    
    user = UserService.create_user(
        data.username,
        data.password,
        data.initial_balance,
        data.is_admin
    )
    
    return {"success": True, "user": user}


@router.post("/tokens/distribute")
async def distribute_tokens(admin_id: str, data: DistributeTokens):
    """Distribute tokens to user (admin only)"""
    if not UserService.is_admin(admin_id):
        raise HTTPException(status_code=403, detail="غير مصرح لك")
    
    success = UserService.add_balance(data.user_id, data.amount)
    
    if success:
        user = UserService.get_or_create(data.user_id)
        return {
            "success": True,
            "message": f"تم إضافة {data.amount} توكن",
            "new_balance": user.get("wallet_balance", 0)
        }
    
    raise HTTPException(status_code=500, detail="فشل في توزيع التوكنز")
