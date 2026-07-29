import uuid

from revenue_funnel import FUNNEL_STAGES, build_conical_trigger


def _base_payload():
    return {
        "phase": "phase_1_core_offer",
        "funnel": {
            "revenue_path": "subscriptions",
            "inbound_source": "forms",
        },
        "customer": {
            "lead_id": "LEAD-1",
            "account_id": "ACCT-1",
            "email": "buyer@example.com",
            "first_name": "Ari",
            "last_name": "Lane",
            "lifecycle_stage": "lead",
            "stripe_customer_id": "cus_123",
            "hubspot_contact_id": "12345",
        },
        "commerce": {
            "offer_name": "Growth",
            "product_line": "automation",
            "amount": 2000,
            "currency": "usd",
            "mrr": 2000,
            "stripe_price_id": "price_123",
        },
        "analytics": {
            "cac": 500,
            "churn_rate": 0.04,
            "ltv": 18000,
            "gross_margin": 0.7,
            "conversion_rate": 0.2,
            "net_revenue_growth": 0.1,
        },
        "governance": {
            "approved": True,
            "approval_reference": "REVOPS-1",
        },
    }


def test_build_conical_trigger_contains_funnel_contract():
    result = build_conical_trigger(_base_payload())
    assert result.status == "ok"
    assert result.trigger_event["system"] == "conical_revenue_funnel"
    assert result.trigger_event["funnel_model"]["stages"] == FUNNEL_STAGES
    assert result.trigger_event["funnel_model"]["revenue_path"] == "subscriptions"
    assert result.trigger_event["funnel_model"]["inbound_source"] == "forms"
    assert "hubspot_deal" in result.trigger_event
    assert "stripe_subscription" in result.trigger_event
    assert "zapier_trigger" in result.trigger_event
    assert "linear_issue" in result.trigger_event
    assert "github_issue" in result.trigger_event
    assert "notion_page" in result.trigger_event


def test_build_conical_trigger_blocks_high_risk_without_approval(monkeypatch):
    monkeypatch.setenv("CONICAL_HIGH_RISK_AMOUNT", "1000")
    payload = _base_payload()
    payload["commerce"]["amount"] = 5000
    payload["governance"] = {"approved": False}

    result = build_conical_trigger(payload)
    assert result.status == "blocked"
    assert result.blocked_reason
    assert result.trigger_event == {}


def test_build_conical_trigger_allows_high_risk_with_approval(monkeypatch):
    monkeypatch.setenv("CONICAL_HIGH_RISK_AMOUNT", "1000")
    payload = _base_payload()
    payload["commerce"]["amount"] = 5000
    payload["governance"] = {
        "approved": True,
        "approval_reference": "REVOPS-APPROVED-1",
    }

    result = build_conical_trigger(payload)
    assert result.status == "ok"
    assert result.trigger_event["governance"]["high_risk"] is True


def test_main_conical_metrics_rollup(monkeypatch):
    import main

    monkeypatch.setattr(main, "_conical_runs", [])
    e1 = build_conical_trigger(_base_payload()).trigger_event
    p2 = _base_payload()
    p2["commerce"]["amount"] = 1000
    p2["commerce"]["mrr"] = 1000
    p2["analytics"]["cac"] = 300
    e2 = build_conical_trigger(p2).trigger_event

    main._record_conical_run(e1, str(uuid.uuid4()))
    main._record_conical_run(e2, str(uuid.uuid4()))
    summary = main._conical_metrics_summary()

    assert summary["runs"] == 2
    assert summary["totals"]["booked_revenue"] == 3000.0
    assert summary["totals"]["mrr"] == 3000.0
    assert summary["averages"]["cac"] == 400.0
