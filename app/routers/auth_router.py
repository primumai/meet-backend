from fastapi import APIRouter, HTTPException, Depends, status, Header, BackgroundTasks, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, NoResultFound
from jose.exceptions import ExpiredSignatureError
from jose import JWTError
from typing import Optional
import logging

from app.database import get_db
from app.models.user_model import User, UserRole
from app.models.reset_password_model import ResetPassword
from app.schemas.auth_schema import UserSignupSchema, UserLoginSchema, TokenResponseSchema, UserResponseSchema
from app.schemas.reset_password_schema import (
    ResetPasswordRequest, 
    ResetPasswordConfirm, 
    ResetPasswordResponse
)
from app.utils.jwt_utils import create_access_token, decode_access_token
from app.utils.password_utils import hash_password, verify_password
from app.utils.email_utils import send_password_reset_email
from app.utils.token_utils import generate_reset_token, get_token_expiration, is_token_expired
from app.config import settings

# Security schemes for Swagger UI
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="x-api-key", auto_error=False, description="Use the API key for company authentication. Send user_id in the request body for POST APIs, and for GET APIs, send user_id in the query parameter like ?user_id=123absc.")

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/signup", response_model=TokenResponseSchema, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignupSchema, db: Session = Depends(get_db)):
    """
    User signup endpoint
    
    Creates a new user and returns a JWT token with token_type: "signup"
    """
    try:
        # Check if user with email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash the password
        hashed_password = hash_password(user_data.password)
        
        # Create new user
        new_user = User(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            role=UserRole.HOST,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create JWT token with token_type: "signup"
        access_token = create_access_token(
            user_id=new_user.id,
            role=new_user.role.value,
            token_type="signup"
        )
        
        return {
            "access_token": access_token,
            "token_type": "signup",
            "user_id": new_user.id,
            "role": new_user.role.value
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like "Email already registered")
        raise
    except IntegrityError as e:
        # Handle database integrity errors (e.g., unique constraint violations)
        db.rollback()
        if "email" in str(e).lower() or "unique" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create account. Please try again."
        )
    except SQLAlchemyError as e:
        # Handle other database errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred. Please try again later."
        )
    except Exception as e:
        # Handle any other unexpected errors
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during signup. Please try again."
        )


@router.post("/login", response_model=TokenResponseSchema)
def login(user_data: UserLoginSchema, db: Session = Depends(get_db)):
    """
    User login endpoint
    
    Authenticates user and returns a JWT token with token_type: "login"
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == user_data.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Verify password
        if not verify_password(user_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Password mismatch"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        # Create JWT token with token_type: "login"
        access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            token_type="login"
        )
        
        return {
            "access_token": access_token,
            "token_type": "login",
            "user_id": user.id,
            "role": user.role.value
        }
    except HTTPException:
        # Re-raise HTTP exceptions (like authentication errors)
        raise
    except SQLAlchemyError as e:
        # Handle database errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred. Please try again later."
        )
    except Exception as e:
        # Handle any other unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login. Please try again."
        )


@router.post("/request-password-reset", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
async def request_password_reset(
    request: ResetPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request a password reset link to be sent to the user's email.
    
    - **email**: The email address of the user requesting a password reset
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            # For security reasons, don't reveal that the email doesn't exist
            logger.info(f"Password reset requested for non-existent email: {request.email}")
            return {"message": "If your email is registered, you will receive a password reset link."}
        
        # Invalidate any existing reset tokens for this user
        db.query(ResetPassword).filter(
            ResetPassword.user_id == user.id,
            ResetPassword.expires_at > datetime.utcnow()
        ).delete(synchronize_session=False)
        
        # Generate a new reset token
        reset_token = generate_reset_token()
        expires_at = get_token_expiration()
        
        # Create reset password record
        reset_password = ResetPassword(
            email=user.email,
            reset_token=reset_token,
            expires_at=expires_at,
            user_id=user.id
        )
        
        db.add(reset_password)
        db.commit()
        
        # Send password reset email in background
        background_tasks.add_task(
            send_password_reset_email,
            recipient_email=user.email,
            reset_token=reset_token,
            username=user.name
        )
        
        logger.info(f"Password reset token generated for user {user.id}")
        return {
            "message": "If your email is registered, you will receive a password reset link.",
            "reset_token": reset_token  # For testing, in production this should not be returned
        }
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during password reset request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request."
        )
    except Exception as e:
        logger.error(f"Unexpected error during password reset request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.post("/reset-password", response_model=ResetPasswordResponse, status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: ResetPasswordConfirm,
    db: Session = Depends(get_db)
):
    """
    Reset user's password using a valid reset token.
    
    - **token**: The reset token received via email
    - **new_password**: The new password to set
    """
    try:
        # Find the reset token
        reset_record = db.query(ResetPassword).filter(
            ResetPassword.reset_token == reset_data.token
        ).first()
        
        # Check if token exists and is not expired
        if not reset_record or is_token_expired(reset_record.expires_at):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token."
            )
        
        # Find the user
        user = db.query(User).filter(User.email == reset_record.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        
        # Update the user's password
        hashed_password = hash_password(reset_data.new_password)
        user.password = hashed_password
        
        # Delete the used reset token
        db.delete(reset_record)
        
        db.commit()
        
        logger.info(f"Password reset successful for user {user.id}")
        return {"message": "Password has been reset successfully."}
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error during password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting your password."
        )
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later."
        )


@router.get("/profile", response_model=UserResponseSchema)
async def get_profile(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db),
    bearer_token: HTTPAuthorizationCredentials = Security(bearer_scheme),
    api_key: str = Security(api_key_scheme)
):
    """
    Get current user profile from JWT token.

    - **Authorization**: Bearer token in the `Authorization` header.

    - If token is **valid**: returns the user profile (id, name, email, role, is_active, created_at, updated_at).
    - If token is **expired**: returns 401 with detail `Token expired`.
    - If token is **invalid** or missing: returns 401 with detail `Invalid token`.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    try:
        payload = decode_access_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

    return user


@router.get("/user/{user_id}", response_model=UserResponseSchema)
def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user details by user ID

    - **user_id**: The UUID of the user

    Returns user details including name, email, role, and status.
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found"
        )
    
    return user

