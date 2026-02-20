from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
 
from app.config import settings
from app.database import get_db
from app.models.user_model import User
 
# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
 



 
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
 
    Args:
        token: The JWT token from the Authorization header
        db: Database session
 
    Returns:
        User: The authenticated user
 
    Raises:
        HTTPException: If the token is invalid or the user doesn't exist
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
 
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
 
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
 
    return user

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

