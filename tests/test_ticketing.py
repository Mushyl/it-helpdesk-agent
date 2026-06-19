"""Unit tests for ticketing.py — Jira / ServiceNow payload mapping (pure)."""

import json

import ticketing


# --------------------------------------------------------------------------
# Jira
# --------------------------------------------------------------------------
def test_jira_high_urgency_is_incident_with_high_priority():
    t = ticketing.to_jira_ticket("VPN", "HIGH", "VPN down", "details")
    f = t["fields"]
    assert f["summary"] == "VPN down"
    assert f["issuetype"]["name"] == "Incident"
    assert f["priority"]["name"] == "High"
    assert f["labels"] == ["vpn"]
    assert f["project"]["key"]  # default project key from config


def test_jira_low_urgency_is_service_request():
    t = ticketing.to_jira_ticket("SOFTWARE", "LOW", "s", "d")
    assert t["fields"]["issuetype"]["name"] == "Service Request"
    assert t["fields"]["priority"]["name"] == "Low"


def test_jira_security_is_incident_even_when_not_high():
    t = ticketing.to_jira_ticket("SECURITY", "MEDIUM", "s", "d")
    assert t["fields"]["issuetype"]["name"] == "Incident"


def test_jira_custom_project_key():
    t = ticketing.to_jira_ticket("VPN", "LOW", "s", "d", project_key="HELP")
    assert t["fields"]["project"]["key"] == "HELP"


# --------------------------------------------------------------------------
# ServiceNow
# --------------------------------------------------------------------------
def test_servicenow_structure_and_high_urgency():
    t = ticketing.to_servicenow_ticket("VPN", "HIGH", "VPN down", "details")
    assert t["short_description"] == "VPN down"
    assert t["category"] == "vpn"
    assert t["urgency"] == "1"   # HIGH
    assert t["impact"] == "1"


def test_servicenow_urgency_scale():
    assert ticketing.to_servicenow_ticket("X", "MEDIUM", "s", "d")["urgency"] == "2"
    assert ticketing.to_servicenow_ticket("X", "LOW", "s", "d")["urgency"] == "3"


# --------------------------------------------------------------------------
# build_tickets
# --------------------------------------------------------------------------
def test_build_tickets_has_both_systems_and_is_json_serialisable():
    tickets = ticketing.build_tickets("VPN", "HIGH", "summary", "message", "reply")
    assert set(tickets) == {"jira", "servicenow"}
    json.dumps(tickets)  # must not raise


def test_build_tickets_description_contains_message_and_reply():
    tickets = ticketing.build_tickets(
        "VPN", "HIGH", "sum", "my original message", "the drafted reply"
    )
    jira_desc = tickets["jira"]["fields"]["description"]
    snow_desc = tickets["servicenow"]["description"]
    assert "my original message" in jira_desc
    assert "the drafted reply" in jira_desc
    assert jira_desc == snow_desc


def test_build_tickets_unknown_urgency_defaults_to_medium():
    tickets = ticketing.build_tickets("VPN", "WEIRD", "s", "m", "r")
    assert tickets["jira"]["fields"]["priority"]["name"] == "Medium"
    assert tickets["servicenow"]["urgency"] == "2"
