"""
User Service
User management and authentication
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.core.config import settings
import app.core.database as db_module
from app.core.database import LOCAL_DB
from app.core.security import hash_password, verify_password


class UserService:
    """User management service"""
    
    @staticmethod
    def get_or_create(user_id: str) -> Dict[str, Any]:
        """Get existing user or create new one"""
        is_admin = user_id.lower() == "admin"
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM users WHERE username = %s", (user_id,))
                row = cur.fetchone()
                
                if row:
                    user = dict(row)
                    if is_admin:
                        user["is_admin"] = True
                    cur.close()
                    return user
                
                cur.execute("""
                    INSERT INTO users (username, wallet_balance, is_admin) 
                    VALUES (%s, %s, %s) 
                    ON CONFLICT (username) DO NOTHING
                    RETURNING *
                """, (user_id, settings.DEFAULT_BALANCE, is_admin))
                new_row = cur.fetchone()
                cur.close()
                
                if new_row:
                    return dict(new_row)
                
                return {"username": user_id, "wallet_balance": settings.DEFAULT_BALANCE, "is_admin": is_admin}
            except Exception as e:
                print(f"DB Error: {e}")
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("users").select("*").eq("username", user_id).execute()
                if result.data:
                    user = result.data[0]
                    if is_admin:
                        user["is_admin"] = True
                    return user
                
                new_user = {
                    "username": user_id,
                    "wallet_balance": settings.DEFAULT_BALANCE,
                    "is_admin": is_admin,
                    "created_at": datetime.now().isoformat()
                }
                db_module.supabase.table("users").insert(new_user).execute()
                return new_user
            except:
                pass
        
        if user_id not in LOCAL_DB["users"]:
            LOCAL_DB["users"][user_id] = {
                "username": user_id,
                "wallet_balance": settings.DEFAULT_BALANCE,
                "is_admin": is_admin,
                "created_at": datetime.now().isoformat()
            }
        elif is_admin:
            LOCAL_DB["users"][user_id]["is_admin"] = True
        
        return LOCAL_DB["users"][user_id]
    
    @staticmethod
    def is_admin(user_id: str) -> bool:
        """Check if user is admin"""
        if user_id.lower() == "admin":
            return True
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT is_admin FROM users WHERE username = %s", (user_id,))
                row = cur.fetchone()
                cur.close()
                if row:
                    return row.get("is_admin", False)
            except:
                pass
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("users").select("is_admin").eq("username", user_id).execute()
                if result.data:
                    return result.data[0].get("is_admin", False)
            except:
                pass
        
        return LOCAL_DB["users"].get(user_id, {}).get("is_admin", False)
    
    @staticmethod
    def check_balance(user_id: str, cost: int) -> tuple:
        """Check if user has enough balance"""
        user = UserService.get_or_create(user_id)
        
        if user.get("is_admin", False):
            return True, 999999
        
        balance = user.get("wallet_balance", 0)
        return balance >= cost, balance
    
    @staticmethod
    def deduct_balance(user_id: str, cost: int) -> bool:
        """Deduct from user's wallet balance"""
        user = UserService.get_or_create(user_id)
        
        if user.get("is_admin", False):
            return True
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute(
                    "UPDATE users SET wallet_balance = wallet_balance - %s WHERE username = %s AND wallet_balance >= %s",
                    (cost, user_id, cost)
                )
                success = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
                return success
            except Exception as e:
                print(f"Deduct balance error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                current = user.get("wallet_balance", 0)
                if current >= cost:
                    db_module.supabase.table("users").update(
                        {"wallet_balance": current - cost}
                    ).eq("username", user_id).execute()
                    return True
            except:
                pass
        
        if user_id in LOCAL_DB["users"]:
            if LOCAL_DB["users"][user_id].get("wallet_balance", 0) >= cost:
                LOCAL_DB["users"][user_id]["wallet_balance"] -= cost
                return True
        
        return False
    
    @staticmethod
    def add_balance(user_id: str, amount: int) -> bool:
        """Add to user's wallet balance"""
        UserService.get_or_create(user_id)
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute(
                    "UPDATE users SET wallet_balance = wallet_balance + %s WHERE username = %s",
                    (amount, user_id)
                )
                success = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
                return success
            except Exception as e:
                print(f"Add balance error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                user = UserService.get_or_create(user_id)
                current = user.get("wallet_balance", 0)
                db_module.supabase.table("users").update(
                    {"wallet_balance": current + amount}
                ).eq("username", user_id).execute()
                return True
            except:
                pass
        
        if user_id in LOCAL_DB["users"]:
            LOCAL_DB["users"][user_id]["wallet_balance"] = LOCAL_DB["users"][user_id].get("wallet_balance", 0) + amount
            return True
        
        return False
    
    @staticmethod
    def set_admin(user_id: str, is_admin: bool = True) -> bool:
        """Set admin status for user"""
        UserService.get_or_create(user_id)
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute(
                    "UPDATE users SET is_admin = %s WHERE username = %s",
                    (is_admin, user_id)
                )
                success = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
                return success
            except Exception as e:
                print(f"Set admin error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_module.supabase.table("users").update(
                    {"is_admin": is_admin}
                ).eq("username", user_id).execute()
                return True
            except:
                pass
        
        if user_id in LOCAL_DB["users"]:
            LOCAL_DB["users"][user_id]["is_admin"] = is_admin
            return True
        
        return False
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        """Get all users (admin only)"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT username, wallet_balance, is_admin, created_at FROM users ORDER BY created_at DESC")
                users = [dict(row) for row in cur.fetchall()]
                cur.close()
                return users
            except:
                pass
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("users").select("username, wallet_balance, is_admin, created_at").execute()
                return result.data
            except:
                pass
        
        return [
            {
                "username": k,
                "wallet_balance": v.get("wallet_balance", 0),
                "is_admin": v.get("is_admin", False),
                "created_at": v.get("created_at", "")
            }
            for k, v in LOCAL_DB["users"].items()
        ]
    
    @staticmethod
    def create_user(username: str, password: str = "", initial_balance: int = 100, is_admin: bool = False) -> Dict:
        """Create new user with optional password"""
        hashed = hash_password(password) if password else ""
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute("""
                    INSERT INTO users (username, password, wallet_balance, is_admin)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (username, hashed, initial_balance, is_admin))
                cur.close()
            except:
                pass
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_module.supabase.table("users").insert({
                    "username": username,
                    "password": hashed,
                    "wallet_balance": initial_balance,
                    "is_admin": is_admin,
                    "created_at": datetime.now().isoformat()
                }).execute()
            except:
                pass
        
        LOCAL_DB["users"][username] = {
            "username": username,
            "password": hashed,
            "wallet_balance": initial_balance,
            "is_admin": is_admin,
            "created_at": datetime.now().isoformat()
        }
        
        return LOCAL_DB["users"][username]
    
    @staticmethod
    def login_with_password(username: str, password: str) -> Optional[Dict]:
        """Login user with password verification"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                cur.close()
                
                if row:
                    user = dict(row)
                    stored_password = user.get("password", "")
                    if not stored_password or verify_password(password, stored_password):
                        return user
                return None
            except Exception as e:
                print(f"Login error: {e}")
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("users").select("*").eq("username", username).execute()
                if result.data:
                    user = result.data[0]
                    stored_password = user.get("password", "")
                    if not stored_password or verify_password(password, stored_password):
                        return user
                return None
            except:
                pass
        
        if username in LOCAL_DB["users"]:
            user = LOCAL_DB["users"][username]
            stored_password = user.get("password", "")
            if not stored_password or verify_password(password, stored_password):
                return user
        
        return None
    
    @staticmethod
    def set_password(username: str, new_password: str) -> bool:
        """Set or update user password"""
        hashed = hash_password(new_password)
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute("UPDATE users SET password = %s WHERE username = %s", (hashed, username))
                success = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
                return success
            except Exception as e:
                print(f"Set password error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_module.supabase.table("users").update({"password": hashed}).eq("username", username).execute()
                return True
            except:
                pass
        
        if username in LOCAL_DB["users"]:
            LOCAL_DB["users"][username]["password"] = hashed
            return True
        
        return False
    
    @staticmethod
    def delete_user(username: str) -> tuple[bool, str]:
        """Delete a user and all their data"""
        if username.lower() == "admin":
            return False, "لا يمكن حذف حساب الأدمن"
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute("DELETE FROM leads WHERE user_id = %s", (username,))
                cur.execute("DELETE FROM chat_history WHERE user_id = %s", (username,))
                cur.execute("DELETE FROM feedback WHERE user_id = %s", (username,))
                cur.execute("DELETE FROM shared_leads WHERE from_user = %s OR to_user = %s", (username, username))
                cur.execute("DELETE FROM users WHERE username = %s", (username,))
                deleted = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
                if deleted:
                    return True, f"تم حذف المستخدم {username} وجميع بياناته"
                return False, "المستخدم غير موجود"
            except Exception as e:
                print(f"Delete user error: {e}")
                db_module.pg_conn.rollback()
                return False, f"حدث خطأ: {str(e)}"
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_module.supabase.table("leads").delete().eq("user_id", username).execute()
                db_module.supabase.table("chat_history").delete().eq("user_id", username).execute()
                db_module.supabase.table("feedback").delete().eq("user_id", username).execute()
                db_module.supabase.table("shared_leads").delete().or_(f"from_user.eq.{username},to_user.eq.{username}").execute()
                db_module.supabase.table("users").delete().eq("username", username).execute()
                return True, f"تم حذف المستخدم {username} وجميع بياناته"
            except Exception as e:
                return False, f"حدث خطأ: {str(e)}"
        
        if username in LOCAL_DB["users"]:
            del LOCAL_DB["users"][username]
            return True, f"تم حذف المستخدم {username}"
        
        return False, "المستخدم غير موجود"
    
    @staticmethod
    def change_password(username: str, old_password: str, new_password: str) -> tuple[bool, str]:
        """Change user password with old password verification"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT password FROM users WHERE username = %s", (username,))
                row = cur.fetchone()
                cur.close()
                
                if not row:
                    return False, "المستخدم غير موجود"
                
                stored_password = row.get("password", "")
                if stored_password and not verify_password(old_password, stored_password):
                    return False, "كلمة المرور القديمة غير صحيحة"
                
                if UserService.set_password(username, new_password):
                    return True, "تم تغيير كلمة المرور بنجاح"
                return False, "فشل في تغيير كلمة المرور"
            except Exception as e:
                print(f"Change password error: {e}")
                return False, "حدث خطأ"
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("users").select("password").eq("username", username).execute()
                if not result.data:
                    return False, "المستخدم غير موجود"
                
                stored_password = result.data[0].get("password", "")
                if stored_password and not verify_password(old_password, stored_password):
                    return False, "كلمة المرور القديمة غير صحيحة"
                
                if UserService.set_password(username, new_password):
                    return True, "تم تغيير كلمة المرور بنجاح"
                return False, "فشل في تغيير كلمة المرور"
            except:
                return False, "حدث خطأ"
        
        if username not in LOCAL_DB["users"]:
            return False, "المستخدم غير موجود"
        
        stored_password = LOCAL_DB["users"][username].get("password", "")
        if stored_password and not verify_password(old_password, stored_password):
            return False, "كلمة المرور القديمة غير صحيحة"
        
        if UserService.set_password(username, new_password):
            return True, "تم تغيير كلمة المرور بنجاح"
        return False, "فشل في تغيير كلمة المرور"
