from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.company_model import Company
from app.schemas.company_schema import CreateCompanySchema, CompanyResponseSchema
import secrets
import string

router = APIRouter()


def generate_apikey() -> str:
    """
    Generate a secure API key for companies
    Returns a URL-safe random string of 32 characters
    """
    # Generate a secure random string using secrets module
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


@router.post("/create", response_model=CompanyResponseSchema, status_code=status.HTTP_201_CREATED)
def create_company(
    company_data: CreateCompanySchema,
    db: Session = Depends(get_db)
):
    """
    Create a new company
    
    - **company_name**: Company name (required)
    - **email**: Company email address (optional)
    - **contact**: Company contact information (optional)
    - **location**: Company location (optional)
    
    Returns the created company with auto-generated API key.
    """
    try:
        # Check if company with same name already exists
        existing_company = db.query(Company).filter(
            Company.company_name == company_data.company_name
        ).first()
        
        if existing_company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Company with this name already exists"
            )
        
        # Generate unique API key
        apikey = generate_apikey()
        
        # Ensure API key is unique (very unlikely but check anyway)
        while db.query(Company).filter(Company.apikey == apikey).first():
            apikey = generate_apikey()
        
        # Create new company
        new_company = Company(
            company_name=company_data.company_name,
            email=company_data.email,
            contact=company_data.contact,
            location=company_data.location,
            apikey=apikey
        )
        
        db.add(new_company)
        db.commit()
        db.refresh(new_company)
        
        return new_company
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating company: {str(e)}"
        )


@router.get("/{company_id}", response_model=CompanyResponseSchema)
def get_company_by_id(
    company_id: str,
    db: Session = Depends(get_db)
):
    """
    Get company details by company ID
    
    - **company_id**: The UUID of the company
    
    Returns company details including API key.
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{company_id}' not found"
            )
        
        return company
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching company: {str(e)}"
        )


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a company by company ID
    
    - **company_id**: The UUID of the company
    
    Returns 204 No Content on successful deletion.
    """
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with ID '{company_id}' not found"
            )
        
        db.delete(company)
        db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting company: {str(e)}"
        )
