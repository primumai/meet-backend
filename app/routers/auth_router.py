from fastapi import APIRouter, HTTPException, Depends, status, Header
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from jose.exceptions import ExpiredSignatureError
from jose import JWTError
from app.database import get_db
from app.models.user_model import User, UserRole
from app.schemas.auth_schema import UserSignupSchema, UserLoginSchema, TokenResponseSchema, UserResponseSchema
from app.utils.jwt_utils import create_access_token, decode_access_token
from app.utils.password_utils import hash_password, verify_password

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


@router.get("/profile", response_model=UserResponseSchema)
def get_profile(
    authorization: str | None = Header(None, alias="Authorization"),
    db: Session = Depends(get_db)
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

