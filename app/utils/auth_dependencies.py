from fastapi import HTTPException, Request, status

from app.models.user_model import User
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User
from app.models.user_subscription_model import UserSubscription


def get_current_user(request: Request) -> User:
    """
    Dependency to get the current authenticated user.
    Relies on AuthMiddleware: user is set in request.state by JWT or by apiKey + user_id.

    Returns:
        User object

    Raises:
        HTTPException: If no user in request.state (middleware did not authenticate).
    """
    if not hasattr(request.state, "user") or request.state.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return request.state.user


def require_active_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency that ensures the user has a valid (active, not expired) subscription.
    Use on endpoints that require subscription (e.g. create room).

    Raises:
        HTTPException 403: If user has no subscription or subscription is expired.
    """
    now = datetime.now(timezone.utc)
    valid_subscription = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "active",
            (UserSubscription.expired_at.is_(None)) | (UserSubscription.expired_at > now),
        )
        .first()
    )
    if not valid_subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription. Please subscribe to create meeting rooms.",
        )
    return current_user