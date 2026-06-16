"""GoPhish REST API client.

Provides a lightweight, dependency-free client that mirrors the essential
operations of the GoPhish admin REST API:

* Connection management and health checks
* Campaign CRUD (create, launch, list, get results)
* Landing page management
* Email template management
* Target group management
* SMTP / sending profile management
* Result timeline access

The implementation is intentionally self-contained so that tests can run
without an actual GoPhish server.  In a production deployment the private
methods would dispatch real HTTP requests via ``requests`` or ``httpx``.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class GoPhishConfig:
    """Connection parameters for a GoPhish admin server.

    Args:
        server_url: Base URL of the GoPhish admin interface.
        api_key: GoPhish API key for authentication.
        verify_ssl: Whether to verify TLS certificates.
    """

    server_url: str = "https://localhost:3333"
    api_key: str = ""
    verify_ssl: bool = True


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class EmailTemplate:
    """Represents a GoPhish email template.

    Attributes:
        template_id: Unique template identifier.
        name: Human-readable template name.
        subject: Email subject line.
        html: HTML body content.
        text: Plain-text body content.
        created_at: Unix timestamp of creation.
    """

    template_id: str
    name: str
    subject: str = ""
    html: str = ""
    text: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class LandingPage:
    """Represents a GoPhish landing page.

    Attributes:
        page_id: Unique landing page identifier.
        name: Human-readable page name.
        html: HTML content of the page.
        capture_credentials: Whether to capture submitted credentials.
        capture_passwords: Whether to capture passwords specifically.
        redirect_url: URL to redirect to after form submission.
        created_at: Unix timestamp of creation.
    """

    page_id: str
    name: str
    html: str = ""
    capture_credentials: bool = True
    capture_passwords: bool = True
    redirect_url: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class TargetGroup:
    """Represents a GoPhish target group.

    Attributes:
        group_id: Unique group identifier.
        name: Human-readable group name.
        targets: List of target email addresses.
        created_at: Unix timestamp of creation.
    """

    group_id: str
    name: str
    targets: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class SmtpProfile:
    """Represents a GoPhish sending (SMTP) profile.

    Attributes:
        smtp_id: Unique SMTP profile identifier.
        name: Human-readable profile name.
        host: SMTP server host.
        port: SMTP server port.
        username: SMTP username.
        from_address: Sender email address.
        created_at: Unix timestamp of creation.
    """

    smtp_id: str
    name: str
    host: str = ""
    port: int = 587
    username: str = ""
    from_address: str = ""
    created_at: float = field(default_factory=time.time)


@dataclass
class Campaign:
    """Represents a GoPhish phishing campaign.

    Attributes:
        campaign_id: Unique campaign identifier.
        name: Human-readable campaign name.
        template: Email template name.
        landing_page: Landing page name.
        group: Target group name.
        smtp: SMTP profile name.
        url: Base URL for phishing links.
        status: Current campaign status.
        created_at: Unix timestamp of creation.
    """

    campaign_id: int
    name: str
    template: str = ""
    landing_page: str = ""
    group: str = ""
    smtp: str = ""
    url: str = ""
    status: str = "created"
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class GoPhishClient:
    """Lightweight GoPhish REST API client.

    The client manages in-memory stores for campaigns, templates, landing
    pages, groups, and SMTP profiles, validating inputs before dispatching
    to the (mocked) HTTP layer.

    Args:
        config: Optional :class:`GoPhishConfig`.  Defaults to
            ``GoPhishConfig()`` when *None*.
    """

    def __init__(self, config: GoPhishConfig | None = None) -> None:
        self.config = config or GoPhishConfig()
        self._connected: bool = False
        self._campaigns: dict[int, Campaign] = {}
        self._templates: dict[str, EmailTemplate] = {}
        self._landing_pages: dict[str, LandingPage] = {}
        self._groups: dict[str, TargetGroup] = {}
        self._smtp_profiles: dict[str, SmtpProfile] = {}
        self._next_campaign_id: int = 1

    # -- properties -----------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Whether the client is connected to the GoPhish server."""
        return self._connected

    @property
    def campaign_count(self) -> int:
        """Number of campaigns tracked by this client."""
        return len(self._campaigns)

    @property
    def template_count(self) -> int:
        """Number of email templates tracked by this client."""
        return len(self._templates)

    @property
    def landing_page_count(self) -> int:
        """Number of landing pages tracked by this client."""
        return len(self._landing_pages)

    @property
    def group_count(self) -> int:
        """Number of target groups tracked by this client."""
        return len(self._groups)

    @property
    def smtp_count(self) -> int:
        """Number of SMTP profiles tracked by this client."""
        return len(self._smtp_profiles)

    # -- connection management ------------------------------------------

    def connect(self) -> bool:
        """Establish a connection to the GoPhish server.

        Returns:
            ``True`` if the connection succeeded, ``False`` otherwise.
        """
        if not self.config.server_url:
            return False
        if not self.config.api_key:
            return False
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Disconnect from the GoPhish server and clear all state."""
        self._connected = False
        self._campaigns.clear()
        self._templates.clear()
        self._landing_pages.clear()
        self._groups.clear()
        self._smtp_profiles.clear()

    def health_check(self) -> dict[str, Any]:
        """Check the GoPhish server health.

        Returns:
            A dict with ``"status"`` (``"ok"`` or ``"error"``) and
            optional ``"detail"``.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected"}
        return {"status": "ok", "version": "0.12.1"}

    # -- campaign management --------------------------------------------

    def create_campaign(
        self,
        name: str,
        template: str,
        landing_page: str,
        group: str,
        smtp: str = "default",
        url: str = "",
    ) -> dict[str, Any]:
        """Create a new phishing campaign.

        Args:
            name: Campaign name.
            template: Email template name.
            landing_page: Landing page name.
            group: Target group name.
            smtp: Sending profile name.
            url: Base URL for phishing links.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if not name:
            return {"status": "error", "detail": "Campaign name is required"}
        if not template:
            return {"status": "error", "detail": "Email template is required"}
        if not landing_page:
            return {"status": "error", "detail": "Landing page is required"}
        if not group:
            return {"status": "error", "detail": "Target group is required"}

        campaign_id = self._next_campaign_id
        self._next_campaign_id += 1

        campaign = Campaign(
            campaign_id=campaign_id,
            name=name,
            template=template,
            landing_page=landing_page,
            group=group,
            smtp=smtp,
            url=url,
        )
        self._campaigns[campaign_id] = campaign
        return {"status": "ok", "campaign_id": campaign_id, "name": name}

    def list_campaigns(self) -> list[Campaign]:
        """Return all tracked campaigns.

        Returns:
            A list of :class:`Campaign` objects.  Always returns an
            empty list when not connected.
        """
        if not self._connected:
            return []
        return list(self._campaigns.values())

    def get_campaign(self, campaign_id: int) -> Campaign | None:
        """Look up a campaign by ID.

        Args:
            campaign_id: The unique campaign identifier.

        Returns:
            The matching :class:`Campaign`, or ``None`` if not found.
        """
        return self._campaigns.get(campaign_id)

    def launch_campaign(self, campaign_id: int) -> dict[str, Any]:
        """Launch a campaign.

        Args:
            campaign_id: The campaign to launch.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}

        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return {
                "status": "error",
                "detail": f"Campaign {campaign_id} not found",
            }

        campaign.status = "running"
        return {"status": "ok", "campaign_id": campaign_id}

    def get_campaign_results(self, campaign_id: int) -> dict[str, Any]:
        """Retrieve the results for a campaign.

        Args:
            campaign_id: The campaign to query.

        Returns:
            A result dict with ``"status"`` and, on success, ``"stats"``
            containing aggregated metrics.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}

        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return {
                "status": "error",
                "detail": f"Campaign {campaign_id} not found",
            }

        return {
            "status": "ok",
            "campaign_id": campaign_id,
            "stats": {
                "sent": 100,
                "delivered": 98,
                "opened": 45,
                "clicked": 23,
                "submitted_data": 12,
                "reported": 3,
                "bounced": 2,
            },
        }

    def get_campaign_timeline(
        self, campaign_id: int
    ) -> list[dict[str, Any]]:
        """Retrieve the event timeline for a campaign.

        Args:
            campaign_id: The campaign to query.

        Returns:
            A list of event dicts.  Returns an empty list when not
            connected or when the campaign is not found.
        """
        if not self._connected:
            return []

        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return []

        return [
            {
                "id": 1,
                "campaign_id": campaign_id,
                "email": "user1@example.com",
                "time": time.time(),
                "message": "Email Sent",
                "details": "",
            },
            {
                "id": 2,
                "campaign_id": campaign_id,
                "email": "user1@example.com",
                "time": time.time(),
                "message": "Email Opened",
                "details": "",
            },
            {
                "id": 3,
                "campaign_id": campaign_id,
                "email": "user1@example.com",
                "time": time.time(),
                "message": "Clicked Link",
                "details": "",
            },
        ]

    # -- template management --------------------------------------------

    def create_template(
        self,
        name: str,
        subject: str = "",
        html: str = "",
        text: str = "",
    ) -> dict[str, Any]:
        """Create a new email template.

        Args:
            name: Template name.
            subject: Email subject line.
            html: HTML body content.
            text: Plain-text body content.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if not name:
            return {"status": "error", "detail": "Template name is required"}

        template_id = str(uuid.uuid4())
        template = EmailTemplate(
            template_id=template_id,
            name=name,
            subject=subject,
            html=html,
            text=text,
        )
        self._templates[template_id] = template
        return {"status": "ok", "template_id": template_id, "name": name}

    def list_templates(self) -> list[EmailTemplate]:
        """Return all tracked email templates.

        Returns:
            A list of :class:`EmailTemplate` objects.
        """
        if not self._connected:
            return []
        return list(self._templates.values())

    def get_template(self, template_id: str) -> EmailTemplate | None:
        """Look up a template by ID.

        Args:
            template_id: The unique template identifier.

        Returns:
            The matching :class:`EmailTemplate`, or ``None``.
        """
        return self._templates.get(template_id)

    def delete_template(self, template_id: str) -> dict[str, Any]:
        """Delete an email template.

        Args:
            template_id: The template to delete.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if template_id not in self._templates:
            return {
                "status": "error",
                "detail": f"Template {template_id!r} not found",
            }
        del self._templates[template_id]
        return {"status": "ok", "template_id": template_id}

    # -- landing page management ----------------------------------------

    def create_landing_page(
        self,
        name: str,
        html: str = "",
        capture_credentials: bool = True,
        capture_passwords: bool = True,
        redirect_url: str = "",
    ) -> dict[str, Any]:
        """Create a new landing page.

        Args:
            name: Landing page name.
            html: HTML content.
            capture_credentials: Whether to capture submitted credentials.
            capture_passwords: Whether to capture passwords.
            redirect_url: URL to redirect to after submission.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if not name:
            return {"status": "error", "detail": "Landing page name is required"}

        page_id = str(uuid.uuid4())
        page = LandingPage(
            page_id=page_id,
            name=name,
            html=html,
            capture_credentials=capture_credentials,
            capture_passwords=capture_passwords,
            redirect_url=redirect_url,
        )
        self._landing_pages[page_id] = page
        return {"status": "ok", "page_id": page_id, "name": name}

    def list_landing_pages(self) -> list[LandingPage]:
        """Return all tracked landing pages.

        Returns:
            A list of :class:`LandingPage` objects.
        """
        if not self._connected:
            return []
        return list(self._landing_pages.values())

    def get_landing_page(self, page_id: str) -> LandingPage | None:
        """Look up a landing page by ID.

        Args:
            page_id: The unique page identifier.

        Returns:
            The matching :class:`LandingPage`, or ``None``.
        """
        return self._landing_pages.get(page_id)

    def delete_landing_page(self, page_id: str) -> dict[str, Any]:
        """Delete a landing page.

        Args:
            page_id: The page to delete.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if page_id not in self._landing_pages:
            return {
                "status": "error",
                "detail": f"Landing page {page_id!r} not found",
            }
        del self._landing_pages[page_id]
        return {"status": "ok", "page_id": page_id}

    # -- group management -----------------------------------------------

    def create_group(
        self, name: str, targets: list[str] | None = None
    ) -> dict[str, Any]:
        """Create a new target group.

        Args:
            name: Group name.
            targets: List of target email addresses.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if not name:
            return {"status": "error", "detail": "Group name is required"}

        group_id = str(uuid.uuid4())
        group = TargetGroup(
            group_id=group_id,
            name=name,
            targets=targets or [],
        )
        self._groups[group_id] = group
        return {"status": "ok", "group_id": group_id, "name": name}

    def list_groups(self) -> list[TargetGroup]:
        """Return all tracked target groups.

        Returns:
            A list of :class:`TargetGroup` objects.
        """
        if not self._connected:
            return []
        return list(self._groups.values())

    def get_group(self, group_id: str) -> TargetGroup | None:
        """Look up a group by ID.

        Args:
            group_id: The unique group identifier.

        Returns:
            The matching :class:`TargetGroup`, or ``None``.
        """
        return self._groups.get(group_id)

    def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a target group.

        Args:
            group_id: The group to delete.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if group_id not in self._groups:
            return {
                "status": "error",
                "detail": f"Group {group_id!r} not found",
            }
        del self._groups[group_id]
        return {"status": "ok", "group_id": group_id}

    # -- SMTP profile management ----------------------------------------

    def create_smtp_profile(
        self,
        name: str,
        host: str = "",
        port: int = 587,
        username: str = "",
        from_address: str = "",
    ) -> dict[str, Any]:
        """Create a new SMTP / sending profile.

        Args:
            name: Profile name.
            host: SMTP server host.
            port: SMTP server port.
            username: SMTP username.
            from_address: Sender email address.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if not name:
            return {"status": "error", "detail": "SMTP profile name is required"}

        smtp_id = str(uuid.uuid4())
        smtp = SmtpProfile(
            smtp_id=smtp_id,
            name=name,
            host=host,
            port=port,
            username=username,
            from_address=from_address,
        )
        self._smtp_profiles[smtp_id] = smtp
        return {"status": "ok", "smtp_id": smtp_id, "name": name}

    def list_smtp_profiles(self) -> list[SmtpProfile]:
        """Return all tracked SMTP profiles.

        Returns:
            A list of :class:`SmtpProfile` objects.
        """
        if not self._connected:
            return []
        return list(self._smtp_profiles.values())

    def get_smtp_profile(self, smtp_id: str) -> SmtpProfile | None:
        """Look up an SMTP profile by ID.

        Args:
            smtp_id: The unique SMTP profile identifier.

        Returns:
            The matching :class:`SmtpProfile`, or ``None``.
        """
        return self._smtp_profiles.get(smtp_id)

    def delete_smtp_profile(self, smtp_id: str) -> dict[str, Any]:
        """Delete an SMTP profile.

        Args:
            smtp_id: The profile to delete.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}
        if smtp_id not in self._smtp_profiles:
            return {
                "status": "error",
                "detail": f"SMTP profile {smtp_id!r} not found",
            }
        del self._smtp_profiles[smtp_id]
        return {"status": "ok", "smtp_id": smtp_id}
