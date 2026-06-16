"""
Tests for AD Attack Path module.
"""
import pytest
from modules.ad_attack import ADAttackModule
from modules.ad_attack.bloodhound_client import BloodHoundClient

class TestBloodHoundClient:
    def test_init_defaults(self):
        client = BloodHoundClient()
        assert "localhost" in client.server_url

    def test_init_with_token(self):
        client = BloodHoundClient(server_url="https://bh.local", api_token="tok-abc")
        assert "Bearer" in client._headers.get("Authorization", "")

    def test_health_check(self):
        client = BloodHoundClient()
        assert client.health_check() is True

    def test_run_cypher(self):
        client = BloodHoundClient()
        assert client.run_cypher("MATCH (n) RETURN n") == []

    def test_search_nodes(self):
        client = BloodHoundClient()
        assert client.search_nodes("admin") == []

    def test_get_node_info_none(self):
        client = BloodHoundClient()
        assert client.get_node_info("S-1-5-...") is None

class TestADAttackModule:
    def test_init(self):
        mod = ADAttackModule()
        assert mod.connected is False

    def test_init_custom(self):
        mod = ADAttackModule(server_url="https://bh.internal:8443")
        assert "bh.internal" in mod.client.server_url

    def test_connect(self):
        mod = ADAttackModule()
        assert mod.connect() is True
        assert mod.connected is True

    def test_find_paths_not_connected(self):
        mod = ADAttackModule()
        with pytest.raises(RuntimeError):
            mod.find_shortest_paths_to_da("USER@DOMAIN.LOCAL")

    def test_find_paths_connected(self):
        mod = ADAttackModule()
        mod.connect()
        result = mod.find_shortest_paths_to_da("RHAM@CORP.LOCAL")
        assert result == []

    def test_find_sessions(self):
        mod = ADAttackModule()
        mod.connect()
        assert mod.find_sessions("PC-01.CORP.LOCAL") == []

    def test_find_dcom(self):
        mod = ADAttackModule()
        mod.connect()
        assert mod.find_dcom_connections("SERVER.CORP.LOCAL") == []

    def test_find_kerberoastable(self):
        mod = ADAttackModule()
        mod.connect()
        assert mod.find_kerberoastable() == []

    def test_health(self):
        mod = ADAttackModule()
        h = mod.health()
        assert "connected" in h
        assert h["connected"] is False
