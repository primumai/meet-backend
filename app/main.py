from fastapi import FastAPI
import socketio
from app.routers.auth_router import router as auth_router
from app.routers.room_router import router as room_router
from app.routers.websocket_router import sio
from app.database import engine, Base
from app.models import User, Room  # Import models to ensure tables are created
from app.config import settings

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

# Mount Socket.IO app
socketio_app = socketio.ASGIApp(sio, app, socketio_path=settings.SOCKETIO_PATH)

# Replace the app with the Socket.IO wrapped app
app = socketio_app
