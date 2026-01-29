from fastapi import FastAPI
import socketio
import logging
import sys
from app.routers.auth_router import router as auth_router
from app.routers.room_router import router as room_router
from app.routers.company_router import router as company_router
from app.routers.subscription_router import router as subscription_router
from app.routers.websocket_router import sio
from app.database import engine, Base
from app.models import User, Room, Company  # Import models to ensure tables are created
from app.config import settings
from app.middleware.auth_middleware import AuthMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set specific loggers to INFO level
logging.getLogger("app").setLevel(logging.INFO)
logging.getLogger("app.routers").setLevel(logging.INFO)
logging.getLogger("app.services").setLevel(logging.INFO)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Meeting App API",
    description="FastAPI application for managing meetings",
    version="1.0.0"
)

# Hello World endpoint
@app.get("/")
def hello_world():
    return {"message": "Hello World"}

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(room_router, prefix="/rooms", tags=["Rooms"])
app.include_router(company_router, prefix="/companies", tags=["Companies"])
app.include_router(subscription_router, tags=["Subscriptions"])

# Auth middleware: JWT (Authorization) or apiKey header + user_id in body/query
app.add_middleware(AuthMiddleware)

# Mount Socket.IO app
socketio_app = socketio.ASGIApp(sio, app, socketio_path=settings.SOCKETIO_PATH)

# Replace the app with the Socket.IO wrapped app
app = socketio_app
