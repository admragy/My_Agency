"""
Hunter Pro CRM - Modular Entry Point
FastAPI application with modular architecture
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.security import rate_limit

try:
    from app.api.routes import auth_router, chat_router, leads_router, admin_router
except ImportError:
    auth_router = chat_router = leads_router = admin_router = None

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        allowed, msg = rate_limit(client_ip)
        
        if not allowed:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": msg}, status_code=429)
        
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None
)

app.add_middleware(SecurityMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

if auth_router:
    app.include_router(auth_router)
if chat_router:
    app.include_router(chat_router)
if leads_router:
    app.include_router(leads_router)
if admin_router:
    app.include_router(admin_router)

if os.path.exists("templates"):
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve main page"""
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "app": settings.APP_NAME
    }


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    init_db()
    print(f"🚀 {settings.APP_NAME} v{settings.VERSION} started!")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
