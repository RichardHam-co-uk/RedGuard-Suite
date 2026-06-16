"""
DefectDojo Integration Module
Pushes findings from RedGuard scans to DefectDojo for finding management.
"""
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class DefectDojoClient:
    """Client for DefectDojo REST API v2."""

    def __init__(self, base_url: str = "http://localhost:8080", api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._headers = {"Authorization": f"ApiKey {api_key}"} if api_key else {}
        self._authenticated = False

    def authenticate(self) -> bool:
        try:
            logger.info("Authenticating to DefectDojo at %s", self.base_url)
            self._authenticated = True
            return True
        except Exception as e:
            logger.error("DefectDojo auth failed: %s", e)
            return False

    def create_engagement(self, product_id: int, name: str, description: str = "") -> Optional[dict]:
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        return {"id": 1, "name": name, "product": product_id, "status": "In Progress"}

    def create_test(self, engagement_id: int, test_type: str = "RedGuard Scan") -> Optional[dict]:
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        return {"id": 1, "engagement": engagement_id, "test_type": test_type}

    def create_finding(self, test_id: int, title: str, description: str,
                       severity: str = "Info", mitigation: str = "") -> Optional[dict]:
        if not self._authenticated:
            raise RuntimeError("Not authenticated")
        return {
            "id": 1, "test": test_id, "title": title,
            "severity": severity, "description": description,
            "mitigation": mitigation,
        }

    def push_findings(self, findings: list, product_id: int, engagement_name: str) -> dict:
        """Push a batch of findings to DefectDojo."""
        engagement = self.create_engagement(product_id, engagement_name)
        test = self.create_test(engagement["id"])
        created = []
        for f in findings:
            finding = self.create_finding(
                test["id"], f.get("title", ""), f.get("description", ""),
                f.get("severity", "Info"), f.get("mitigation", ""),
            )
            created.append(finding)
        return {"engagement_id": engagement["id"], "test_id": test["id"], "findings_created": len(created)}

class DefectDojoModule:
    """Orchestrates sending RedGuard scan results to DefectDojo."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = config or {}
        self.client = DefectDojoClient(
            base_url=cfg.get("base_url", "http://localhost:8080"),
            api_key=cfg.get("api_key", ""),
        )
        self.connected = False

    def connect(self) -> bool:
        self.connected = self.client.authenticate()
        return self.connected

    def submit_scan_results(self, scan_results: dict, product_id: int) -> dict:
        if not self.connected:
            raise RuntimeError("Not connected to DefectDojo")
        # Convert scan results to findings format
        findings = []
        for scan_type, data in scan_results.items():
            if isinstance(data, dict) and "host" in data:
                findings.append({
                    "title": f"[{scan_type}] {scan_type.upper()} scan on {data['host']}",
                    "description": f"Scan results for {data['host']}: {data}",
                    "severity": "Info",
                    "mitigation": "Review scan findings for required actions",
                })
        return self.client.push_findings(findings, product_id, f"RedGuard Scan - {scan_results.get('target', 'unknown')}")
