import json
import requests
from django.conf import settings

ONESIGNAL_URL = "https://api.onesignal.com/notifications"

def send_onesignal_notification(title, message, external_ids=None):
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}",  # ✅ FIXED
    }
    payload = {
        "app_id": settings.ONESIGNAL_APP_ID,
        "headings": {"en": title},
        "contents": {"en": message},
    }

    if external_ids:
        payload["include_aliases"] = {"external_id": [str(x) for x in external_ids]}
    else:
        payload["included_segments"] = ["All"]  # ✅ better default

    resp = requests.post(ONESIGNAL_URL, headers=headers, data=json.dumps(payload))
    try:
        return resp.json()
    except Exception:
        return {"error": resp.text}
