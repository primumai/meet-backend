from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class RoomPermissionsSchema(BaseModel):
    """Schema for room permissions object"""
    # Add specific permission fields as needed
    # Example: can_share_screen: bool = True
    # Example: can_toggle_mic: bool = True
    # Example: can_toggle_camera: bool = True
    pass


class CreateRoomSchema(BaseModel):
    """Schema for creating a room"""
    permissions: Dict[str, Any] = Field(default_factory=dict, description="Room permissions object")
    maximum_participants: int = Field(default=10, ge=1, le=100, description="Maximum number of participants")
    start_time: Optional[datetime] = Field(None, description="Room start time")
    end_time: Optional[datetime] = Field(None, description="Room end time")


class GetTokenSchema(BaseModel):
    """Schema for getting meeting token"""
    participant_name: str = Field(..., min_length=1, description="Name of the participant")
    participant_identity: str = Field(..., min_length=1, description="Unique identity of the participant")


class TokenResponseSchema(BaseModel):
    """Schema for token response"""
    token: str


class UserDetailsSchema(BaseModel):
    """Schema for user details in room response"""
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomResponseSchema(BaseModel):
    """Schema for room response"""
    id: str
    room_id: str
    user_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    permissions: Dict[str, Any]
    maximum_participants: int
    meeting_link: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoomWithUserResponseSchema(BaseModel):
    """Schema for room response with user details"""
    id: str
    room_id: str
    user_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    permissions: Dict[str, Any]
    maximum_participants: int
    meeting_link: str
    created_at: datetime
    updated_at: datetime
    user: UserDetailsSchema

    class Config:
        from_attributes = True

