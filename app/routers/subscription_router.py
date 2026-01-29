from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.subscription_model import Subscription
from app.models.user_subscription_model import UserSubscription
from app.models.company_model import Company
from app.models.user_model import User
from app.schemas.subscription_schema import (
    SubscriptionSchema,
    SubscriptionBasicSchema,
    UserSubscriptionSchema,
    UserSubscriptionWithDetailsSchema,
    SubscriptionListResponse,
    UserSubscriptionResponse,
    UserSubscriptionWithDetailsResponse,
    SubscribeRequest,
    SubscribeResponse,
)
from app.utils.jwt_utils import decode_access_token
from app.config import settings
import stripe   

router = APIRouter()


def _require_user_id_from_bearer(request: Request, db: Session) -> str:
    """
    Resolve user_id strictly from Authorization Bearer token.
    Raises HTTPException if missing/invalid.
    """
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token required",
        )
    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user_id
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


def _resolve_user_id_from_token_or_apikey(
    request: Request, db: Session, body_user_id: Optional[str] = None
) -> Optional[str]:
    print(request, "request")
    """
    Resolve a user_id from Authorization Bearer token or apiKey headers.
    Returns None if no auth headers are provided.
    Raises HTTPException on invalid auth inputs.
    """
    auth_header = request.headers.get("authorization")
    api_key = request.headers.get("x-api-key") or request.headers.get("apikey")

    # Prefer Authorization Bearer
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        try:
            payload = decode_access_token(token)
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload",
                )
            # Ensure user exists and is active
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                )
            return user_id
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    # Fallback: apiKey + user_id in query params for this endpoint
    if api_key:
        company = db.query(Company).filter(Company.apikey == api_key.strip()).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key. Access denied.",
            )
        user_id = body_user_id # ✅ FROM BODY
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="When using apiKey, user_id is required as query param (user_id=...).",
            )
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
            )
        return user_id

    # No auth provided
    return None


@router.get("/subscriptions", response_model=SubscriptionListResponse)
def get_subscriptions(request: Request, db: Session = Depends(get_db)):
    """
    Get all subscriptions. Public endpoint.
    If Authorization Bearer token or apiKey+user_id is provided, also returns the user's subscriptions.
    """
    subscriptions: List[Subscription] = db.query(Subscription).all()

    user_subscriptions: Optional[List[UserSubscription]] = None
    user_id = _resolve_user_id_from_token_or_apikey(request, db)
    if user_id:
        user_subscriptions = (
            db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .all()
        )

    return {
        "success": True,
        "message": "Subscriptions fetched successfully",
        "subscriptions": subscriptions,
        "user_subscriptions": user_subscriptions,
    }


@router.get("/subscriptions/user", response_model=UserSubscriptionWithDetailsResponse)
def get_user_subscriptions(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get subscriptions for the authenticated user with subscription details (name, price, duration).
    Requires Authorization Bearer token OR apiKey + user_id (query).
    """
    user_id = _resolve_user_id_from_token_or_apikey(request, db)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization required",
        )

    user_subscriptions = (
        db.query(UserSubscription)
        .filter(UserSubscription.user_id == user_id)
        .all()
    )

    subs_ids = [us.subs_id for us in user_subscriptions]
    subscriptions = (
        db.query(Subscription).filter(Subscription.subs_id.in_(subs_ids)).all()
    )
    sub_by_subs_id = {s.subs_id: s for s in subscriptions}

    result = []
    for us in user_subscriptions:
        sub = sub_by_subs_id.get(us.subs_id)
        result.append(
            UserSubscriptionWithDetailsSchema(
                id=us.id,
                user_id=us.user_id,
                subs_id=us.subs_id,
                status=us.status,
                feature_entitlements=us.feature_entitlements,
                expired_at=us.expired_at,
                created_at=us.created_at,
                updated_at=us.updated_at,
                subscription=SubscriptionBasicSchema(
                    name=sub.name if sub else "",
                    price=sub.price if sub else "",
                    duration_days=sub.duration_days if sub else 0,
                ),
            )
        )

    return {
        "user_subscriptions": result,
        "success": True,
        "message": "User subscriptions fetched successfully",
    }


@router.post("/subscriptions/subscribe", response_model=SubscribeResponse)
def subscribe_package(
    payload: SubscribeRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout session for a subscription purchase.
    Requires Authorization Bearer token. Returns the Stripe init URL.
    """
    user_id = _resolve_user_id_from_token_or_apikey(request, db, payload.user_id)

    subscription = (
        db.query(Subscription)
        .filter(Subscription.subs_id == payload.subs_id)
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # If user already has an active, not-expired subscription for this subs_id,
    # do not create a new Stripe checkout session – just return immediately.
    now = datetime.utcnow()
    existing_active = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.subs_id == payload.subs_id,
            UserSubscription.status == "active",
            (UserSubscription.expired_at.is_(None)) | (UserSubscription.expired_at > now),
        )
        .first()
    )
    if existing_active:
        return {
            "success": True,
            "init_url": "",
        }

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe secret key is not configured on the server.",
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    print(subscription.price, "subscription")

    try:
        amount = float(subscription.price)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription price is invalid",
        )

    amount_cents = int(amount * 100)
    if amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Subscription price must be greater than zero",
        )

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": subscription.name},
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            success_url="http://localhost:8000/subscriptions/callback" + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=payload.cancelUrl,
            metadata={
                "user_id": user_id,
                "subs_id": subscription.subs_id,
                "redirect_url": payload.redirectUrl,
                "cancel_url": payload.cancelUrl,
            },
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {e.user_message or str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create checkout session: {str(e)}",
        )

    return {
        "success": True,
        "init_url": session.url,
    }


@router.get("/subscriptions/callback")
def subscription_success(session_id: str, db: Session = Depends(get_db)):

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe is not configured",
        )
    
    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.retrieve(session_id)
    # You can access metadata right here ✅
    metadata = session.metadata

    if session.payment_status != "paid":
        raise HTTPException(status_code=400, detail="Payment not completed")

    def _meta_get(m, key: str):
        if not m:
            return None
        # Stripe returns a dict-like object; support both styles
        getter = getattr(m, "get", None)
        if callable(getter):
            try:
                return getter(key)
            except Exception:
                pass
        return getattr(m, key, None)

    user_id = _meta_get(metadata, "user_id")
    subs_id = _meta_get(metadata, "subs_id")
    redirect_url = _meta_get(metadata, "redirect_url")

    if not user_id or not subs_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing user_id or subs_id in Stripe session metadata",
        )

    user_id = str(user_id).strip()
    subs_id = str(subs_id).strip()

    subscription = (
        db.query(Subscription)
        .filter(Subscription.subs_id == subs_id)
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    # Use Stripe session creation time as the base "create date" (UTC)
    base_time = datetime.utcnow()
    created_ts = getattr(session, "created", None)
    if isinstance(created_ts, (int, float)):
        base_time = datetime.utcfromtimestamp(created_ts)

    expired_at = base_time + timedelta(days=int(subscription.duration_days or 0))

    existing = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.subs_id == subs_id,
        )
        .first()
    )

    if existing:
        existing.status = "active"
        existing.expired_at = expired_at
        existing.feature_entitlements = subscription.feature_entitlements
    else:
        db.add(
            UserSubscription(
                user_id=user_id,
                subs_id=subs_id,
                status="active",
                expired_at=expired_at,
                feature_entitlements=subscription.feature_entitlements,
            )
        )

    db.commit()

    if not redirect_url:
        # Fallback: don't crash if metadata.redirect_url wasn't set
        redirect_url = "/"

    return RedirectResponse(url=redirect_url)