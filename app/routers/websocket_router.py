from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Store active connections (optional - for tracking)
active_connections: set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint that handles connection and disconnection events only.
    """
    # Accept the WebSocket connection
    await websocket.accept()
    logger.info(f"WebSocket client connected: {websocket.client}")
    
    # Add to active connections set
    active_connections.add(websocket)
    
    try:
        # Keep the connection alive
        # This loop will run until the client disconnects
        while True:
            # Wait for any message (we're not processing it, just keeping connection alive)
            # If client disconnects, this will raise WebSocketDisconnect
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        # Handle disconnection
        logger.info(f"WebSocket client disconnected: {websocket.client}")
        active_connections.discard(websocket)
        
    except Exception as e:
        # Handle any other errors
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)
        await websocket.close()

