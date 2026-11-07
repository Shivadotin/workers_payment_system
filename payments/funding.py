import hmac
import hashlib
import requests
from django.conf import settings


class FundingError(Exception):
    pass


def _auth():
    if not (settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET):
        raise FundingError("Razorpay keys are missing in .env")
    if not settings.RAZORPAY_KEY_ID.startswith("rzp_test_"):
        raise FundingError("Only Razorpay TEST keys (rzp_test_...) are allowed")
    return settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET


def create_order(batch):
    """Asks Razorpay for an order worth the batch total. Returns the order id."""
    try:
        response = requests.post(
            "https://api.razorpay.com/v1/orders",
            json={
                "amount": int(batch.total_amount * 100),   # rupees to paise
                "currency": "INR",
                "receipt": f"batch-{batch.id}",
            },
            auth=_auth(), timeout=20,
        )
    except requests.RequestException as e:
        raise FundingError(f"Could not reach Razorpay: {e}")
    data = response.json() if response.content else {}
    if response.status_code >= 400:
        raise FundingError(data.get("error", {}).get("description", "Razorpay rejected the order"))
    return data["id"]


def verify_signature(order_id, payment_id, signature):
    """Razorpay signs 'order_id|payment_id' with your key secret. Recompute and compare."""
    secret = settings.RAZORPAY_KEY_SECRET.encode()
    expected = hmac.new(secret, f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")