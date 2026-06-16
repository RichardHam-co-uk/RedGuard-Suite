"""
Tests for DefectDojo integration module.
"""
import pytest
from modules.defectdojo import DefectDojoClient, DefectDojoModule

class TestDefectDojoClient:
    def test_init(self):
        client = DefectDojoClient()
        assert "localhost" in client.base_url

    def test_init_with_key(self):
        client = DefectDojoClient(base_url="https://dojo.corp", api_key="key-123")
        assert "ApiKey" in client._headers.get("Authorization", "")

    def test_authenticate(self):
        client = DefectDojoClient(api_key="key")
        assert client.authenticate() is True

    def test_create_engagement_not_auth(self):
        client = DefectDojoClient()
        with pytest.raises(RuntimeError):
            client.create_engagement(1, "test")

    def test_create_engagement(self):
        client = DefectDojoClient(api_key="key")
        client.authenticate()
        result = client.create_engagement(1, "Test Engagement")
        assert result["name"] == "Test Engagement"

    def test_create_test(self):
        client = DefectDojoClient(api_key="key")
        client.authenticate()
        result = client.create_test(1)
        assert result["test_type"] == "RedGuard Scan"

    def test_create_finding(self):
        client = DefectDojoClient(api_key="key")
        client.authenticate()
        result = client.create_finding(1, "Open SMB port", "Port 445 exposed", "Medium", "Restrict firewall")
        assert result["severity"] == "Medium"

    def test_push_findings(self):
        client = DefectDojoClient(api_key="key")
        client.authenticate()
        findings = [
            {"title": "Finding 1", "severity": "High"},
            {"title": "Finding 2", "severity": "Medium"},
        ]
        result = client.push_findings(findings, 1, "Test Scan")
        assert result["findings_created"] == 2

class TestDefectDojoModule:
    def test_init(self):
        mod = DefectDojoModule()
        assert mod.connected is False

    def test_init_with_config(self):
        mod = DefectDojoModule({"base_url": "https://dojo.local", "api_key": "key-abc"})
        assert "dojo.local" in mod.client.base_url

    def test_connect(self):
        mod = DefectDojoModule({"api_key": "key"})
        assert mod.connect() is True

    def test_submit_not_connected(self):
        mod = DefectDojoModule()
        with pytest.raises(RuntimeError):
            mod.submit_scan_results({"target": "10.0.0.1"}, 1)

    def test_submit_scan_results(self):
        mod = DefectDojoModule({"api_key": "key"})
        mod.connect()
        results = {
            "target": "10.0.0.1",
            "modbus": {"host": "10.0.0.1", "reachable": True},
        }
        result = mod.submit_scan_results(results, 1)
        assert result["findings_created"] >= 1
