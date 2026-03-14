"""
HubSpot platform agent.

Leaf tasks:
  - create_contact  — create a new CRM contact
  - update_contact  — update contact properties
  - create_deal     — create a new deal in the pipeline
  - send_email      — send a single-send email via HubSpot

Auth: HUBSPOT_API_KEY environment variable (Private App access token).
Uses hubspot-api-client (already in requirements.txt).
"""

import logging
import os

from tree import BranchNode, LeafNode, WorkflowState

logger = logging.getLogger(__name__)


def _client():
    from hubspot import HubSpot  # lazy import

    return HubSpot(access_token=os.getenv("HUBSPOT_API_KEY", ""))


def _check_key() -> bool:
    return bool(os.getenv("HUBSPOT_API_KEY"))


# ---------------------------------------------------------------------------
# Leaf actions
# ---------------------------------------------------------------------------


async def _create_contact(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "HUBSPOT_API_KEY not configured"}

    from hubspot.crm.contacts import SimplePublicObjectInputForCreate
    from hubspot.crm.contacts.exceptions import ApiException

    payload = state.trigger_event.get("hubspot_contact", {})
    email = payload.get("email", "")
    firstname = payload.get("firstname", "")
    lastname = payload.get("lastname", "")
    extra_props = payload.get("properties", {})

    properties = {"email": email, "firstname": firstname, "lastname": lastname, **extra_props}
    body = SimplePublicObjectInputForCreate(properties=properties)

    try:
        contact = _client().crm.contacts.basic_api.create(simple_public_object_input_for_create=body)
        logger.info("HubSpot: created contact %s (%s)", contact.id, email)
        return {"status": "success", "contact_id": contact.id, "email": email}
    except ApiException as exc:
        logger.error("HubSpot create_contact error: %s", exc)
        return {"status": "error", "error": str(exc)}


async def _update_contact(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "HUBSPOT_API_KEY not configured"}

    from hubspot.crm.contacts import SimplePublicObjectInput
    from hubspot.crm.contacts.exceptions import ApiException

    payload = state.trigger_event.get("hubspot_update", {})
    contact_id = payload.get("contact_id")
    if not contact_id:
        return {"status": "skipped", "reason": "hubspot_update.contact_id not provided"}

    properties = payload.get("properties", {})
    body = SimplePublicObjectInput(properties=properties)

    try:
        _client().crm.contacts.basic_api.update(contact_id=contact_id, simple_public_object_input=body)
        logger.info("HubSpot: updated contact %s", contact_id)
        return {"status": "success", "contact_id": contact_id}
    except ApiException as exc:
        logger.error("HubSpot update_contact error: %s", exc)
        return {"status": "error", "error": str(exc)}


async def _create_deal(state: WorkflowState) -> dict:
    if not _check_key():
        return {"status": "skipped", "reason": "HUBSPOT_API_KEY not configured"}

    from hubspot.crm.deals import SimplePublicObjectInputForCreate
    from hubspot.crm.deals.exceptions import ApiException

    payload = state.trigger_event.get("hubspot_deal", {})
    deal_name = payload.get("dealname", "Automated Deal")
    stage = payload.get("dealstage", "appointmentscheduled")
    pipeline = payload.get("pipeline", "default")
    amount = payload.get("amount", "")
    extra = payload.get("properties", {})

    properties = {
        "dealname": deal_name,
        "dealstage": stage,
        "pipeline": pipeline,
        **extra,
    }
    if amount:
        properties["amount"] = str(amount)

    body = SimplePublicObjectInputForCreate(properties=properties)

    try:
        deal = _client().crm.deals.basic_api.create(simple_public_object_input_for_create=body)
        logger.info("HubSpot: created deal %s ('%s')", deal.id, deal_name)
        return {"status": "success", "deal_id": deal.id, "deal_name": deal_name}
    except ApiException as exc:
        logger.error("HubSpot create_deal error: %s", exc)
        return {"status": "error", "error": str(exc)}


async def _send_email(state: WorkflowState) -> dict:
    """Send a transactional email via HubSpot single-send API."""
    if not _check_key():
        return {"status": "skipped", "reason": "HUBSPOT_API_KEY not configured"}

    import requests

    payload = state.trigger_event.get("hubspot_email", {})
    email_id = payload.get("email_id")
    to_email = payload.get("to")
    contact_id = payload.get("contact_id")

    if not email_id or not to_email:
        return {"status": "skipped", "reason": "hubspot_email requires email_id and to"}

    body: dict = {
        "emailId": email_id,
        "message": {"to": to_email},
    }
    if contact_id:
        body["contactProperties"] = {"vid": contact_id}

    headers = {
        "Authorization": f"Bearer {os.getenv('HUBSPOT_API_KEY', '')}",
        "Content-Type": "application/json",
    }
    resp = requests.post(
        "https://api.hubapi.com/marketing/v3/transactional/single-email/send",
        headers=headers,
        json=body,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info("HubSpot: sent email to %s", to_email)
    return {"status": "success", "request_id": data.get("requestId"), "to": to_email}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_hubspot_branch(enabled: bool = True) -> BranchNode:
    """Return a fully-wired HubSpot BranchNode."""
    branch = BranchNode(
        name="HubSpot",
        description="HubSpot CRM automation: contacts, deals, email",
        enabled=enabled,
    )
    branch.add_child(LeafNode("hubspot.create_contact", "Create a HubSpot contact", _create_contact))
    branch.add_child(LeafNode("hubspot.update_contact", "Update a HubSpot contact", _update_contact))
    branch.add_child(LeafNode("hubspot.create_deal", "Create a HubSpot deal", _create_deal))
    branch.add_child(LeafNode("hubspot.send_email", "Send email via HubSpot", _send_email))
    return branch
