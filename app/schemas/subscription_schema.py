from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from datetime import datetime


class SubscriptionSchema(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    subs_id: str
    price: str
    duration_days: int
    feature_entitlements: Optional[Dict[str, Any] | List[Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSubscriptionSchema(BaseModel):
    id: str
    user_id: str
    subs_id: str
    status: str
    feature_entitlements: Optional[Dict[str, Any] | List[Any]] = None
    expired_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionBasicSchema(BaseModel):
    """Basic subscription fields: name, price, duration_days only."""
    name: str
    price: str
    duration_days: int


class UserSubscriptionWithDetailsSchema(BaseModel):
    """User subscription with nested subscription (name, price, duration_days only)."""
    id: str
    user_id: str
    subs_id: str
    status: str
    feature_entitlements: Optional[Dict[str, Any] | List[Any]] = None
    expired_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    subscription: SubscriptionBasicSchema

    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    success: bool
    message: str
    subscriptions: List[SubscriptionSchema]
    user_subscriptions: Optional[List[UserSubscriptionSchema]] = None


class UserSubscriptionResponse(BaseModel):
    success: bool
    message: str
    user_subscriptions: List[UserSubscriptionSchema]


class UserSubscriptionWithDetailsResponse(BaseModel):
    success: bool
    message: str
    user_subscriptions: List[UserSubscriptionWithDetailsSchema]


class SubscribeRequest(BaseModel):
    user_id: Optional[str] = None
    subs_id: str
    redirectUrl: str
    cancelUrl: str


class SubscribeResponse(BaseModel):
    success: bool
    init_url: str
