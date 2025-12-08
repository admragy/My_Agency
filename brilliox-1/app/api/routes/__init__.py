"""API Route Modules"""
try:
    from .auth import router as auth_router
    from .chat import router as chat_router
    from .leads import router as leads_router
    from .admin import router as admin_router
except ImportError as e:
    print(f"Route import warning: {e}")
