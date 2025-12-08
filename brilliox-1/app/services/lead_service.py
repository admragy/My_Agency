"""
Lead Service
Lead management and storage
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from app.core.config import settings
import app.core.database as db_module


class LeadService:
    """Lead management service"""
    
    @staticmethod
    def _normalize_lead(lead: Dict) -> Dict:
        """Normalize lead fields for consistent API response"""
        return {
            "id": lead.get("id", ""),
            "user_id": lead.get("user_id", ""),
            "name": lead.get("full_name") or lead.get("name", ""),
            "phone": lead.get("phone_number") or lead.get("phone", ""),
            "email": lead.get("email", ""),
            "source": lead.get("source", ""),
            "notes": lead.get("notes", ""),
            "status": lead.get("status", "new"),
            "quality": lead.get("quality", ""),
            "funnel_stage": lead.get("funnel_stage", ""),
            "is_favorite": lead.get("is_favorite", False),
            "created_at": str(lead.get("created_at", ""))
        }
    
    @staticmethod
    def get_user_leads(user_id: str) -> List[Dict]:
        """Get all leads for a user"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    "SELECT * FROM leads WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
                leads = [LeadService._normalize_lead(dict(row)) for row in cur.fetchall()]
                cur.close()
                return leads
            except Exception as e:
                print(f"Lead fetch error: {e}")
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("leads").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
                return [LeadService._normalize_lead(l) for l in result.data]
            except:
                pass
        
        return [LeadService._normalize_lead(l) for l in db_module.LOCAL_DB["leads"] if l.get("user_id") == user_id]
    
    @staticmethod
    def add_lead(user_id: str, lead_data: Dict) -> Dict:
        """Add new lead"""
        lead_id = str(uuid.uuid4())
        
        lead = {
            "id": lead_id,
            "user_id": user_id,
            "full_name": lead_data.get("name", "") or lead_data.get("full_name", ""),
            "phone_number": lead_data.get("phone", "") or lead_data.get("phone_number", ""),
            "email": lead_data.get("email", ""),
            "source": lead_data.get("source", ""),
            "notes": lead_data.get("notes", ""),
            "status": lead_data.get("status", "new"),
            "created_at": datetime.now().isoformat()
        }
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    INSERT INTO leads (id, user_id, full_name, phone_number, email, source, notes, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (lead_id, user_id, lead["full_name"], lead["phone_number"], lead["email"], lead["source"], lead["notes"], lead["status"]))
                result = cur.fetchone()
                db_module.pg_conn.commit()
                cur.close()
                if result:
                    return LeadService._normalize_lead(dict(result))
            except Exception as e:
                print(f"Lead add error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                result = db_module.supabase.table("leads").insert(lead).execute()
                if result.data:
                    return LeadService._normalize_lead(result.data[0])
            except:
                pass
        
        db_module.LOCAL_DB["leads"].append(lead)
        return LeadService._normalize_lead(lead)
    
    @staticmethod
    def add_leads_batch(user_id: str, leads_data: List[Dict]) -> List[Dict]:
        """Add multiple leads at once"""
        added = []
        for lead_data in leads_data:
            lead = LeadService.add_lead(user_id, lead_data)
            added.append(lead)
        return added
    
    @staticmethod
    def update_lead(lead_id: str, user_id: str, updates: Dict) -> Optional[Dict]:
        """Update lead data"""
        field_map = {
            "name": "full_name",
            "phone": "phone_number",
            "email": "email",
            "source": "source",
            "notes": "notes",
            "status": "status"
        }
        
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                
                set_parts = []
                values = []
                for key, value in updates.items():
                    db_field = field_map.get(key, key)
                    if db_field in ["full_name", "phone_number", "email", "source", "notes", "status"]:
                        set_parts.append(f"{db_field} = %s")
                        values.append(value)
                
                if set_parts:
                    values.extend([str(lead_id), user_id])
                    cur.execute(
                        f"UPDATE leads SET {', '.join(set_parts)} WHERE id = %s AND user_id = %s RETURNING *",
                        values
                    )
                    result = cur.fetchone()
                    db_module.pg_conn.commit()
                    cur.close()
                    if result:
                        return LeadService._normalize_lead(dict(result))
            except Exception as e:
                print(f"Lead update error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_updates = {field_map.get(k, k): v for k, v in updates.items()}
                result = db_module.supabase.table("leads").update(db_updates).eq("id", str(lead_id)).eq("user_id", user_id).execute()
                if result.data:
                    return LeadService._normalize_lead(result.data[0])
            except:
                pass
        
        for lead in db_module.LOCAL_DB["leads"]:
            if str(lead.get("id")) == str(lead_id) and lead.get("user_id") == user_id:
                for k, v in updates.items():
                    db_field = field_map.get(k, k)
                    lead[db_field] = v
                return LeadService._normalize_lead(lead)
        
        return None
    
    @staticmethod
    def delete_lead(lead_id: str, user_id: str) -> bool:
        """Delete a lead"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute(
                    "DELETE FROM leads WHERE id = %s AND user_id = %s",
                    (str(lead_id), user_id)
                )
                success = cur.rowcount > 0
                db_module.pg_conn.commit()
                cur.close()
                return success
            except Exception as e:
                print(f"Lead delete error: {e}")
                db_module.pg_conn.rollback()
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_module.supabase.table("leads").delete().eq("id", str(lead_id)).eq("user_id", user_id).execute()
                return True
            except:
                pass
        
        db_module.LOCAL_DB["leads"] = [
            l for l in db_module.LOCAL_DB["leads"]
            if not (str(l.get("id")) == str(lead_id) and l.get("user_id") == user_id)
        ]
        return True
    
    @staticmethod
    def get_lead_stats(user_id: str) -> Dict:
        """Get lead statistics"""
        leads = LeadService.get_user_leads(user_id)
        
        status_counts = {}
        for lead in leads:
            status = lead.get("status", "new")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total": len(leads),
            "by_status": status_counts,
            "new": status_counts.get("new", 0),
            "bait_sent": status_counts.get("bait_sent", 0),
            "replied": status_counts.get("replied", 0),
            "interested": status_counts.get("interested", 0),
            "negotiating": status_counts.get("negotiating", 0),
            "hot": status_counts.get("hot", 0),
            "closed": status_counts.get("closed", 0),
            "lost": status_counts.get("lost", 0),
            "converted": status_counts.get("closed", 0)
        }
    
    @staticmethod
    def share_lead(from_user: str, to_user: str, lead_id: str, status: str = "new", notes: str = "") -> bool:
        """Share lead with another user including status"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                cur.execute("""
                    INSERT INTO shared_leads (from_user, to_user, lead_id, shared_status, shared_notes, last_updated_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (from_user, to_user, str(lead_id), status, notes, from_user))
                db_module.pg_conn.commit()
                cur.close()
                return True
            except Exception as e:
                print(f"Share lead error: {e}")
                pass
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                db_module.supabase.table("shared_leads").insert({
                    "from_user": from_user,
                    "to_user": to_user,
                    "lead_id": str(lead_id),
                    "shared_status": status,
                    "shared_notes": notes,
                    "last_updated_by": from_user,
                    "created_at": datetime.now().isoformat()
                }).execute()
                return True
            except:
                pass
        
        share_id = str(uuid.uuid4())
        db_module.LOCAL_DB["shared_leads"].append({
            "id": share_id,
            "from_user": from_user,
            "to_user": to_user,
            "lead_id": str(lead_id),
            "shared_status": status,
            "shared_notes": notes,
            "last_updated_by": from_user,
            "created_at": datetime.now().isoformat()
        })
        return True
    
    @staticmethod
    def share_leads_batch(from_user: str, to_user: str, lead_ids: List[str], status: str = "new", notes: str = "") -> Dict:
        """Share multiple leads with another user"""
        success_count = 0
        failed_count = 0
        
        for lead_id in lead_ids:
            if LeadService.share_lead(from_user, to_user, lead_id, status, notes):
                success_count += 1
            else:
                failed_count += 1
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(lead_ids)
        }
    
    @staticmethod
    def update_shared_lead_status(share_id: str, user_id: str, status: str, notes: Optional[str] = None) -> bool:
        """Update shared lead status - both sender and receiver can update"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                cur = db_module.pg_conn.cursor()
                if notes is not None:
                    cur.execute("""
                        UPDATE shared_leads 
                        SET shared_status = %s, shared_notes = %s, last_updated_by = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND (from_user = %s OR to_user = %s)
                    """, (status, notes, user_id, share_id, user_id, user_id))
                else:
                    cur.execute("""
                        UPDATE shared_leads 
                        SET shared_status = %s, last_updated_by = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s AND (from_user = %s OR to_user = %s)
                    """, (status, user_id, share_id, user_id, user_id))
                db_module.pg_conn.commit()
                success = cur.rowcount > 0
                cur.close()
                return success
            except Exception as e:
                print(f"Update shared status error: {e}")
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                update_data = {
                    "shared_status": status,
                    "last_updated_by": user_id,
                    "updated_at": datetime.now().isoformat()
                }
                if notes is not None:
                    update_data["shared_notes"] = notes
                result = db_module.supabase.table("shared_leads").select("*").eq("id", share_id).execute()
                if result.data:
                    share = result.data[0]
                    if share.get("from_user") == user_id or share.get("to_user") == user_id:
                        db_module.supabase.table("shared_leads").update(update_data).eq("id", share_id).execute()
                        return True
                return False
            except:
                pass
        
        for share in db_module.LOCAL_DB["shared_leads"]:
            if str(share.get("id")) == str(share_id) and (share.get("from_user") == user_id or share.get("to_user") == user_id):
                share["shared_status"] = status
                share["last_updated_by"] = user_id
                if notes is not None:
                    share["shared_notes"] = notes
                return True
        
        return False
    
    @staticmethod
    def get_sent_shared_leads(user_id: str) -> List[Dict]:
        """Get leads that user has shared with others"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT s.id as share_id, s.to_user, s.shared_status, s.shared_notes, s.last_updated_by, s.created_at as shared_at, s.updated_at,
                           l.id as lead_id, l.full_name as name, l.phone_number as phone, l.email, l.status as original_status
                    FROM shared_leads s
                    JOIN leads l ON l.id::text = s.lead_id
                    WHERE s.from_user = %s
                    ORDER BY s.created_at DESC
                """, (user_id,))
                leads = [dict(row) for row in cur.fetchall()]
                cur.close()
                return leads
            except Exception as e:
                print(f"Get sent leads error: {e}")
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                shared = db_module.supabase.table("shared_leads").select("*").eq("from_user", user_id).execute()
                result = []
                for s in shared.data:
                    lead = db_module.supabase.table("leads").select("*").eq("id", s["lead_id"]).execute()
                    if lead.data:
                        result.append({**s, **lead.data[0]})
                return result
            except:
                pass
        
        sent = [s for s in db_module.LOCAL_DB["shared_leads"] if s.get("from_user") == user_id]
        return sent
    
    @staticmethod
    def get_shared_leads(user_id: str) -> List[Dict]:
        """Get leads shared with user including status"""
        if db_module.DB_TYPE == "replit_pg" and db_module.pg_conn:
            try:
                from psycopg2.extras import RealDictCursor
                cur = db_module.pg_conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("""
                    SELECT s.id as share_id, s.from_user, s.shared_status, s.shared_notes, s.last_updated_by, s.created_at as shared_at, s.updated_at,
                           l.id as lead_id, l.full_name as name, l.phone_number as phone, l.email, l.status as original_status, l.source, l.notes as lead_notes
                    FROM shared_leads s
                    JOIN leads l ON l.id::text = s.lead_id
                    WHERE s.to_user = %s
                    ORDER BY s.created_at DESC
                """, (user_id,))
                leads = [dict(row) for row in cur.fetchall()]
                cur.close()
                return leads
            except Exception as e:
                print(f"Get shared leads error: {e}")
        
        elif db_module.DB_TYPE == "supabase" and db_module.supabase:
            try:
                shared = db_module.supabase.table("shared_leads").select("*").eq("to_user", user_id).execute()
                result = []
                for s in shared.data:
                    lead = db_module.supabase.table("leads").select("*").eq("id", s["lead_id"]).execute()
                    if lead.data:
                        result.append({**s, **lead.data[0]})
                return result
            except:
                pass
        
        result = []
        for s in db_module.LOCAL_DB["shared_leads"]:
            if s.get("to_user") == user_id:
                for l in db_module.LOCAL_DB["leads"]:
                    if l.get("id") == s.get("lead_id"):
                        result.append({**s, **l})
                        break
        return result
