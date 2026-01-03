import requests
from typing import Dict, Any, Optional, List
from app.config import settings
from fastapi import HTTPException, status
import jwt  # PyJWT for VideoSDK token generation
from datetime import datetime, timedelta


class VideoSDKService:
    """Service for interacting with VideoSDK API"""
    
    BASE_URL = "https://api.videosdk.live/v2"
    
    @staticmethod
    def generate_videosdk_token(
        room_id: Optional[str] = None,
        participant_id: Optional[str] = None,
    ) -> str:
        """
        Generate JWT token for VideoSDK API authentication or meeting participation
        
        Args:
            room_id: The VideoSDK room ID (OPTIONAL)
            participant_id: Unique identity of the participant (OPTIONAL)
        
        Returns:
            JWT token string
        """
        # Build payload according to VideoSDK specification
        payload = {
            "apikey": settings.VIDEOSDK_API_KEY,  # MANDATORY
            "permissions": ["allow_join"],  # MANDATORY
            "version": 2,
            "roles": ["CRAWLER", "RTCPEER"],
            "exp": datetime.utcnow() + timedelta(hours=24)
        }

        
        if room_id:
            payload["roomId"] = room_id
        
        if participant_id:
            payload["participantId"] = participant_id
        
        token = jwt.encode(
            payload,
            settings.VIDEOSDK_API_SECRET,
            algorithm="HS256"
        )
        
        # Ensure token is a string (PyJWT returns string by default, but ensure compatibility)
        return str(token)
    
    @staticmethod
    def create_room(max_participants: int = 10) -> Dict[str, Any]:
        """
        Create a room using VideoSDK API
        
        Args:
            max_participants: Maximum number of participants allowed in the room
            
        Returns:
            Dictionary containing roomId and other room details
            
        Raises:
            HTTPException: If room creation fails
        """
        try:
            # Generate authentication token
            token = VideoSDKService.generate_videosdk_token()
            
            # Prepare request
            url = f"{VideoSDKService.BASE_URL}/rooms"
            headers = {
                "Authorization": token,
                "Content-Type": "application/json"
            }
            payload = {
                "max_participants": max_participants
            }
            
            # Make API request
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code != 200:
                error_detail = response.json().get("error", "Failed to create room")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"VideoSDK API error: {error_detail}"
                )
            
            room_data = response.json()
            
            if "roomId" not in room_data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="VideoSDK API did not return roomId"
                )
            
            return room_data
            
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to connect to VideoSDK API: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating room: {str(e)}"
            )
    
    @staticmethod
    def get_meeting_link(room_id: str) -> str:
        """
        Generate meeting link for a room
        
        Args:
            room_id: The VideoSDK room ID
            
        Returns:
            Meeting link URL
        """
        return f"https://app.videosdk.live/meeting/{room_id}"

