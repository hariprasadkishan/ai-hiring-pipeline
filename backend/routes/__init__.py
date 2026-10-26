from .auth_routes import router as auth_router
from .opening_routes import router as opening_router
from .application_routes import router as application_router

__all__ = [
    "auth_router",
    "opening_router",
    "application_router",
]
