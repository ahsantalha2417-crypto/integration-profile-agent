from datetime import date
from types import SimpleNamespace

from integration_agent.backlog import BacklogItem, metrics, prioritize
from integration_agent.extract import extract_profile
from integration_agent.fetch import html_to_text
from integration_agent.schema import AccessStatus, IntegrationProfile

SAMPLE = {
    "partner": "Acme Loyalty",
    "category": "loyalty",
    "base_url": "https://api.acme.test/v2",
    "api_style": "REST",
    "auth": {"type": "oauth2", "details": "Authorization code flow, read_customers scope"},
    "key_endpoints": [{"method": "GET", "path": "/customers", "purpose": "List loyalty members"}],
    "webhooks": True,
    "rate_limits": {"documented": True, "details": "100 requests/minute"},
    "sandbox": {"available": True, "how_to_get": "Request a dev store"},
    "partner_program": {"required": True, "url": "https://acme.test/partners", "notes": "Approval ~2 weeks"},
    "open_questions": ["Is historical order backfill supported?"],
}


class FakeClient:
    """Stands in for anthropic.Anthropic so tests run without an API key."""

    def __init__(self):
        self.messages = self
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(type="tool_use", input=SAMPLE)])


def test_extract_forces_tool_and_validates():
    client = FakeClient()
    prof = extract_profile("Acme Loyalty", "https://docs.acme.test", "docs...", client=client, model="test-model")
    assert client.last_kwargs["tool_choice"]["name"] == "record_integration_profile"
    assert prof.auth.type.value == "oauth2"
    assert prof.docs_url == "https://docs.acme.test"
    assert prof.access_status == AccessStatus.NOT_STARTED
    assert not prof.build_ready  # access not approved yet


def test_build_ready_and_days_to_access():
    prof = IntegrationProfile(**SAMPLE, docs_url="x", access_status="approved",
                              access_requested_on=date(2026, 9, 1), access_granted_on=date(2026, 9, 15))
    assert prof.build_ready
    assert prof.days_to_access == 14


def test_prioritize_rewards_demand_and_readiness():
    ready = IntegrationProfile(**SAMPLE, docs_url="x", access_status="approved")
    items = [BacklogItem("Low Demand", "u", 1, 2, 4), BacklogItem("Acme Loyalty", "u", 5, 4, 3)]
    ranked = prioritize(items, {"acme-loyalty": ready})
    assert ranked[0][0].partner == "Acme Loyalty"
    assert ranked[0][1] == 2 * 5 + 3 * 4 - 2 * 3 + 5


def test_metrics_coverage():
    prof = IntegrationProfile(**SAMPLE, docs_url="x")
    items = [BacklogItem("Acme Loyalty", "u", 1, 1, 1), BacklogItem("Other", "u", 1, 1, 1)]
    m = metrics(items, {"acme-loyalty": prof})
    assert m["backlog_coverage_pct"] == 50.0
    assert m["open_questions"] == 1


def test_html_to_text_strips_scripts():
    html = "<html><script>x=1</script><h1>Auth</h1><p>Use OAuth 2.0</p></html>"
    assert html_to_text(html) == "Auth\nUse OAuth 2.0"
