import redis
import json
from typing import Optional, List, Dict
from app.config import settings

# Redis client instance
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            db=settings.REDIS_DB,
            decode_responses=True
        )
        # Test connection
        try:
            _redis_client.ping()
        except redis.ConnectionError:
            raise ConnectionError("Failed to connect to Redis server")
    return _redis_client


def add_to_waiting_room(meeting_id: str, socket_id: str, participant_data: Dict[str, str]) -> bool:
    """
    Add a participant to the waiting room in Redis
    
    Args:
        meeting_id: The meeting ID
        socket_id: The socket ID of the participant
        participant_data: Dictionary containing participantId and name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_redis_client()
        key = f"waiting_room:{meeting_id}"
        
        participant_info = {
            "socketId": socket_id,
            "participantId": participant_data.get("participantId"),
            "name": participant_data.get("name"),
            "requestedAt": str(int(__import__("time").time() * 1000))  # Current timestamp in milliseconds
        }
        
        # Store participant data as JSON
        client.hset(key, socket_id, json.dumps(participant_info))
        
        # Set expiration for the waiting room (24 hours)
        client.expire(key, 86400)
        
        return True
    except Exception as e:
        print(f"[Redis] Error adding to waiting room: {e}")
        return False


def remove_from_waiting_room(meeting_id: str, socket_id: str) -> Optional[Dict]:
    """
    Remove a participant from the waiting room
    
    Args:
        meeting_id: The meeting ID
        socket_id: The socket ID of the participant
        
    Returns:
        Participant data if found, None otherwise
    """
    try:
        client = get_redis_client()
        key = f"waiting_room:{meeting_id}"
        
        # Get participant data before removing
        participant_json = client.hget(key, socket_id)
        
        if participant_json:
            participant_data = json.loads(participant_json)
            # Remove from Redis
            client.hdel(key, socket_id)
            return participant_data
        
        return None
    except Exception as e:
        print(f"[Redis] Error removing from waiting room: {e}")
        return None


def get_waiting_room_participants(meeting_id: str) -> List[Dict]:
    """
    Get all participants in the waiting room for a meeting
    
    Args:
        meeting_id: The meeting ID
        
    Returns:
        List of participant dictionaries
    """
    try:
        client = get_redis_client()
        key = f"waiting_room:{meeting_id}"
        
        # Get all participants from the hash
        participants_data = client.hgetall(key)
        
        participants = []
        for socket_id, participant_json in participants_data.items():
            try:
                participant = json.loads(participant_json)
                participants.append(participant)
            except json.JSONDecodeError:
                continue
        
        return participants
    except Exception as e:
        print(f"[Redis] Error getting waiting room participants: {e}")
        return []

