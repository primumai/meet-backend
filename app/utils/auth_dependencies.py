from fastapi import HTTPException, Request, status

from app.models.user_model import User


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

