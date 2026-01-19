from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.room_model import Room
from app.models.user_model import User
from app.models.company_model import Company
from app.schemas.room_schema import (
    CreateRoomSchema, 
    RoomResponseSchema,
    GetTokenSchema,
    TokenResponseSchema,
    RoomWithUserResponseSchema
)
from app.services.videosdk_service import VideoSDKService
from app.utils.auth_dependencies import get_current_user

router = APIRouter()


@router.post("/create", response_model=RoomResponseSchema, status_code=status.HTTP_201_CREATED)
def create_room(
    room_data: CreateRoomSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new room using VideoSDK API
    
    - **apikey**: API key for company authentication (required)
    - **permissions**: Object containing room feature permissions
    - **maximum_participants**: Maximum number of participants (1-100)
    - **start_time**: Optional room start time
    - **end_time**: Optional room end time
    
    Returns the created room with meeting link.
    """
    try:
        # Validate API key
        # company = db.query(Company).filter(Company.apikey == room_data.apikey).first()
        
        # if not company:
        #     raise HTTPException(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         detail="Invalid API key. Access denied."
        #     )
        
        # Create room using VideoSDK API
        videosdk_room = VideoSDKService.create_room(
            max_participants=room_data.maximum_participants
        )
        
        room_id = videosdk_room.get("roomId")
        
        if not room_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get room ID from VideoSDK"
            )
        
        # Generate meeting link
        meeting_link = VideoSDKService.get_meeting_link(room_id)
        
        # Create room record in database
        new_room = Room(
            room_id=room_id,
            user_id=current_user.id,
            start_time=room_data.start_time,
            end_time=room_data.end_time,
            permissions=room_data.permissions,
            maximum_participants=room_data.maximum_participants
        )
        
        db.add(new_room)
        db.commit()
        db.refresh(new_room)
        
        # Return room response with meeting link
        return {
            "id": new_room.id,
            "room_id": new_room.room_id,
            "user_id": new_room.user_id,
            "start_time": new_room.start_time,
            "end_time": new_room.end_time,
            "permissions": new_room.permissions,
            "maximum_participants": new_room.maximum_participants,
            "meeting_link": meeting_link,
            "created_at": new_room.created_at,
            "updated_at": new_room.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating room: {str(e)}"
        )


@router.post("/{room_id}/get-token", response_model=TokenResponseSchema)
def get_meeting_token(
    room_id: str,
    token_data: GetTokenSchema,
    db: Session = Depends(get_db)
):
    """
    Get a meeting token for joining a room
    
    - **room_id**: The VideoSDK room ID (path parameter)
    - **participant_name**: Name of the participant joining
    - **participant_identity**: Unique identity of the participant (used as participantId)
    - **permissions**: List of permissions - ['allow_join'] or ['ask_join'] or ['allow_mod'] (optional, default: ['allow_join'])
    - **roles**: List of roles - ['crawler', 'rtc'] (optional)
    - **version**: Token version (optional, default: 2)
    
    Returns a JWT token that can be used to join the meeting.
    """
    try:
        # Verify that the room exists in the database
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room with ID '{room_id}' not found"
            )
        
        # Generate meeting token using VideoSDK service with correct payload structure
        token = VideoSDKService.generate_videosdk_token(
            room_id=room_id,
            participant_id=token_data.participant_identity,
        )
        
        return {
            "token": token
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating meeting token: {str(e)}"
        )


@router.get("/{room_id}", response_model=RoomWithUserResponseSchema)
def get_room_by_id(
    room_id: str,
    db: Session = Depends(get_db)
):
    """
    Get room details by room ID including user details
    
    - **room_id**: The VideoSDK room ID (path parameter)
    
    Returns room details with user information (creator of the room).
    """
    try:
        # Query room with user relationship (eager loading)
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Room with ID '{room_id}' not found"
            )
        
        # Generate meeting link
        meeting_link = VideoSDKService.get_meeting_link(room.room_id)
        
        # Return room with user details
        return {
            "id": room.id,
            "room_id": room.room_id,
            "user_id": room.user_id,
            "start_time": room.start_time,
            "end_time": room.end_time,
            "permissions": room.permissions,
            "maximum_participants": room.maximum_participants,
            "meeting_link": meeting_link,
            "created_at": room.created_at,
            "updated_at": room.updated_at,
            "user": {
                "id": room.user.id,
                "name": room.user.name,
                "email": room.user.email,
                "role": room.user.role.value,
                "is_active": room.user.is_active,
                "created_at": room.user.created_at,
                "updated_at": room.user.updated_at
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching room: {str(e)}"
        )

