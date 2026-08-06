"""
Conical revenue funnel builder.

Normalizes all revenue paths into one unified funnel:
Acquisition -> Qualification -> Conversion -> Fulfillment -> Retention/Expansion
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List

FUNNEL_STAGES: List[str] = [
    "acquisition",
    "qualification",
    "conversion",
    "fulfillment",
    "retention_expansion",
]

REVENUE_PATHS = {
    "services",
    "subscriptions",
    "one_time_sales",
    "upsells",
    "partnerships",
    "affiliates",
    "referrals",
}

INBOUND_SOURCES = {
    "ads",
    "forms",
    "email",
    "social",
    "webhooks",
    "partner_leads",
    "support_signals",
    "direct",
}


@dataclass
class BuildResult:
    status: str
    trigger_event: Dict[str, Any]
    blocked_reason: str | None = None


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def build_conical_trigger(payload: Dict[str, Any]) -> BuildResult:
    """
    Build a normalized trigger_event payload that routes through all integrated
    platform branches with a single funnel contract.
    """
    funnel = payload.get("funnel", {})
    customer = payload.get("customer", {})
    commerce = payload.get("commerce", {})
    retention = payload.get("retention", {})
    analytics = payload.get("analytics", {})
    governance = payload.get("governance", {})

    revenue_path = str(funnel.get("revenue_path", "services")).strip().lower()
    if revenue_path not in REVENUE_PATHS:
        revenue_path = "services"

    inbound_source = str(funnel.get("inbound_source", "webhooks")).strip().lower()
    if inbound_source not in INBOUND_SOURCES:
        inbound_source = "webhooks"

    amount = _to_float(commerce.get("amount"), 0.0)
    amount_cents = max(_to_int(round(amount * 100)), 0)
    currency = str(commerce.get("currency", "usd")).lower()

    approved_raw = governance.get("approved", False)
    approved = approved_raw is True or str(approved_raw).lower() == "true"
    approval_reference = str(governance.get("approval_reference", "")).strip()
    high_risk_threshold = _to_float(os.getenv("CONICAL_HIGH_RISK_AMOUNT", "50000"), 50000)
    is_high_risk = amount >= high_risk_threshold

    if is_high_risk and not (approved and approval_reference):
        return BuildResult(
            status="blocked",
            trigger_event={},
            blocked_reason=(
                "High-risk transaction requires governance.approved=true and "
                "governance.approval_reference"
            ),
        )

    lifecycle_stage = str(customer.get("lifecycle_stage", "lead"))
    contact_email = str(customer.get("email", ""))
    contact_firstname = str(customer.get("first_name", ""))
    contact_lastname = str(customer.get("last_name", ""))
    company = str(customer.get("company", ""))
    contact_id = str(customer.get("hubspot_contact_id", ""))
    customer_id = str(customer.get("stripe_customer_id", ""))

    offer_name = str(commerce.get("offer_name", "Unified Offer"))
    product_line = str(commerce.get("product_line", "core"))
    subscription_price_id = str(commerce.get("stripe_price_id", ""))

    deal_stage = str(commerce.get("deal_stage", "appointmentscheduled"))
    pipeline = str(commerce.get("pipeline", "default"))
    recurring = revenue_path in {"subscriptions", "upsells"}
    mrr = _to_float(commerce.get("mrr"), amount if recurring else 0.0)
    arr = _to_float(commerce.get("arr"), mrr * 12 if recurring else 0.0)

    gross_margin = _to_float(analytics.get("gross_margin"), 0.0)
    churn_rate = _to_float(analytics.get("churn_rate"), 0.0)
    cac = _to_float(analytics.get("cac"), 0.0)
    ltv = _to_float(analytics.get("ltv"), arr if arr > 0 else amount)
    payback_months = _to_float(analytics.get("payback_months"), (cac / max(mrr, 1.0)) if mrr else 0.0)

    conversion_rate = _to_float(analytics.get("conversion_rate"), 0.0)
    net_revenue_growth = _to_float(analytics.get("net_revenue_growth"), 0.0)

    opportunity_id = str(
        payload.get("opportunity_id")
        or commerce.get("deal_id")
        or customer.get("lead_id")
        or "opportunity-unset"
    )
    account_id = str(customer.get("account_id", opportunity_id))

    trigger_event: Dict[str, Any] = {
        "system": "conical_revenue_funnel",
        "funnel_model": {
            "name": "unified_conical_funnel",
            "stages": FUNNEL_STAGES,
            "revenue_path": revenue_path,
            "inbound_source": inbound_source,
            "phase": str(payload.get("phase", "phase_1_core_offer")),
        },
        "kpis": {
            "cac": cac,
            "payback_months": round(payback_months, 2),
            "churn_rate": churn_rate,
            "ltv": ltv,
            "gross_margin": gross_margin,
            "net_revenue_growth": net_revenue_growth,
            "conversion_rate": conversion_rate,
            "mrr": mrr,
            "arr": arr,
            "booked_revenue": amount,
        },
        "governance": {
            "high_risk": is_high_risk,
            "risk_threshold": high_risk_threshold,
            "approved": approved,
            "approval_reference": approval_reference,
            "rollback_plan": [
                "hubspot_revert_contact_tags",
                "hubspot_revert_deal_stage",
                "stripe_refund_or_cancel_subscription",
                "linear_close_fulfillment_issue",
                "github_close_fulfillment_issue",
                "notion_mark_entry_archived",
            ],
            "optimization_review_cadence": "weekly",
            "continue_on_error": True,
        },
        # Zapier = normalized inbound routing layer
        "zapier_trigger": {
            "data": {
                "source": inbound_source,
                "opportunity_id": opportunity_id,
                "account_id": account_id,
                "revenue_path": revenue_path,
                "funnel_stage": "acquisition",
            }
        },
        # HubSpot = source of truth for pipeline/customer state
        "hubspot_contact": {
            "email": contact_email,
            "firstname": contact_firstname,
            "lastname": contact_lastname,
            "properties": {
                "company": company,
                "lifecyclestage": lifecycle_stage,
                "revenue_path": revenue_path,
                "funnel_stage": "qualification",
                "acquisition_channel": inbound_source,
                "product_line": product_line,
            },
        },
        "hubspot_deal": {
            "dealname": f"{offer_name} - {account_id}",
            "dealstage": deal_stage,
            "pipeline": pipeline,
            "amount": amount,
            "properties": {
                "revenue_path": revenue_path,
                "funnel_stage": "conversion",
                "mrr": str(round(mrr, 2)),
                "arr": str(round(arr, 2)),
                "booked_revenue": str(round(amount, 2)),
                "acquisition_channel": inbound_source,
            },
        },
        "hubspot_update": {
            "contact_id": contact_id,
            "properties": {
                "funnel_stage": "retention_expansion",
                "upsell_target": "true" if revenue_path in {"subscriptions", "upsells"} else "false",
                "churn_risk": "high" if churn_rate >= 0.08 else "normal",
            },
        },
        # Stripe = checkout, subscription, invoice, collections
        "stripe_customer": {
            "email": contact_email,
            "name": f"{contact_firstname} {contact_lastname}".strip(),
            "metadata": {
                "opportunity_id": opportunity_id,
                "revenue_path": revenue_path,
                "account_id": account_id,
            },
        },
        "stripe_charge": {
            "amount": amount_cents,
            "currency": currency,
            "customer": customer_id or None,
            "description": f"{offer_name} ({revenue_path})",
        },
        "stripe_subscription": {
            "customer_id": customer_id,
            "price_id": subscription_price_id,
        },
        "stripe_invoice": {
            "customer_id": customer_id,
        },
        # Closed deal -> fulfillment & tracking tasks
        "linear_issue": {
            "title": f"Fulfillment: {offer_name} ({opportunity_id})",
            "description": "Automated fulfillment task created from closed deal.",
        },
        "github_issue": {
            "title": f"Delivery workflow for {offer_name} ({opportunity_id})",
            "body": "Track delivery implementation and completion criteria for this deal.",
            "labels": ["automation", "fulfillment", revenue_path],
        },
        "notion_page": {
            "title": f"Account Plan: {account_id}",
            "content": (
                f"Revenue Path: {revenue_path}\n"
                f"Offer: {offer_name}\n"
                f"Funnel Stages: {', '.join(FUNNEL_STAGES)}\n"
                f"Status: Fulfillment started."
            ),
        },
        # Retention / expansion automation signals
        "hubspot_email": {
            "to": contact_email,
            "contact_id": contact_id,
            "email_id": retention.get("hubspot_email_id"),
        },
        "slack_message": {
            "text": (
                f"Revenue funnel update: {opportunity_id} | path={revenue_path} | "
                f"source={inbound_source} | amount={amount:.2f} {currency.upper()}"
            )
        },
    }

    return BuildResult(status="ok", trigger_event=trigger_event)
