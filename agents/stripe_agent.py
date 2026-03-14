"""
Stripe platform agent.

Leaf tasks:
  - charge_card         — create a PaymentIntent and confirm it
  - create_customer     — create a new Stripe customer
  - create_subscription — subscribe a customer to a price/plan
  - create_invoice      — create and finalize an invoice

Auth: STRIPE_SECRET_KEY environment variable.
Uses stripe SDK (already in requirements.txt).
"""

import logging
import os

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)


def _stripe():
    import stripe as _stripe_sdk  # lazy import

    _stripe_sdk.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    return _stripe_sdk


def _check_key() -> bool:
    return bool(os.getenv("STRIPE_SECRET_KEY"))


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _charge_card(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "STRIPE_SECRET_KEY not configured"}

    stripe = _stripe()
    payload = state.trigger_event.get("stripe_charge", {})
    amount = int(payload.get("amount", 1000))  # cents
    currency = payload.get("currency", "usd")
    payment_method = payload.get("payment_method")
    customer = payload.get("customer")
    description = payload.get("description", "AI Automation charge")

    kwargs: dict = {
        "amount": amount,
        "currency": currency,
        "description": description,
        "confirm": True,
        "automatic_payment_methods": {"enabled": True, "allow_redirects": "never"},
    }
    if payment_method:
        kwargs["payment_method"] = payment_method
        kwargs.pop("automatic_payment_methods", None)
    if customer:
        kwargs["customer"] = customer

    intent = stripe.PaymentIntent.create(**kwargs)
    logger.info("Stripe: created PaymentIntent %s status=%s", intent.id, intent.status)
    return {"status": "success", "payment_intent_id": intent.id, "amount": amount, "currency": currency, "intent_status": intent.status}


async def _create_customer(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "STRIPE_SECRET_KEY not configured"}

    stripe = _stripe()
    payload = state.trigger_event.get("stripe_customer", {})
    email = payload.get("email", "")
    name = payload.get("name", "")
    metadata = payload.get("metadata", {})

    customer = stripe.Customer.create(email=email, name=name, metadata=metadata)
    logger.info("Stripe: created customer %s (%s)", customer.id, email)
    return {"status": "success", "customer_id": customer.id, "email": email}


async def _create_subscription(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "STRIPE_SECRET_KEY not configured"}

    stripe = _stripe()
    payload = state.trigger_event.get("stripe_subscription", {})
    customer_id = payload.get("customer_id")
    price_id = payload.get("price_id")

    if not customer_id or not price_id:
        return {"status": "skipped", "reason": "stripe_subscription requires customer_id and price_id"}

    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
    )
    logger.info("Stripe: created subscription %s for customer %s", sub.id, customer_id)
    return {"status": "success", "subscription_id": sub.id, "sub_status": sub.status}


async def _create_invoice(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "STRIPE_SECRET_KEY not configured"}

    stripe = _stripe()
    payload = state.trigger_event.get("stripe_invoice", {})
    customer_id = payload.get("customer_id")
    if not customer_id:
        return {"status": "skipped", "reason": "stripe_invoice.customer_id not provided"}

    invoice = stripe.Invoice.create(customer=customer_id, auto_advance=True)
    finalized = stripe.Invoice.finalize_invoice(invoice.id)
    logger.info("Stripe: created invoice %s for customer %s", finalized.id, customer_id)
    return {"status": "success", "invoice_id": finalized.id, "invoice_status": finalized.status, "amount_due": finalized.amount_due}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_stripe_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired Stripe BranchNode."""
    branch = BranchNode(
        name="Stripe",
        description="Stripe automation: payments, customers, subscriptions, invoices",
        enabled=enabled,
    )
    branch.add_child(LeafNode("stripe.charge_card", "Charge a card via Stripe", _charge_card))
    branch.add_child(LeafNode("stripe.create_customer", "Create a Stripe customer", _create_customer))
    branch.add_child(LeafNode("stripe.create_subscription", "Subscribe a customer to a plan", _create_subscription))
    branch.add_child(LeafNode("stripe.create_invoice", "Create and finalize a Stripe invoice", _create_invoice))
    return branch
