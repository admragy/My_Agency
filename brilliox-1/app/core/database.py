"""Database Connection Manager"""
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, Any
from .config import settings

# Global connections
pg_conn: Optional[Any] = None
supabase_client: Optional[Any] = None
supabase: Optional[Any] = None
DB_TYPE: str = "local"
db_type: str = "local"

# Local storage fallback
local_db: Dict[str, Any] = {
    "users": {},
    "leads": [],
    "chat_history": [],
    "campaigns": [],
    "ads": [],
    "shared_leads": [],
    "feedback": [],
    "uploads": []
}
LOCAL_DB = local_db


def execute_query(query: str, params: tuple = None) -> Any:
    """Execute a query on the database"""
    if pg_conn:
        try:
            cur = pg_conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params or ())
            result = cur.fetchall() if cur.description else None
            cur.close()
            return result
        except Exception as e:
            print(f"Query error: {e}")
    return None


def init_postgres() -> bool:
    """Initialize PostgreSQL connection"""
    global pg_conn, db_type, DB_TYPE
    
    if not settings.DATABASE_URL:
        return False
    
    try:
        pg_conn = psycopg2.connect(settings.DATABASE_URL)
        pg_conn.autocommit = True
        
        with pg_conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    password VARCHAR(255),
                    wallet_balance INTEGER DEFAULT 100,
                    is_admin BOOLEAN DEFAULT FALSE,
                    industry VARCHAR(100),
                    language VARCHAR(10) DEFAULT 'ar',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS leads (
                    id VARCHAR(100) PRIMARY KEY,
                    user_id VARCHAR(100),
                    full_name VARCHAR(255),
                    phone_number VARCHAR(50),
                    email VARCHAR(255),
                    source VARCHAR(255),
                    notes TEXT,
                    status VARCHAR(50) DEFAULT 'NEW',
                    quality VARCHAR(50) DEFAULT 'جيد ⭐',
                    funnel_stage VARCHAR(50),
                    tags JSONB DEFAULT '{}',
                    is_favorite BOOLEAN DEFAULT FALSE,
                    last_contact TIMESTAMP,
                    next_followup TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100),
                    message TEXT,
                    response TEXT,
                    tokens_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS feedback (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100),
                    lead_id VARCHAR(100),
                    rating INTEGER,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS shared_leads (
                    id SERIAL PRIMARY KEY,
                    from_user VARCHAR(100),
                    to_user VARCHAR(100),
                    lead_id VARCHAR(100),
                    shared_status VARCHAR(50) DEFAULT 'new',
                    shared_notes TEXT,
                    last_updated_by VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS ai_patterns (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100),
                    pattern_type VARCHAR(50),
                    trigger_text TEXT,
                    response_text TEXT,
                    success_count INTEGER DEFAULT 1,
                    fail_count INTEGER DEFAULT 0,
                    confidence FLOAT DEFAULT 0.5,
                    stage VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE TABLE IF NOT EXISTS conversation_imports (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(100),
                    platform VARCHAR(50),
                    conversation_data JSONB,
                    rating INTEGER,
                    is_successful BOOLEAN DEFAULT FALSE,
                    patterns_extracted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        
        print("✅ Connected to PostgreSQL")
        db_type = "replit_pg"
        DB_TYPE = "replit_pg"
        return True
        
    except Exception as e:
        print(f"⚠️ PostgreSQL error: {e}")
        return False


def init_supabase() -> bool:
    """Initialize Supabase connection"""
    global supabase_client, supabase, db_type, DB_TYPE
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        return False
    
    try:
        from supabase import create_client
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        supabase = supabase_client
        supabase_client.table("users").select("username").limit(1).execute()
        print("✅ Connected to Supabase")
        db_type = "supabase"
        DB_TYPE = "supabase"
        return True
    except Exception as e:
        print(f"⚠️ Supabase error: {e}")
        return False


def init_db() -> str:
    """Initialize database - try PostgreSQL first, then Supabase, then local"""
    if init_postgres():
        return "postgres"
    if init_supabase():
        return "supabase"
    print("💡 Using local storage (temporary)")
    return "local"


def get_db():
    """Get database connection"""
    return {
        "type": db_type,
        "pg": pg_conn,
        "supabase": supabase_client,
        "local": local_db
    }
