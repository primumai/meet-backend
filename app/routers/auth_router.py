from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_model import User, UserRole
from app.schemas.auth_schema import UserSignupSchema, UserLoginSchema, TokenResponseSchema, UserResponseSchema
from app.utils.jwt_utils import create_access_token
from app.utils.password_utils import hash_password, verify_password

router = APIRouter()


@router.post("/signup", response_model=TokenResponseSchema, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignupSchema, db: Session = Depends(get_db)):
    """
    User signup endpoint
    
    Creates a new user and returns a JWT token with token_type: "signup"
    """
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


@router.post("/login", response_model=TokenResponseSchema)
def login(user_data: UserLoginSchema, db: Session = Depends(get_db)):
    """
    User login endpoint
    
    Authenticates user and returns a JWT token with token_type: "login"
    """
    # Find user by email
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(user_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
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

