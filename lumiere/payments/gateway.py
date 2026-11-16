"""
External Payment Service adapter.

Lumiere never receives or stores card numbers. Checkout passes a payment-method
token to the provider and stores only the provider reference and status.

PAYMENT_MODE=mock    Built-in simulator (default). No keys or network needed.
PAYMENT_MODE=stripe  Stripe API in test mode. Requires an sk_test_ key;
                     live keys are refused on purpose.
"""
import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

# Stripe's published test payment methods, which the mock simulator mirrors.
TEST_PAYMENT_METHODS = {
    "pm_card_visa": "Visa test card – payment succeeds",
    "pm_card_chargeDeclined": "Test card – payment is declined",
    "pm_card_chargeDeclinedInsufficientFunds": "Test card – insufficient funds",
}


@dataclass
class PaymentResult:
    success: bool
    status: str  # SUCCEEDED, DECLINED or FAILED
    provider: str
    reference: str = ""
    message: str = ""


def submit_payment(amount, payment_method, description=""):
    """Send a payment request to the configured provider and return its result."""
    amount = Decimal(amount)
    mode = getattr(settings, "PAYMENT_MODE", "mock")
    if amount <= 0:
        return PaymentResult(False, "FAILED", mode, message="Invalid payment amount.")
    if payment_method not in TEST_PAYMENT_METHODS:
        return PaymentResult(False, "FAILED", mode, message="Please choose a payment method.")
    if mode == "stripe":
        return _stripe_payment(amount, payment_method, description)
    return _mock_payment(amount, payment_method)


def _mock_payment(amount, payment_method):
    if payment_method == "pm_card_visa":
        return PaymentResult(True, "SUCCEEDED", "mock", reference=f"mock_pi_{uuid.uuid4().hex[:20]}")
    if payment_method == "pm_card_chargeDeclinedInsufficientFunds":
        return PaymentResult(False, "DECLINED", "mock", message="Payment declined: insufficient funds.")
    return PaymentResult(False, "DECLINED", "mock", message="Payment declined. Please try another payment method.")


def _stripe_payment(amount, payment_method, description):
    key = getattr(settings, "STRIPE_SECRET_KEY", "")
    if not key.startswith("sk_test_"):
        return PaymentResult(False, "FAILED", "stripe", message="Payment service is not configured (test key required).")

    import stripe

    stripe.api_key = key
    cents = int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    try:
        intent = stripe.PaymentIntent.create(
            amount=cents,
            currency="usd",
            payment_method=payment_method,
            confirm=True,
            description=description or "Lumiere order",
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
    except stripe.CardError as exc:
        return PaymentResult(False, "DECLINED", "stripe", message=f"Payment declined: {exc.user_message}")
    except stripe.StripeError:
        return PaymentResult(False, "FAILED", "stripe", message="Payment service unavailable. Please try again.")

    if intent.status == "succeeded":
        return PaymentResult(True, "SUCCEEDED", "stripe", reference=intent.id)
    return PaymentResult(False, "FAILED", "stripe", message="Payment could not be completed.")
