import bcrypt
import hashlib


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    Bcrypt has a 72-byte limit, so we first hash with SHA256 to ensure
    the input is always a fixed 64-byte hex string (within the limit)
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password (bcrypt hash as string)
    """
    # First hash with SHA256 to get a fixed 64-byte hex string
    # This ensures we're always within bcrypt's 72-byte limit
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    # Convert to bytes for bcrypt
    password_bytes = sha256_hash.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password (bcrypt hash)
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Hash the plain password with SHA256 first
        sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
        password_bytes = sha256_hash.encode('utf-8')
        # Verify against the stored hash
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

