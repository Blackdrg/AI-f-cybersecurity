import os
import sys
import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("desktop_backend")

# Set default environment variables for desktop mode
os.environ["IS_DESKTOP"] = "true"
if not os.getenv("DB_URL"):
    # Default to local SQLite in user data directory or current dir
    app_data = os.getenv("APPDATA", os.getcwd())
    db_path = os.path.join(app_data, "AI-F-Desktop", "data.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    logger.info(f"Using local SQLite database at {db_path}")

if not os.getenv("REDIS_URL"):
    os.environ["USE_FAKE_REDIS"] = "true"
    logger.info("Using fake Redis for local operation")

# Import the main app
# We need to make sure the backend directory is in the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Path to the 'app' directory if we are running from the parent
app_path = os.path.join(backend_dir, "app")
if os.path.exists(app_path) and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    from app.main import app
except ImportError as e:
    logger.error(f"Failed to import app.main: {e}")
    # Try adding one level up
    sys.path.insert(0, os.path.dirname(backend_dir))
    from app.main import app

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    host = "127.0.0.1" # Only allow local connections for security
    
    logger.info(f"Starting desktop backend on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        workers=1 # Desktop only needs 1 worker
    )

if __name__ == "__main__":
    main()
