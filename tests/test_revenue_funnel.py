import uuid

from revenue_funnel import FUNNEL_STAGES, INBOUND_SOURCES, REVENUE_PATHS, build_conical_trigger


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


# ---------------------------------------------------------------------------
# Normalization fallbacks
# ---------------------------------------------------------------------------


def test_unknown_revenue_path_defaults_to_services():
    payload = _base_payload()
    payload["funnel"]["revenue_path"] = "nonexistent_path"
    result = build_conical_trigger(payload)
    assert result.status == "ok"
    assert result.trigger_event["funnel_model"]["revenue_path"] == "services"
    assert result.trigger_event["funnel_model"]["revenue_path"] in REVENUE_PATHS


def test_unknown_inbound_source_defaults_to_webhooks():
    payload = _base_payload()
    payload["funnel"]["inbound_source"] = "carrier_pigeon"
    result = build_conical_trigger(payload)
    assert result.status == "ok"
    assert result.trigger_event["funnel_model"]["inbound_source"] == "webhooks"
    assert result.trigger_event["funnel_model"]["inbound_source"] in INBOUND_SOURCES


def test_missing_funnel_and_commerce_fields_use_defaults():
    result = build_conical_trigger({})
    assert result.status == "ok"
    fm = result.trigger_event["funnel_model"]
    assert fm["revenue_path"] in REVENUE_PATHS
    assert fm["inbound_source"] in INBOUND_SOURCES


def test_amount_defaults_to_zero_when_missing():
    payload = _base_payload()
    del payload["commerce"]["amount"]
    result = build_conical_trigger(payload)
    assert result.status == "ok"
    assert result.trigger_event["kpis"]["booked_revenue"] == 0.0


# ---------------------------------------------------------------------------
# Governance edge cases
# ---------------------------------------------------------------------------


def test_high_risk_blocked_when_approval_reference_missing(monkeypatch):
    monkeypatch.setenv("CONICAL_HIGH_RISK_AMOUNT", "1000")
    payload = _base_payload()
    payload["commerce"]["amount"] = 5000
    payload["governance"] = {"approved": True, "approval_reference": ""}
    result = build_conical_trigger(payload)
    assert result.status == "blocked"


def test_string_false_is_not_approved(monkeypatch):
    """The string 'false' must not be treated as an approved flag."""
    monkeypatch.setenv("CONICAL_HIGH_RISK_AMOUNT", "1000")
    payload = _base_payload()
    payload["commerce"]["amount"] = 5000
    payload["governance"] = {"approved": "false", "approval_reference": "REVOPS-1"}
    result = build_conical_trigger(payload)
    assert result.status == "blocked"


def test_string_true_is_approved(monkeypatch):
    """The string 'true' should be treated as an approved flag."""
    monkeypatch.setenv("CONICAL_HIGH_RISK_AMOUNT", "1000")
    payload = _base_payload()
    payload["commerce"]["amount"] = 5000
    payload["governance"] = {"approved": "true", "approval_reference": "REVOPS-1"}
    result = build_conical_trigger(payload)
    assert result.status == "ok"


def test_low_risk_transaction_allowed_without_governance():
    payload = _base_payload()
    payload["commerce"]["amount"] = 100
    payload["governance"] = {}
    result = build_conical_trigger(payload)
    assert result.status == "ok"


# ---------------------------------------------------------------------------
# Metrics rollup
# ---------------------------------------------------------------------------


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


def test_main_conical_metrics_empty_history(monkeypatch):
    import main

    monkeypatch.setattr(main, "_conical_runs", [])
    summary = main._conical_metrics_summary()
    assert summary["runs"] == 0
    assert summary["averages"] == {}
    assert summary["totals"] == {}
    assert summary["by_revenue_path"] == {}
    assert summary["by_source"] == {}
    assert summary["stages"] == FUNNEL_STAGES


def test_main_conical_metrics_by_revenue_path_and_source(monkeypatch):
    import main

    monkeypatch.setattr(main, "_conical_runs", [])

    p1 = _base_payload()
    p1["funnel"]["revenue_path"] = "subscriptions"
    p1["funnel"]["inbound_source"] = "ads"
    e1 = build_conical_trigger(p1).trigger_event

    p2 = _base_payload()
    p2["funnel"]["revenue_path"] = "subscriptions"
    p2["funnel"]["inbound_source"] = "forms"
    e2 = build_conical_trigger(p2).trigger_event

    p3 = _base_payload()
    p3["funnel"]["revenue_path"] = "services"
    p3["funnel"]["inbound_source"] = "ads"
    e3 = build_conical_trigger(p3).trigger_event

    for e in (e1, e2, e3):
        main._record_conical_run(e, str(uuid.uuid4()))

    summary = main._conical_metrics_summary()
    assert summary["by_revenue_path"]["subscriptions"] == 2
    assert summary["by_revenue_path"]["services"] == 1
    assert summary["by_source"]["ads"] == 2
    assert summary["by_source"]["forms"] == 1
