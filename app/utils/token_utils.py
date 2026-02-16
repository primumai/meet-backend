import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings

def generate_reset_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token for password reset.
    
    Args:
        length: Length of the token to generate (default: 32)
        
    Returns:
        str: A URL-safe base64-encoded random token
    """
    # Generate a secure random string using URL-safe characters
    alphabet = string.ascii_letters + string.digits + '-_'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def get_token_expiration() -> datetime:
    """
    Get the expiration datetime for a reset token.
    
    Returns:
        datetime: The expiration datetime
    """
    return datetime.utcnow() + timedelta(minutes=settings.RESET_PASSWORD_EXPIRE_MINUTES)

def is_token_expired(expires_at: datetime) -> bool:
    """
    Check if a token is expired.
    
    Args:
        expires_at: The expiration datetime of the token
        
    Returns:
        bool: True if the token is expired, False otherwise
    """
    return datetime.utcnow() > expires_at
