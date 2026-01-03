# from datetime import datetime, timezone
# from app.storage.links_store import LINKS

# def validate_link(token: str):
#     link = LINKS.get(token)

#     if not link:
#         return None

#     if not link["is_active"]:
#         return None

#     # Check expiration if set
#     if link["expires_at"]:
#         # Handle both timezone-aware and naive datetimes
#         expires_at = link["expires_at"]
#         if expires_at.tzinfo is None:
#             expires_at = expires_at.replace(tzinfo=timezone.utc)
#         now = datetime.now(timezone.utc)
#         if expires_at < now:
#             return None

#     if link["used_count"] >= link["max_usage"]:
#         return None

#     return link
