from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from app.database import get_db
from app.models.subscription_model import Subscription
from app.models.user_subscription_model import UserSubscription
from app.models.user_subscription_usage_model import UserSubscriptionUsage
from app.models.company_model import Company
from app.models.user_model import User
from app.models.transaction_model import Transaction
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
                subscription_id=us.subscription_id,
                status=us.status,
                feature_entitlements=us.feature_entitlements,
                start_date=us.start_date,
                end_date=us.end_date,
                expired_at=us.expired_at,
                created_at=us.created_at,
                updated_at=us.updated_at,
                subscription=SubscriptionBasicSchema(
                    name=sub.name if sub else "",
                    price=sub.price if sub else "",
                    duration_days=sub.duration_days if sub else 0,
                    usage_limit=sub.usage_limit if sub else None,
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

    # Ensure we have (and persist) a Stripe customer for this user
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    try:
        if not user.stripe_customer_id:
            # Create Stripe customer only once and store the ID on the user
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
            )
            user.stripe_customer_id = customer.id
            db.commit()
            db.refresh(user)
        stripe_customer_id = user.stripe_customer_id
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {e.user_message or str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Stripe customer: {str(e)}",
        )

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
    print(subscription.name, "subscription description")


    # Map duration_days to Stripe recurring interval (used for subscription period)
    duration_days = int(subscription.duration_days or 0)
    if duration_days <= 0:
        duration_days = 30  # fallback
    if duration_days >= 365:
        recurring = {"interval": "year", "interval_count": duration_days // 365}
    elif duration_days >= 30:
        recurring = {"interval": "month", "interval_count": max(1, duration_days // 30)}
    elif duration_days >= 7:
        recurring = {"interval": "week", "interval_count": duration_days // 7}
    else:
        recurring = {"interval": "day", "interval_count": duration_days}

    try:
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": subscription.name,
                            "description": subscription.description,
                        },
                        "unit_amount": amount_cents,
                        "recurring": recurring,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{settings.SERVER_API_URL}subscriptions/callback?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=payload.cancelUrl,
            metadata={
                "user_id": user_id,
                "subs_id": subscription.subs_id,
                "redirect_url": payload.redirectUrl or "/",
                "cancel_url": payload.cancelUrl or "/",
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


# @router.get("/subscriptions/callback")
# def subscription_success(session_id: str, db: Session = Depends(get_db)):

    # if not settings.STRIPE_SECRET_KEY:
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Stripe is not configured",
    #     )
    
    # stripe.api_key = settings.STRIPE_SECRET_KEY

    # session = stripe.checkout.Session.retrieve(
    #     session_id,
    #     expand=["subscription","payment_intent"],
    # )
    # metadata = session.metadata

    # if session.payment_status != "paid":
    #     raise HTTPException(status_code=400, detail="Payment not completed")

    # # Get subscription and invoice details from Stripe
    # start_date = None
    # end_date = None
    # subscription_id = None
    # invoice_id = None
    
    # # Get subscription details
    # stripe_sub = session.subscription
    # if stripe_sub:
    #     sub_obj = stripe.Subscription.retrieve(stripe_sub) if isinstance(stripe_sub, str) else stripe_sub
    #     subscription_id = sub_obj.id
    #     period_start = getattr(sub_obj, "current_period_start", None)
    #     period_end = getattr(sub_obj, "current_period_end", None)
    #     if period_start:
    #         start_date = datetime.utcfromtimestamp(period_start)
    #     if period_end:
    #         end_date = datetime.utcfromtimestamp(period_end)
    
    # # Get invoice ID from the payment intent or invoice
    # if session.payment_intent:
    #     payment_intent = stripe.PaymentIntent.retrieve(session.payment_intent)
    #     if payment_intent and hasattr(payment_intent, 'latest_charge'):
    #         charge = stripe.Charge.retrieve(payment_intent.latest_charge)
    #         if charge and hasattr(charge, 'invoice'):
    #             invoice_id = charge.invoice

    # def _meta_get(m, key: str):
    #     if not m:
    #         return None
    #     # Stripe returns a dict-like object; support both styles
    #     getter = getattr(m, "get", None)
    #     if callable(getter):
    #         try:
    #             return getter(key)
    #         except Exception:
    #             pass
    #     return getattr(m, key, None)

    # user_id = _meta_get(metadata, "user_id")
    # subs_id = _meta_get(metadata, "subs_id")
    # redirect_url = _meta_get(metadata, "redirect_url")

    # if not user_id or not subs_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Missing user_id or subs_id in Stripe session metadata",
    #     )

    # user_id = str(user_id).strip()
    # subs_id = str(subs_id).strip()

    # subscription = (
    #     db.query(Subscription)
    #     .filter(Subscription.subs_id == subs_id)
    #     .first()
    # )
    # if not subscription:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail="Subscription not found",
    #     )

    # # Use Stripe subscription period dates (start_date, end_date) - not calculated manually
    # # If Stripe didn't return them (e.g. one-time payment fallback), fall back to calculation
    # if not start_date or not end_date:
    #     base_time = datetime.utcnow()
    #     created_ts = getattr(session, "created", None)
    #     if isinstance(created_ts, (int, float)):
    #         base_time = datetime.utcfromtimestamp(created_ts)
    #     start_date = base_time
    #     end_date = base_time + timedelta(days=int(subscription.duration_days or 0))
    # expired_at = end_date  # end_date from Stripe = subscription expiry

    # existing = (
    #     db.query(UserSubscription)
    #     .filter(
    #         UserSubscription.user_id == user_id,
    #         UserSubscription.subs_id == subs_id,
    #     )
    #     .first()
    # )

    # if existing:
    #     user_sub = existing
    #     existing.status = "active"
    #     existing.start_date = start_date
    #     existing.end_date = end_date
    #     existing.expired_at = expired_at
    #     existing.feature_entitlements = subscription.feature_entitlements
    #     if subscription_id:
    #         existing.subscription_id = subscription_id
    #     if invoice_id:
    #         existing.invoice_id = invoice_id
    # else:
    #     user_sub = UserSubscription(
    #         user_id=user_id,
    #         subs_id=subs_id,
    #         subscription_id=subscription_id,
    #         invoice_id=invoice_id,
    #         status="active",
    #         start_date=start_date,
    #         end_date=end_date,
    #         expired_at=expired_at,
    #         feature_entitlements=subscription.feature_entitlements,
    #     )
    #     db.add(user_sub)
    #     db.flush()  # get user_sub.id before adding usage

    # # Add usage entry: usage_give from subscription.usage_limit, usage_consumed = 0
    # usage_give = int(subscription.usage_limit or 0)
    # db.add(
    #     UserSubscriptionUsage(
    #         user_subscription_id=user_sub.id,
    #         usage_give=usage_give,
    #         usage_consumed=0,
    #     )
    # )

    # db.commit()

    # if not redirect_url:
    #     # Fallback: don't crash if metadata.redirect_url wasn't set
    #     redirect_url = "/"

    # return RedirectResponse(url=redirect_url)


@router.get("/subscriptions/callback")
def subscription_success(session_id: str, db: Session = Depends(get_db)):

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe is not configured",
        )

    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Retrieve checkout session with expanded objects
    session = stripe.checkout.Session.retrieve(
        session_id,
        expand=["subscription", "payment_intent"],
    )
    print(session, "session")
    print(session.metadata,"session.metadata")
    print(session.payment_intent,"session.payment_intent")

    if session.payment_status != "paid":
        raise HTTPException(status_code=400, detail="Payment not completed")

    metadata = session.metadata

    # -----------------------------
    # Extract Stripe IDs
    # -----------------------------
    subscription_id = None
    invoice_id = None
    transaction_id = None

    # Subscription ID
    if session.subscription:
        subscription_id = (
            session.subscription.id
            if not isinstance(session.subscription, str)
            else session.subscription
        )

    # Invoice ID (direct from session)
    invoice_id = session.invoice

    # Transaction ID (PaymentIntent ID)
    if session.payment_intent:
        transaction_id = (
            session.payment_intent.id
            if not isinstance(session.payment_intent, str)
            else session.payment_intent
        )

    # Print transaction_id (as you requested)
    print("Transaction ID (PaymentIntent):", transaction_id)

    # -----------------------------
    # Extract Metadata
    # -----------------------------
    def _meta_get(m, key: str):
        if not m:
            return None
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

    # -----------------------------
    # Fetch Subscription Plan
    # -----------------------------
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

    # -----------------------------
    # Get Stripe Period Dates
    # -----------------------------
    start_date = None
    end_date = None

    if session.subscription:
        sub_obj = session.subscription
        period_start = getattr(sub_obj, "current_period_start", None)
        period_end = getattr(sub_obj, "current_period_end", None)

        if period_start:
            start_date = datetime.utcfromtimestamp(period_start)

        if period_end:
            end_date = datetime.utcfromtimestamp(period_end)

    # Fallback (very rare case)
    if not start_date or not end_date:
        base_time = datetime.utcnow()
        start_date = base_time
        end_date = base_time + timedelta(days=int(subscription.duration_days or 0))

    expired_at = end_date

    # -----------------------------
    # Check Existing User Subscription
    # -----------------------------
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
        existing.start_date = start_date
        existing.end_date = end_date
        existing.expired_at = expired_at
        existing.feature_entitlements = subscription.feature_entitlements

        # Save Stripe IDs
        if subscription_id:
            existing.subscription_id = subscription_id

        if invoice_id:
            existing.invoice_id = invoice_id

    else:
        user_sub = UserSubscription(
            user_id=user_id,
            subs_id=subs_id,
            subscription_id=subscription_id,
            invoice_id=invoice_id,
            status="active",
            start_date=start_date,
            end_date=end_date,
            expired_at=expired_at,
            feature_entitlements=subscription.feature_entitlements,
        )
        db.add(user_sub)
        db.flush()

        # Create usage entry only for new subscription
        db.add(
            UserSubscriptionUsage(
                user_subscription_id=user_sub.id,
                usage_give=int(subscription.usage_limit or 0),
                usage_consumed=0,
            )
        )

    db.commit()

    # -----------------------------
    # Create transaction record
    # -----------------------------
    try:
        amount = None
        currency = None
        
        # Try to get amount and currency from payment intent
        # if session.subscription and hasattr(session.subscription, 'plan'):
        #     # Get amount from plan
        #     plan = session.subscription.plan
        #     if hasattr(plan, 'amount'):
        #         amount = str(float(plan.amount) / 100)  # Convert from cents to dollars
        #     if hasattr(plan, 'currency'):
        #         currency = plan.currency.upper()

        if session.payment_status == "paid":
            amount = session.amount_total / 100
            currency = session.currency.upper()


        # Get transaction_id from payment_intent if available
        payment_intent_id = None
        if hasattr(session, 'payment_intent') and session.payment_intent:
            payment_intent_id = session.payment_intent.id if not isinstance(session.payment_intent, str) else session.payment_intent
        
        # Get invoice_id from session
        invoice_id = getattr(session, 'invoice', None)
        
        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            subscription_id=subscription.id,
            invoice_id=invoice_id,
            # transaction_id=payment_intent_id or f"txn_{user_id[-8:]}_{int(datetime.utcnow().timestamp())}",
            amount=amount,
            currency=currency,
            status="completed" if getattr(session, 'payment_status') == "paid" else "pending"
        )
        db.add(transaction)
        db.commit()
        
    except Exception as e:
        # Log the error but don't fail the whole process
        print(f"Error saving transaction: {str(e)}")
        db.rollback()

    if not redirect_url:
        redirect_url = "/"

    return RedirectResponse(url=redirect_url)



@router.get("/subscriptions/manage/pack")
async def manage_subscription_pack(
    subscription_id: str,
    return_url: str = "https://meet-nine-nu.vercel.app/dashboard",
    db: Session = Depends(get_db)
):
    """
    Generate a Stripe Customer Portal session URL for managing a subscription.
    
    Args:
        subscription_id: The Stripe subscription ID to manage
        return_url: The URL to redirect to after managing the subscription
        
    Returns:
        dict: Contains the URL to the Stripe Customer Portal
    """
    try:
        if not settings.STRIPE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stripe secret key is not configured on the server.",
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Retrieve the subscription to get the customer ID
        subscription = stripe.Subscription.retrieve(subscription_id)
        customer_id = subscription.customer
        
        # Create a Stripe Billing Portal session
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        
        return {"url": session.url}
        
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating Stripe portal session: {str(e)}"
        )
