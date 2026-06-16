"""Tests for the GoPhish phishing simulation module."""

from __future__ import annotations

import pytest

from modules.phishing import CampaignResult, PhishingModule
from modules.phishing.gophish_client import (
    Campaign,
    EmailTemplate,
    GoPhishClient,
    GoPhishConfig,
    LandingPage,
    SmtpProfile,
    TargetGroup,
)


def _connected_client() -> GoPhishClient:
    """Helper: return a connected GoPhishClient with valid config."""
    cfg = GoPhishConfig(
        server_url="https://localhost:3333",
        api_key="test-api-key",
    )
    client = GoPhishClient(config=cfg)
    assert client.connect() is True
    return client


# ---------------------------------------------------------------------------
# GoPhishConfig
# ---------------------------------------------------------------------------


class TestGoPhishConfig:
    def test_defaults(self) -> None:
        cfg = GoPhishConfig()
        assert cfg.server_url == "https://localhost:3333"
        assert cfg.api_key == ""
        assert cfg.verify_ssl is True

    def test_custom(self) -> None:
        cfg = GoPhishConfig(
            server_url="https://gophish.example.com",
            api_key="abc123",
            verify_ssl=False,
        )
        assert cfg.server_url == "https://gophish.example.com"
        assert cfg.api_key == "abc123"
        assert cfg.verify_ssl is False


# ---------------------------------------------------------------------------
# GoPhishClient connection management
# ---------------------------------------------------------------------------


class TestGoPhishClientConnect:
    def test_connect_success(self) -> None:
        client = _connected_client()
        assert client.is_connected is True

    def test_connect_missing_url(self) -> None:
        cfg = GoPhishConfig(server_url="", api_key="key")
        client = GoPhishClient(config=cfg)
        assert client.connect() is False
        assert client.is_connected is False

    def test_connect_missing_api_key(self) -> None:
        cfg = GoPhishConfig(server_url="https://localhost:3333", api_key="")
        client = GoPhishClient(config=cfg)
        assert client.connect() is False
        assert client.is_connected is False

    def test_disconnect(self) -> None:
        client = _connected_client()
        client.disconnect()
        assert client.is_connected is False
        assert client.campaign_count == 0

    def test_disconnect_clears_state(self) -> None:
        client = _connected_client()
        client.create_template("t1", subject="Hi")
        client.create_group("g1", targets=["a@b.com"])
        client.disconnect()
        assert client.template_count == 0
        assert client.group_count == 0

    def test_health_check_connected(self) -> None:
        client = _connected_client()
        result = client.health_check()
        assert result["status"] == "ok"
        assert "version" in result

    def test_health_check_not_connected(self) -> None:
        client = GoPhishClient()
        result = client.health_check()
        assert result["status"] == "error"
        assert "Not connected" in result["detail"]


# ---------------------------------------------------------------------------
# GoPhishClient campaign management
# ---------------------------------------------------------------------------


class TestGoPhishClientCampaign:
    def setup_method(self) -> None:
        self.client = _connected_client()

    def test_create_campaign_ok(self) -> None:
        result = self.client.create_campaign(
            name="Camp1",
            template="welcome.html",
            landing_page="portal-login",
            group="Employees",
            smtp="default",
        )
        assert result["status"] == "ok"
        assert result["name"] == "Camp1"
        assert isinstance(result["campaign_id"], int)

    def test_create_campaign_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.create_campaign(
            name="X", template="t", landing_page="lp", group="g"
        )
        assert result["status"] == "error"
        assert "Not connected" in result["detail"]

    def test_create_campaign_missing_name(self) -> None:
        result = self.client.create_campaign(
            name="", template="t", landing_page="lp", group="g"
        )
        assert result["status"] == "error"
        assert "name is required" in result["detail"]

    def test_create_campaign_missing_template(self) -> None:
        result = self.client.create_campaign(
            name="Camp", template="", landing_page="lp", group="g"
        )
        assert result["status"] == "error"
        assert "template" in result["detail"]

    def test_create_campaign_missing_landing_page(self) -> None:
        result = self.client.create_campaign(
            name="Camp", template="t", landing_page="", group="g"
        )
        assert result["status"] == "error"
        assert "Landing page" in result["detail"]

    def test_create_campaign_missing_group(self) -> None:
        result = self.client.create_campaign(
            name="Camp", template="t", landing_page="lp", group=""
        )
        assert result["status"] == "error"
        assert "group" in result["detail"]

    def test_list_campaigns_empty(self) -> None:
        assert self.client.list_campaigns() == []

    def test_list_campaigns_not_connected(self) -> None:
        client2 = GoPhishClient()
        assert client2.list_campaigns() == []

    def test_list_campaigns_after_create(self) -> None:
        self.client.create_campaign("C1", "t", "lp", "g")
        self.client.create_campaign("C2", "t", "lp", "g")
        assert self.client.campaign_count == 2
        campaigns = self.client.list_campaigns()
        assert len(campaigns) == 2

    def test_get_campaign(self) -> None:
        created = self.client.create_campaign("MyCamp", "t", "lp", "g")
        camp = self.client.get_campaign(created["campaign_id"])
        assert camp is not None
        assert camp.name == "MyCamp"
        assert isinstance(camp, Campaign)

    def test_get_campaign_not_found(self) -> None:
        assert self.client.get_campaign(99999) is None

    def test_launch_campaign_ok(self) -> None:
        created = self.client.create_campaign("LaunchMe", "t", "lp", "g")
        result = self.client.launch_campaign(created["campaign_id"])
        assert result["status"] == "ok"
        campaign = self.client.get_campaign(created["campaign_id"])
        assert campaign is not None
        assert campaign.status == "running"

    def test_launch_campaign_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.launch_campaign(1)
        assert result["status"] == "error"

    def test_launch_campaign_not_found(self) -> None:
        result = self.client.launch_campaign(99999)
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_get_campaign_results_ok(self) -> None:
        created = self.client.create_campaign("ResCamp", "t", "lp", "g")
        result = self.client.get_campaign_results(created["campaign_id"])
        assert result["status"] == "ok"
        stats = result["stats"]
        assert "sent" in stats
        assert "delivered" in stats
        assert "opened" in stats
        assert "clicked" in stats
        assert "submitted_data" in stats
        assert "reported" in stats
        assert "bounced" in stats

    def test_get_campaign_results_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.get_campaign_results(1)
        assert result["status"] == "error"

    def test_get_campaign_results_not_found(self) -> None:
        result = self.client.get_campaign_results(99999)
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_get_campaign_timeline(self) -> None:
        created = self.client.create_campaign("TL", "t", "lp", "g")
        timeline = self.client.get_campaign_timeline(created["campaign_id"])
        assert len(timeline) > 0
        assert timeline[0]["campaign_id"] == created["campaign_id"]

    def test_get_campaign_timeline_not_connected(self) -> None:
        client2 = GoPhishClient()
        assert client2.get_campaign_timeline(1) == []

    def test_get_campaign_timeline_not_found(self) -> None:
        assert self.client.get_campaign_timeline(99999) == []


# ---------------------------------------------------------------------------
# GoPhishClient template management
# ---------------------------------------------------------------------------


class TestGoPhishClientTemplate:
    def setup_method(self) -> None:
        self.client = _connected_client()

    def test_create_template_ok(self) -> None:
        result = self.client.create_template(
            name="Welcome",
            subject="Welcome!",
            html="<h1>Hello</h1>",
        )
        assert result["status"] == "ok"
        assert result["name"] == "Welcome"

    def test_create_template_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.create_template(name="X")
        assert result["status"] == "error"

    def test_create_template_missing_name(self) -> None:
        result = self.client.create_template(name="")
        assert result["status"] == "error"
        assert "name is required" in result["detail"]

    def test_list_templates(self) -> None:
        self.client.create_template(name="T1")
        self.client.create_template(name="T2")
        assert self.client.template_count == 2
        templates = self.client.list_templates()
        assert len(templates) == 2
        assert all(isinstance(t, EmailTemplate) for t in templates)

    def test_list_templates_not_connected(self) -> None:
        client2 = GoPhishClient()
        assert client2.list_templates() == []

    def test_get_template(self) -> None:
        created = self.client.create_template(name="MyTmpl", subject="Subj")
        tmpl = self.client.get_template(created["template_id"])
        assert tmpl is not None
        assert tmpl.name == "MyTmpl"
        assert tmpl.subject == "Subj"

    def test_get_template_not_found(self) -> None:
        assert self.client.get_template("no-such-id") is None

    def test_delete_template_ok(self) -> None:
        created = self.client.create_template(name="ToDelete")
        tid = created["template_id"]
        result = self.client.delete_template(tid)
        assert result["status"] == "ok"
        assert self.client.get_template(tid) is None

    def test_delete_template_not_found(self) -> None:
        result = self.client.delete_template("ghost")
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_delete_template_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.delete_template("x")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# GoPhishClient landing page management
# ---------------------------------------------------------------------------


class TestGoPhishClientLandingPage:
    def setup_method(self) -> None:
        self.client = _connected_client()

    def test_create_landing_page_ok(self) -> None:
        result = self.client.create_landing_page(
            name="Login Portal",
            html="<form>...</form>",
            capture_credentials=True,
            redirect_url="https://example.com/thanks",
        )
        assert result["status"] == "ok"
        assert result["name"] == "Login Portal"

    def test_create_landing_page_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.create_landing_page(name="X")
        assert result["status"] == "error"

    def test_create_landing_page_missing_name(self) -> None:
        result = self.client.create_landing_page(name="")
        assert result["status"] == "error"
        assert "name is required" in result["detail"]

    def test_list_landing_pages(self) -> None:
        self.client.create_landing_page(name="LP1")
        self.client.create_landing_page(name="LP2")
        assert self.client.landing_page_count == 2
        pages = self.client.list_landing_pages()
        assert len(pages) == 2
        assert all(isinstance(p, LandingPage) for p in pages)

    def test_list_landing_pages_not_connected(self) -> None:
        client2 = GoPhishClient()
        assert client2.list_landing_pages() == []

    def test_get_landing_page(self) -> None:
        created = self.client.create_landing_page(name="MyPage")
        page = self.client.get_landing_page(created["page_id"])
        assert page is not None
        assert page.name == "MyPage"
        assert page.capture_credentials is True

    def test_get_landing_page_not_found(self) -> None:
        assert self.client.get_landing_page("nope") is None

    def test_delete_landing_page_ok(self) -> None:
        created = self.client.create_landing_page(name="DelLP")
        pid = created["page_id"]
        result = self.client.delete_landing_page(pid)
        assert result["status"] == "ok"
        assert self.client.get_landing_page(pid) is None

    def test_delete_landing_page_not_found(self) -> None:
        result = self.client.delete_landing_page("ghost")
        assert result["status"] == "error"

    def test_delete_landing_page_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.delete_landing_page("x")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# GoPhishClient target group management
# ---------------------------------------------------------------------------


class TestGoPhishClientGroup:
    def setup_method(self) -> None:
        self.client = _connected_client()

    def test_create_group_ok(self) -> None:
        targets = ["a@example.com", "b@example.com"]
        result = self.client.create_group(name="All Employees", targets=targets)
        assert result["status"] == "ok"
        assert result["name"] == "All Employees"
        group = self.client.get_group(result["group_id"])
        assert group is not None
        assert len(group.targets) == 2

    def test_create_group_empty_targets(self) -> None:
        result = self.client.create_group(name="Empty Group")
        assert result["status"] == "ok"
        group = self.client.get_group(result["group_id"])
        assert group is not None
        assert group.targets == []

    def test_create_group_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.create_group(name="X")
        assert result["status"] == "error"

    def test_create_group_missing_name(self) -> None:
        result = self.client.create_group(name="")
        assert result["status"] == "error"
        assert "name is required" in result["detail"]

    def test_list_groups(self) -> None:
        self.client.create_group(name="G1", targets=["a@b.com"])
        self.client.create_group(name="G2", targets=["c@d.com"])
        assert self.client.group_count == 2
        groups = self.client.list_groups()
        assert len(groups) == 2
        assert all(isinstance(g, TargetGroup) for g in groups)

    def test_list_groups_not_connected(self) -> None:
        client2 = GoPhishClient()
        assert client2.list_groups() == []

    def test_get_group_not_found(self) -> None:
        assert self.client.get_group("nope") is None

    def test_delete_group_ok(self) -> None:
        created = self.client.create_group(name="DelG", targets=["x@y.com"])
        gid = created["group_id"]
        result = self.client.delete_group(gid)
        assert result["status"] == "ok"
        assert self.client.get_group(gid) is None

    def test_delete_group_not_found(self) -> None:
        result = self.client.delete_group("ghost")
        assert result["status"] == "error"

    def test_delete_group_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.delete_group("x")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# GoPhishClient SMTP profile management
# ---------------------------------------------------------------------------


class TestGoPhishClientSmtp:
    def setup_method(self) -> None:
        self.client = _connected_client()

    def test_create_smtp_profile_ok(self) -> None:
        result = self.client.create_smtp_profile(
            name="Corporate SMTP",
            host="smtp.example.com",
            port=587,
            username="sender@example.com",
            from_address="sender@example.com",
        )
        assert result["status"] == "ok"
        assert result["name"] == "Corporate SMTP"

    def test_create_smtp_profile_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.create_smtp_profile(name="X")
        assert result["status"] == "error"

    def test_create_smtp_profile_missing_name(self) -> None:
        result = self.client.create_smtp_profile(name="")
        assert result["status"] == "error"
        assert "name is required" in result["detail"]

    def test_list_smtp_profiles(self) -> None:
        self.client.create_smtp_profile(name="SMTP1", host="h1.example.com")
        self.client.create_smtp_profile(name="SMTP2", host="h2.example.com")
        assert self.client.smtp_count == 2
        profiles = self.client.list_smtp_profiles()
        assert len(profiles) == 2
        assert all(isinstance(p, SmtpProfile) for p in profiles)

    def test_list_smtp_profiles_not_connected(self) -> None:
        client2 = GoPhishClient()
        assert client2.list_smtp_profiles() == []

    def test_get_smtp_profile(self) -> None:
        created = self.client.create_smtp_profile(
            name="MySMTP", host="smtp.test.com"
        )
        smtp = self.client.get_smtp_profile(created["smtp_id"])
        assert smtp is not None
        assert smtp.name == "MySMTP"
        assert smtp.host == "smtp.test.com"

    def test_get_smtp_profile_not_found(self) -> None:
        assert self.client.get_smtp_profile("nope") is None

    def test_delete_smtp_profile_ok(self) -> None:
        created = self.client.create_smtp_profile(name="DelSMTP")
        sid = created["smtp_id"]
        result = self.client.delete_smtp_profile(sid)
        assert result["status"] == "ok"
        assert self.client.get_smtp_profile(sid) is None

    def test_delete_smtp_profile_not_found(self) -> None:
        result = self.client.delete_smtp_profile("ghost")
        assert result["status"] == "error"

    def test_delete_smtp_profile_not_connected(self) -> None:
        client2 = GoPhishClient()
        result = client2.delete_smtp_profile("x")
        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# PhishingModule orchestrator
# ---------------------------------------------------------------------------


class TestPhishingModuleInit:
    def test_default_init(self) -> None:
        mod = PhishingModule()
        assert mod.client is not None
        assert mod.campaign_count == 0

    def test_custom_init(self) -> None:
        mod = PhishingModule(
            server_url="https://gophish.test",
            api_key="key123",
            verify_ssl=False,
        )
        assert mod.client.config.server_url == "https://gophish.test"
        assert mod.client.config.api_key == "key123"
        assert mod.client.config.verify_ssl is False


class TestPhishingModuleCreateCampaign:
    def setup_method(self) -> None:
        self.mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        self.mod.client.connect()

    def test_create_campaign_ok(self) -> None:
        result = self.mod.create_campaign(
            name="Security Awareness Q1",
            template="welcome.html",
            landing_page="portal-login",
            group="All Employees",
            smtp="default",
        )
        assert result["status"] == "ok"
        assert self.mod.campaign_count == 1

    def test_create_campaign_not_connected(self) -> None:
        mod2 = PhishingModule(api_key="k")
        # Not connected — no connect() call
        result = mod2.create_campaign(
            name="X", template="t", landing_page="lp", group="g"
        )
        assert result["status"] == "error"
        assert "Not connected" in result["detail"]

    def test_create_campaign_tracked(self) -> None:
        result = self.mod.create_campaign(
            name="CampA", template="t", landing_page="lp", group="g"
        )
        assert result["status"] == "ok"
        assert self.mod._campaigns[0].name == "CampA"
        assert self.mod._campaigns[0].status == "created"


class TestPhishingModuleLaunchCampaign:
    def setup_method(self) -> None:
        self.mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        self.mod.client.connect()
        self.created = self.mod.create_campaign(
            name="LaunchTest", template="t", landing_page="lp", group="g"
        )

    def test_launch_campaign_ok(self) -> None:
        result = self.mod.launch_campaign(self.created["campaign_id"])
        assert result["status"] == "ok"
        assert self.mod._campaigns[0].status == "running"

    def test_launch_not_connected(self) -> None:
        mod2 = PhishingModule(api_key="k")
        result = mod2.launch_campaign(1)
        assert result["status"] == "error"


class TestPhishingModuleGetResults:
    def setup_method(self) -> None:
        self.mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        self.mod.client.connect()
        self.created = self.mod.create_campaign(
            name="ResultsTest", template="t", landing_page="lp", group="g"
        )

    def test_get_results_ok(self) -> None:
        result = self.mod.get_results(self.created["campaign_id"])
        assert result["status"] == "ok"
        assert "stats" in result
        campaign = self.mod._campaigns[0]
        assert campaign.status == "completed"
        assert "sent" in campaign.stats

    def test_get_results_not_connected(self) -> None:
        mod2 = PhishingModule(api_key="k")
        result = mod2.get_results(1)
        assert result["status"] == "error"


class TestPhishingModuleRun:
    def test_run_no_campaigns(self) -> None:
        mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        mod.client.connect()
        result = mod.run()
        assert result["status"] == "error"
        assert "No campaigns configured" in result["detail"]

    def test_run_not_connected(self) -> None:
        mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        # Don't connect — but we need a campaign tracked.
        # Manually add a campaign to test the branch.
        # Actually the run() checks connected first, so this works:
        mod._campaigns.append(
            CampaignResult(campaign_id=1, name="Fake", status="created")
        )
        result = mod.run()
        assert result["status"] == "error"
        assert "Not connected" in result["detail"]

    def test_run_success(self) -> None:
        mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        mod.client.connect()
        mod.create_campaign(
            name="Full Run", template="t", landing_page="lp", group="g"
        )
        result = mod.run()
        assert result["status"] == "ok"
        assert len(result["results"]) == 1
        assert result["results"][0]["status"] == "completed"

    def test_run_multiple_campaigns(self) -> None:
        mod = PhishingModule(
            server_url="https://localhost:3333",
            api_key="test-key",
        )
        mod.client.connect()
        mod.create_campaign("Camp1", "t", "lp", "g")
        mod.create_campaign("Camp2", "t", "lp", "g")
        result = mod.run()
        assert result["status"] == "ok"
        assert len(result["results"]) == 2


# ---------------------------------------------------------------------------
# Integration-style: full lifecycle
# ---------------------------------------------------------------------------


class TestFullLifecycle:
    def test_create_template_landing_group_campaign(self) -> None:
        """Create all dependent objects and run a campaign."""
        client = _connected_client()

        # Create template
        tmpl = client.create_template(
            name="PhishTmpl",
            subject="Action Required",
            html="<p>Click <a href='{{.URL}}'>here</a></p>",
        )
        assert tmpl["status"] == "ok"

        # Create landing page
        lp = client.create_landing_page(
            name="Fake Portal",
            html="<form method='POST'>...</form>",
            capture_credentials=True,
        )
        assert lp["status"] == "ok"

        # Create group
        grp = client.create_group(
            name="Targets",
            targets=["alice@example.com", "bob@example.com"],
        )
        assert grp["status"] == "ok"

        # Create SMTP profile
        smtp = client.create_smtp_profile(
            name="SendProf",
            host="smtp.example.com",
            from_address="noreply@example.com",
        )
        assert smtp["status"] == "ok"

        # Create campaign
        camp = client.create_campaign(
            name="Full Integration",
            template="PhishTmpl",
            landing_page="Fake Portal",
            group="Targets",
            smtp="SendProf",
        )
        assert camp["status"] == "ok"

        # Launch
        launched = client.launch_campaign(camp["campaign_id"])
        assert launched["status"] == "ok"

        # Results
        results = client.get_campaign_results(camp["campaign_id"])
        assert results["status"] == "ok"

        # Timeline
        timeline = client.get_campaign_timeline(camp["campaign_id"])
        assert len(timeline) > 0

    def test_module_full_workflow(self) -> None:
        """Use PhishingModule to orchestrate a full campaign cycle."""
        mod = PhishingModule(
            server_url="https://gophish.example.com",
            api_key="integration-key",
        )
        assert mod.client.connect() is True

        result = mod.create_campaign(
            name="Integration Campaign",
            template="training.html",
            landing_page="login-clone",
            group="Dept-A",
            smtp="corporate",
        )
        assert result["status"] == "ok"
        assert mod.campaign_count == 1

        run_result = mod.run()
        assert run_result["status"] == "ok"
        assert mod._campaigns[0].status == "completed"
