from fastapi import FastAPI
# from app.routers.link_router import router as link_router
# from app.routers.meeting_router import router as meeting_router
from app.routers.auth_router import router as auth_router
from app.routers.room_router import router as room_router
from app.routers.websocket_router import router as websocket_router
from app.database import engine, Base
from app.models import User, Room  # Import models to ensure tables are created

# Create database tables
Base.metadata.create_all(bind=engine)

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
app.include_router(websocket_router, tags=["WebSocket"])
# app.include_router(link_router, prefix="/links")
# app.include_router(meeting_router, prefix="/meetings")
