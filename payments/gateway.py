import uuid
from django.conf import settings


class PaymentGatewayError(Exception):
    pass


def create_transfer(bank_details, amount, idempotency_key):
    """
    Sends money to one worker. In mock mode it simulates a gateway response.
    Later, replace the real branch with an actual provider SDK call;
    nothing else in the app needs to change.
    """
    if bank_details is None:
        raise PaymentGatewayError("Worker has no bank details")

    if settings.MOCK_PAYMENTS:
        return {
            "id": f"mock_tr_{uuid.uuid4().hex[:16]}",
            "status": "succeeded",
            "amount": str(amount),
        }

    raise PaymentGatewayError("Real payment gateway is not configured")