import socketio
from typing import Dict
from app.utils.redis_utils import (
    add_to_waiting_room,
    remove_from_waiting_room,
    get_waiting_room_participants
)
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    cors_allowed_origins=settings.CORS_ORIGIN if settings.CORS_ORIGIN != "*" else "*",
    async_mode='asgi'
)

@sio.event
async def connect(sid, environ, auth):
    """
    Handle WebSocket connection
    """
    logger.info(f"[WebSocket] Client connected: {sid}")


@sio.event
async def disconnect(sid):
    """
    Handle WebSocket disconnection
    """
    logger.info(f"[WebSocket] Client disconnected: {sid}")
    # Clean up waiting room entries for this socket
    # Note: Redis TTL will handle cleanup automatically


@sio.on("join-request") 
async def join_request(sid, data: Dict):
    """
    Handle join request from participant
    
    Expected data:
    {
        "meetingId": str,
        "participantId": str,
        "name": str
    }
    """
    print(f"Join request received: {data}")
    logger.warning(f"Join request received: {data}")

    try:
        meeting_id = data.get("meetingId")
        participant_id = data.get("participantId")
        name = data.get("name")
        
        if not meeting_id or not participant_id or not name:
            await sio.emit("error", {"message": "Missing required fields"}, room=sid)
            return
        
        logger.info(f"[WebSocket] Join request received: socketId={sid}, meetingId={meeting_id}, participantId={participant_id}, name={name}")
        
        # Check if participant is already in waiting room
        existing_participants = get_waiting_room_participants(meeting_id)
        already_waiting = any(
            p.get("participantId") == participant_id or p.get("socketId") == sid
            for p in existing_participants
        )
        
        if already_waiting:
            logger.info(f"[WebSocket] ⚠️ Participant already in waiting room, skipping duplicate request: participantId={participant_id}, socketId={sid}")
            await sio.emit("join-request-ack", {
                "socketId": sid,
                "status": "already-waiting"
            }, room=sid)
            return
        
        # Add to waiting room in Redis
        success = add_to_waiting_room(meeting_id, sid, {
            "participantId": participant_id,
            "name": name
        })
        
        if not success:
            await sio.emit("error", {"message": "Failed to add to waiting room"}, room=sid)
            return
        
        # Join socket room for this meeting
        await sio.enter_room(sid, f"meeting:{meeting_id}")
        
        # Notify host about new join request
        await sio.emit("waiting-room-update", {
            "type": "new-request",
            "socketId": sid,
            "participantId": participant_id,
            "name": name,
            "requestedAt": int(__import__("time").time() * 1000)
        }, room=f"host:{meeting_id}")
        
        # Send confirmation to participant
        await sio.emit("join-request-ack", {
            "socketId": sid,
            "status": "waiting"
        }, room=sid)
        
        logger.info(f"[WebSocket] Join request processed, waiting for host approval")
        
    except Exception as error:
        logger.error(f"[WebSocket] Error handling join request: {error}")
        await sio.emit("error", {"message": "Failed to process join request"}, room=sid)


@sio.on("host-join")
async def host_join(sid, data: Dict):
    """
    Handle host joining (to receive waiting room updates)
    
    Expected data:
    {
        "meetingId": str
    }
    """
    try:
        meeting_id = data.get("meetingId")
        
        if not meeting_id:
            await sio.emit("error", {"message": "Meeting ID required"}, room=sid)
            return
        
        logger.info(f"[WebSocket] Host joined: socketId={sid}, meetingId={meeting_id}")
        
        # Join host room
        await sio.enter_room(sid, f"host:{meeting_id}")
        await sio.enter_room(sid, f"meeting:{meeting_id}")
        
        # Send current waiting room participants to host
        participants = get_waiting_room_participants(meeting_id)
        logger.info(f"participants: {participants}")
        
        await sio.emit("waiting-room-snapshot", {
            "participants": [
                {
                    "socketId": p.get("socketId"),
                    "participantId": p.get("participantId"),
                    "name": p.get("name"),
                    "requestedAt": p.get("requestedAt")
                }
                for p in participants
            ]
        }, room=sid)
        
        logger.info(f"[WebSocket] Host connected, sent {len(participants)} waiting participants")
        
    except Exception as error:
        logger.error(f"[WebSocket] Error handling host join: {error}")
        await sio.emit("error", {"message": "Failed to join as host"}, room=sid)


@sio.on("admit-participant")
async def admit_participant(sid, data: Dict):
    """
    Handle admit participant (from host)
    
    Expected data:
    {
        "meetingId": str,
        "socketId": str
    }
    """
    try:
        meeting_id = data.get("meetingId")
        socket_id = data.get("socketId")
        
        if not meeting_id or not socket_id:
            await sio.emit("error", {"message": "Meeting ID and socket ID required"}, room=sid)
            return
        
        logger.info(f"[WebSocket] Admit request: meetingId={meeting_id}, socketId={socket_id}")
        
        # Remove from waiting room
        logger.info(f"[WebSocket] 🔍 Attempting to remove participant from waiting room: meetingId={meeting_id}, socketId={socket_id}")
        participant = remove_from_waiting_room(meeting_id, socket_id)
        
        if not participant:
            logger.error(f"[WebSocket] ❌ Participant not found in waiting room when trying to admit: meetingId={meeting_id}, socketId={socket_id}")
            await sio.emit("error", {"message": "Participant not found in waiting room"}, room=sid)
            return
        
        logger.info(f"[WebSocket] ✅ Participant removed from waiting room successfully: participantId={participant.get('participantId')}, name={participant.get('name')}, socketId={socket_id}")
        
        # Notify participant they've been admitted
        approval_data = {
            "socketId": socket_id,
            "participantId": participant.get("participantId")
        }
        logger.info(f"[WebSocket] Sending join-approved to socket: {socket_id}, Data: {approval_data}")
        
        # Send to specific socket
        await sio.emit("join-approved", approval_data, room=socket_id)
        
        # Also send to meeting room as fallback
        await sio.emit("join-approved", approval_data, room=f"meeting:{meeting_id}")
        
        logger.info(f"[WebSocket] ✅ join-approved event sent to socket: {socket_id} and meeting room: meeting:{meeting_id}")
        
        # Notify host about the admission
        await sio.emit("waiting-room-update", {
            "type": "admitted",
            "socketId": socket_id,
            "participantId": participant.get("participantId"),
            "name": participant.get("name")
        }, room=f"host:{meeting_id}")
        
        logger.info(f"[WebSocket] Participant admitted: {participant.get('participantId')}")
        
    except Exception as error:
        logger.error(f"[WebSocket] Error admitting participant: {error}")
        await sio.emit("error", {"message": "Failed to admit participant"}, room=sid)


@sio.on("deny-participant") 
async def deny_participant(sid, data: Dict):
    """
    Handle deny participant (from host)
    
    Expected data:
    {
        "meetingId": str,
        "socketId": str
    }
    """
    try:
        meeting_id = data.get("meetingId")
        socket_id = data.get("socketId")
        
        if not meeting_id or not socket_id:
            await sio.emit("error", {"message": "Meeting ID and socket ID required"}, room=sid)
            return
        
        logger.info(f"[WebSocket] Deny request: meetingId={meeting_id}, socketId={socket_id}")
        
        # Remove from waiting room
        participant = remove_from_waiting_room(meeting_id, socket_id)
        
        if not participant:
            logger.info(f"[WebSocket] ⚠️ Participant not found in waiting room (may have already been admitted): {socket_id}")
            # Still notify host that denial was attempted
            await sio.emit("waiting-room-update", {
                "type": "denied",
                "socketId": socket_id,
                "participantId": "unknown",
                "name": "Unknown"
            }, room=f"host:{meeting_id}")
            return
        
        # Notify participant they've been denied
        await sio.emit("join-denied", {
            "socketId": socket_id,
            "participantId": participant.get("participantId"),
            "reason": "Host denied your request"
        }, room=socket_id)
        
        # Disconnect the participant
        await sio.disconnect(socket_id)
        logger.info(f"[WebSocket] ✅ Participant denied and disconnected: {participant.get('participantId')}")
        
        # Notify host about the denial
        await sio.emit("waiting-room-update", {
            "type": "denied",
            "socketId": socket_id,
            "participantId": participant.get("participantId"),
            "name": participant.get("name")
        }, room=f"host:{meeting_id}")
        
    except Exception as error:
        logger.error(f"[WebSocket] Error denying participant: {error}")
        await sio.emit("error", {"message": "Failed to deny participant"}, room=sid)


