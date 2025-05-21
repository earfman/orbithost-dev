import logging
import uvicorn
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Set up path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Starting OrbitHost API")

# Import API routers - wrapped in try/except to handle potential import errors
try:
    from app.api.endpoints import users_db, context_api
    logger.info("Successfully imported API endpoints")
except ImportError as e:
    logger.warning(f"Could not import API endpoints: {e}")
    users_db = None
    context_api = None

# Create FastAPI app
app = FastAPI(
    title="OrbitHost API",
    description="API for OrbitHost - AI-native hosting platform",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers if available
if users_db is not None:
    logger.info("Including users_db router")
    app.include_router(users_db.router)

if context_api is not None:
    logger.info("Including context_api router")
    app.include_router(context_api.router)

# Health check endpoint for Fly.io
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Root endpoint to show the app is working
@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
        <head>
            <title>OrbitHost - Deployed Successfully</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 100vh; 
                    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                    color: white;
                }
                .container {
                    text-align: center;
                    padding: 2rem;
                    border-radius: 10px;
                    background-color: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    max-width: 600px;
                }
                h1 { color: #4cc9f0; }
                .status { 
                    display: inline-block;
                    background-color: #4cc9f0; 
                    color: #1a1a2e;
                    padding: 0.5rem 1rem;
                    border-radius: 20px;
                    font-weight: bold;
                    margin: 1rem 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>OrbitHost</h1>
                <div class="status">Successfully Deployed ✅</div>
                <p>Your application is now running on Fly.io</p>
                <p>This is a placeholder page. Replace it with your actual frontend.</p>
            </div>
        </body>
    </html>
    """

# MCP server endpoint
@app.get("/mcp")
def mcp_info():
    return {
        "status": "available",
        "version": "0.1.0",
        "description": "Model Context Protocol server for OrbitHost"
    }

# Debug endpoint to show environment information
@app.get("/debug")
def debug_info():
    return {
        "python_version": sys.version,
        "environment": dict(os.environ),
        "cwd": os.getcwd(),
        "directory_contents": os.listdir("."),
        "backend_contents": os.listdir("/app/backend") if os.path.exists("/app/backend") else "Not found"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """
    Startup event handler.
    
    This function is called when the application starts up.
    """
    logger.info("Starting OrbitHost API")
    
    # Initialize Supabase connection
    try:
        from app.db.supabase_client import get_supabase_client
        client = await get_supabase_client()
        logger.info("Supabase connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase connection: {str(e)}")
        
    # Initialize OrbitContext store
    try:
        from app.services.orbitbridge.context_store import get_context_store
        store = await get_context_store()
        logger.info("OrbitContext store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize OrbitContext store: {str(e)}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """
    Shutdown event handler.
    
    This function is called when the application shuts down.
    """
    logger.info("Shutting down OrbitHost API")

# Run the app if this file is executed directly
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
