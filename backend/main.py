import uvicorn
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.endpoints import github_webhooks, deployments, sse, windsurf
from app.core.config import settings
from app.core.auth import get_current_user, get_optional_user
from app.models.user import User

app = FastAPI(
    title="OrbitHost API",
    description="API for OrbitHost - AI-native hosting platform",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you would restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(github_webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(deployments.router, prefix="/deployments", tags=["deployments"])
app.include_router(sse.router, prefix="/sse", tags=["sse"])
app.include_router(windsurf.router, prefix="/api/windsurf", tags=["windsurf"])

# Set up metrics (Phase 1 of monitoring implementation)
Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health_check():
    """Health check endpoint required by monitoring standards"""
    return {"status": "healthy"}

@app.get("/api/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get information about the currently authenticated user"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": f"{current_user.first_name or ''} {current_user.last_name or ''}".strip(),
        "subscription": {
            "tier": current_user.subscription.tier,
            "status": current_user.subscription.status,
            "custom_domains_allowed": current_user.subscription.custom_domains_allowed,
            "team_members_allowed": current_user.subscription.team_members_allowed
        }
    }

@app.get("/api/user-status")
async def get_user_status(user: User = Depends(get_optional_user)):
    """Get user status - works for both authenticated and unauthenticated users"""
    if user:
        return {"authenticated": True, "user_id": user.id}
    return {"authenticated": False}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
