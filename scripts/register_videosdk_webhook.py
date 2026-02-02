# import requests
# import jwt
# from datetime import datetime, timedelta, timezone

# VIDEOSDK_WEBHOOK_API = "https://api.videosdk.live/v2/sip/webhooks"
# VIDEOSDK_API_SECRET = "33d2923d27c61f3d9aa7f41755e72809a328be40cc532115f2fe726f4330e14e"
# VIDEOSDK_API_KEY="05aa1eaa-bcc5-43cd-ac52-7dfb4eb61b79"

# def generate_videosdk_admin_token() -> str:
#     payload = {
#         "apikey": VIDEOSDK_API_KEY,
#         "permissions": ["allow_join"],  # required for server-side API calls
#         "version": 2,
#         "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
#         "roles": ["CRAWLER", "RTCPEER"],
#     }

#     token = jwt.encode(
#         payload,
#         VIDEOSDK_API_SECRET,
#         algorithm="HS256"
#     )

#     return token

# # SIP webhook API only accepts these event names (participant/session events are invalid and cause 500)
# SIP_WEBHOOK_EVENTS = [
#     "call-started",
#     "call-answered",
#     "call-hangup",
#     "call-transferred",
#     "call-missed",
#     "call-update",
#     "call-ringing",
# ]


# def register_videosdk_webhook():
#     payload = {
#         "url": "https://1470b4b75d93.ngrok-free.app/webhooks/videosdk",
#         "events": SIP_WEBHOOK_EVENTS,
#     }

#     token = generate_videosdk_admin_token()

#     headers = {
#         "Authorization": token,
#         "Content-Type": "application/json"
#     }

#     response = requests.post(
#         VIDEOSDK_WEBHOOK_API,
#         json=payload,
#         headers=headers,
#         timeout=10
#     )

#     print("Status:", response.status_code)
#     print("Response body (raw):", response.text)
#     if response.text.strip():
#         try:
#             print("Response (JSON):", response.json())
#         except Exception as e:
#             print("Response is not JSON:", e)
#     else:
#         print("Response body is empty.")


# if __name__ == "__main__":
#     register_videosdk_webhook()
