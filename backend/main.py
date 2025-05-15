import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import router as api_router
from app.core.config import settings

app = FastAPI(
    title="OrbitHost API",
    description="AI-Native Hosting Platform API",
    version="0.1.0",
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add routes
app.include_router(api_router, prefix="/api")

# Set up metrics (Phase 1 of monitoring implementation)
Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health_check():
    """Health check endpoint required by monitoring standards"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
