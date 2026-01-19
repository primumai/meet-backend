from datetime import datetime, timedelta
from jose import JWTError, jwt
from app.config import settings


def create_access_token(user_id: str, role: str, token_type: str = "login") -> str:
    """
    Create a JWT token with user_id, role, exp, and token_type
    
    Args:
        user_id: The user's ID (UUID as string)
        role: The user's role
        token_type: Either "signup" or "login"
    
    Returns:
        Encoded JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode = {
        "user_id": str(user_id),  # Ensure it's a string
        "role": role,
        "exp": expire,
        "token_type": token_type
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        Decoded token payload (e.g. user_id, role, exp, token_type).

    Raises:
        ExpiredSignatureError: If the token has expired.
        JWTError: If the token is invalid (bad signature, malformed, etc.).
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )

