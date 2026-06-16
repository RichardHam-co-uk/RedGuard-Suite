"""Phishing simulation module.

Provides a high-level orchestrator (:class:`PhishingModule`) that manages
GoPhish-powered phishing campaigns through the :class:`GoPhishClient`
REST wrapper.

Typical usage::

    mod = PhishingModule("https://gophish.example.com", api_key="...")
    mod.create_campaign(
        name="Q1 Security Awareness",
        template="welcome.html",
        landing_page="https://portal.example.com",
        group="All Employees",
        smtp="default",
    )
    mod.run()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.phishing.gophish_client import GoPhishClient, GoPhishConfig

__all__ = [
    "GoPhishClient",
    "GoPhishConfig",
    "PhishingModule",
]


@dataclass
class CampaignResult:
    """Summary of a single phishing campaign execution.

    Attributes:
        campaign_id: GoPhish campaign identifier.
        name: Human-readable campaign name.
        status: Campaign status (``"created"``, ``"running"``,
            ``"completed"``, ``"error"``).
        stats: Aggregated result statistics (sent, opened, clicked, …).
        detail: Optional error detail when *status* is ``"error"``.
    """

    campaign_id: int
    name: str
    status: str
    stats: dict[str, int] = field(default_factory=dict)
    detail: str = ""


class PhishingModule:
    """High-level orchestrator for GoPhish phishing campaigns.

    The module wraps a :class:`GoPhishClient` and provides convenience
    methods for creating, launching, and monitoring campaigns.

    Args:
        server_url: Base URL of the GoPhish admin server.
        api_key: GoPhish API key.
        verify_ssl: Whether to verify TLS certificates.
    """

    def __init__(
        self,
        server_url: str = "https://localhost:3333",
        api_key: str = "",
        verify_ssl: bool = True,
    ) -> None:
        cfg = GoPhishConfig(
            server_url=server_url,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )
        self._client = GoPhishClient(config=cfg)
        self._campaigns: list[CampaignResult] = []

    # -- properties -----------------------------------------------------

    @property
    def client(self) -> GoPhishClient:
        """The underlying :class:`GoPhishClient` instance."""
        return self._client

    @property
    def campaign_count(self) -> int:
        """Number of campaigns tracked by this module."""
        return len(self._campaigns)

    # -- campaign lifecycle ---------------------------------------------

    def create_campaign(
        self,
        name: str,
        template: str,
        landing_page: str,
        group: str,
        smtp: str = "default",
        url: str = "",
    ) -> dict[str, Any]:
        """Create a new phishing campaign in GoPhish.

        Args:
            name: Campaign name.
            template: Email template name.
            landing_page: Landing page name.
            group: Target group name.
            smtp: Sending profile name.
            url: Base URL for phishing links (defaults to GoPhish
                server URL).

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._client.is_connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}

        result = self._client.create_campaign(
            name=name,
            template=template,
            landing_page=landing_page,
            group=group,
            smtp=smtp,
            url=url or self._client.config.server_url,
        )
        if result.get("status") == "ok":
            self._campaigns.append(
                CampaignResult(
                    campaign_id=result["campaign_id"],
                    name=name,
                    status="created",
                )
            )
        return result

    def launch_campaign(self, campaign_id: int) -> dict[str, Any]:
        """Launch an existing campaign.

        Args:
            campaign_id: The GoPhish campaign ID to launch.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._client.is_connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}

        result = self._client.launch_campaign(campaign_id)
        if result.get("status") == "ok":
            for c in self._campaigns:
                if c.campaign_id == campaign_id:
                    c.status = "running"
        return result

    def get_results(self, campaign_id: int) -> dict[str, Any]:
        """Retrieve results for a completed campaign.

        Args:
            campaign_id: The GoPhish campaign ID.

        Returns:
            A result dict with ``"status"`` and, on success,
            ``"stats"`` containing aggregated metrics.
        """
        if not self._client.is_connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}

        result = self._client.get_campaign_results(campaign_id)
        if result.get("status") == "ok":
            for c in self._campaigns:
                if c.campaign_id == campaign_id:
                    c.status = "completed"
                    c.stats = result.get("stats", {})
        return result

    def run(self) -> dict[str, Any]:
        """Execute the full phishing workflow for all tracked campaigns.

        For each campaign the method launches it, waits for completion
        (mocked), and collects results.

        Returns:
            A dict with ``"status"`` (``"ok"``, ``"partial"``, or
            ``"error"``) and per-campaign ``"results"``.
        """
        if not self._campaigns:
            return {"status": "error", "detail": "No campaigns configured"}

        if not self._client.is_connected:
            return {"status": "error", "detail": "Not connected to GoPhish server"}

        results: list[dict[str, Any]] = []
        any_ok = False
        any_fail = False

        for campaign in self._campaigns:
            try:
                launch = self._client.launch_campaign(campaign.campaign_id)
                if launch.get("status") != "ok":
                    any_fail = True
                    campaign.status = "error"
                    campaign.detail = launch.get("detail", "Launch failed")
                    results.append(
                        {
                            "campaign_id": campaign.campaign_id,
                            "name": campaign.name,
                            "status": "error",
                            "detail": campaign.detail,
                        }
                    )
                    continue

                campaign.status = "running"
                res = self._client.get_campaign_results(campaign.campaign_id)
                if res.get("status") == "ok":
                    any_ok = True
                    campaign.status = "completed"
                    campaign.stats = res.get("stats", {})
                    results.append(
                        {
                            "campaign_id": campaign.campaign_id,
                            "name": campaign.name,
                            "status": "completed",
                            "stats": campaign.stats,
                        }
                    )
                else:
                    any_fail = True
                    campaign.status = "error"
                    results.append(
                        {
                            "campaign_id": campaign.campaign_id,
                            "name": campaign.name,
                            "status": "error",
                            "detail": res.get("detail", "Result collection failed"),
                        }
                    )
            except Exception as exc:  # noqa: BLE001
                any_fail = True
                campaign.status = "error"
                campaign.detail = str(exc)
                results.append(
                    {
                        "campaign_id": campaign.campaign_id,
                        "name": campaign.name,
                        "status": "error",
                        "detail": str(exc),
                    }
                )

        if any_ok and any_fail:
            overall = "partial"
        elif any_ok:
            overall = "ok"
        else:
            overall = "error"

        return {"status": overall, "results": results}
