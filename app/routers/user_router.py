# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import List
# import logging

# from app.database import get_db
# from app.models.user_model import User
# from app.models.transaction_model import Transaction
# from app.schemas.transaction_schema import TransactionResponseSchema, TransactionListResponse
# from app.schemas.user_schema import UserUpdateSchema
# from app.schemas.auth_schema import UserResponseSchema
# from app.utils.password_utils import hash_password, verify_password
# from app.utils.jwt_utils import get_current_user

# logger = logging.getLogger(__name__)

# router = APIRouter()

# @router.get("/{user_id}/transactions", response_model=TransactionListResponse)
# async def get_user_transactions(
#     user_id: str,
#     skip: int = 0,
#     limit: int = 100,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Get all transactions for a specific user
    
#     - **user_id**: The UUID of the user to get transactions for
#     - **skip**: Number of records to skip (for pagination)
#     - **limit**: Maximum number of records to return (for pagination)
    
#     Returns a list of transactions for the specified user
#     """
#     # Check if the requesting user is the same as the requested user or an admin
#     if str(current_user.id) != user_id and current_user.role != "ADMIN":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access these transactions"
#         )
    
#     # Query transactions for the user
#     query = db.query(Transaction).filter(Transaction.user_id == user_id)
#     total = query.count()
#     transactions = query.offset(skip).limit(limit).all()
    
#     return {
#         "transactions": transactions,
#         "total": total
#     }

# @router.get("/{user_id}", response_model=UserResponseSchema)
# async def get_user_profile(
#     user_id: str,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Get user profile by ID
    
#     - **user_id**: The UUID of the user to get profile for
    
#     Returns the user's profile information
#     """
#     # Check if the requesting user is the same as the requested user or an admin
#     if str(current_user.id) != user_id and current_user.role != "ADMIN":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to access this profile"
#         )
    
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     return user

# @router.patch("/{user_id}", response_model=UserResponseSchema)
# async def update_user_profile(
#     user_id: str,
#     user_data: UserUpdateSchema,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Update user profile
    
#     - **user_id**: The UUID of the user to update
#     - **name**: (Optional) New name
#     - **email**: (Optional) New email
#     - **current_password**: (Required if changing password) Current password
#     - **new_password**: (Optional) New password
#     - **is_active**: (Admin only) Update user active status
    
#     Returns the updated user profile
#     """
#     # Check if the requesting user is the same as the requested user or an admin
#     if str(current_user.id) != user_id and current_user.role != "ADMIN":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Not authorized to update this profile"
#         )
    
#     # Get the user to update
#     user = db.query(User).filter(User.id == user_id).first()
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail="User not found"
#         )
    
#     # Update fields if provided
#     update_data = user_data.dict(exclude_unset=True)
    
#     # Handle password update if new_password is provided
#     if 'new_password' in update_data and update_data['new_password']:
#         if 'current_password' not in update_data or not verify_password(update_data['current_password'], user.password):
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Current password is incorrect"
#             )
#         user.password = hash_password(update_data['new_password'])
    
#     # Update other fields
#     if 'name' in update_data:
#         user.name = update_data['name']
    
#     if 'email' in update_data and update_data['email'] != user.email:
#         # Check if email is already in use
#         existing_user = db.query(User).filter(User.email == update_data['email']).first()
#         if existing_user and existing_user.id != user.id:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Email already in use"
#             )
#         user.email = update_data['email']
    
#     # Only allow admins to update is_active
#     if 'is_active' in update_data and current_user.role == "ADMIN":
#         user.is_active = update_data['is_active']
    
#     try:
#         db.commit()
#         db.refresh(user)
#         return user
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error updating user profile: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error updating user profile"
#         )
