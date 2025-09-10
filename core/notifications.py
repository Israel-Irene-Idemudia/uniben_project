from onesignal_sdk.client import Client
from django.conf import settings

client = Client(
    app_id=settings.ONESIGNAL_APP_ID,
    rest_api_key=settings.ONESIGNAL_API_KEY
)

def send_notification(title, message, segments=["All"]):
    notification = {
        "headings": {"en": title},
        "contents": {"en": message},
        "included_segments": segments,  # Default: send to all users
    }
    return client.send_notification(notification)
