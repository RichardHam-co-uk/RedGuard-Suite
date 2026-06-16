"""Tests for the C2/adversary emulation module."""

from __future__ import annotations

import pytest

from modules.c2 import C2Module
from modules.c2.mythic_client import MythicClient, MythicConfig
from modules.c2.sliver_client import SessionInfo, SliverClient, SliverConfig

# The orchestrator adapter may not be importable on all branches
# (e.g. when dependent modules haven't been merged yet).
try:
    from redguard.modules.c2 import run as c2_run  # noqa: E402
except ImportError:
    c2_run = None  # type: ignore[misc, assignment]

# ---------------------------------------------------------------------------
# SliverClient
# ---------------------------------------------------------------------------


class TestSliverConfig:
    def test_defaults(self) -> None:
        cfg = SliverConfig()
        assert cfg.host == "localhost"
        assert cfg.port == 31337

    def test_custom(self) -> None:
        cfg = SliverConfig(host="10.0.0.1", port=443, operator_name="tester")
        assert cfg.host == "10.0.0.1"
        assert cfg.port == 443
        assert cfg.operator_name == "tester"


class TestSliverClientConnect:
    def test_connect_success(self) -> None:
        cfg = SliverConfig(host="10.0.0.1", port=31337)
        client = SliverClient(config=cfg)
        assert client.connect() is True
        assert client.is_connected is True

    def test_connect_missing_host(self) -> None:
        cfg = SliverConfig(host="", port=31337)
        client = SliverClient(config=cfg)
        assert client.connect() is False
        assert client.is_connected is False

    def test_connect_missing_port(self) -> None:
        cfg = SliverConfig(host="10.0.0.1", port=0)
        client = SliverClient(config=cfg)
        assert client.connect() is False

    def test_disconnect(self) -> None:
        cfg = SliverConfig(host="10.0.0.1", port=31337)
        client = SliverClient(config=cfg)
        client.connect()
        client.register_session(
            SessionInfo(
                session_id="sess-1",
                remote_address="10.0.0.2:4444",
                username="root",
                os="linux",
                arch="amd64",
            )
        )
        client.disconnect()
        assert client.is_connected is False
        assert client.session_count == 0


class TestSliverClientSessions:
    def setup_method(self) -> None:
        self.cfg = SliverConfig(host="10.0.0.1", port=31337)
        self.client = SliverClient(config=self.cfg)
        self.client.connect()

    def test_list_sessions_empty(self) -> None:
        assert self.client.list_sessions() == []

    def test_register_and_get_session(self) -> None:
        info = SessionInfo(
            session_id="sess-1",
            remote_address="10.0.0.2:4444",
            username="admin",
            os="windows",
            arch="amd64",
        )
        self.client.register_session(info)
        assert self.client.session_count == 1
        fetched = self.client.get_session("sess-1")
        assert fetched is not None
        assert fetched.username == "admin"
        assert fetched.os == "windows"

    def test_get_nonexistent_session(self) -> None:
        assert self.client.get_session("no-such") is None

    def test_remove_session(self) -> None:
        info = SessionInfo(
            session_id="sess-1",
            remote_address="10.0.0.2:4444",
            username="root",
            os="linux",
            arch="amd64",
        )
        self.client.register_session(info)
        assert self.client.remove_session("sess-1") is True
        assert self.client.session_count == 0

    def test_remove_nonexistent_session(self) -> None:
        assert self.client.remove_session("nope") is False

    def test_list_sessions_not_connected(self) -> None:
        client2 = SliverClient(self.cfg)
        assert client2.list_sessions() == []


class TestSliverClientImplant:
    def setup_method(self) -> None:
        self.cfg = SliverConfig(host="10.0.0.1", port=31337)
        self.client = SliverClient(config=self.cfg)
        self.client.connect()

    def test_generate_implant_ok(self) -> None:
        result = self.client.generate_implant("test-implant", os="linux", arch="amd64")
        assert result["status"] == "ok"
        assert result["implant_name"] == "test-implant"

    def test_generate_implant_not_connected(self) -> None:
        client2 = SliverClient(self.cfg)
        result = client2.generate_implant("x")
        assert result["status"] == "error"
        assert "Not connected" in result["detail"]

    def test_generate_implant_missing_name(self) -> None:
        result = self.client.generate_implant("")
        assert result["status"] == "error"
        assert "name is required" in result["detail"]

    def test_generate_implant_invalid_os(self) -> None:
        result = self.client.generate_implant("bad", os="freebsd")
        assert result["status"] == "error"
        assert "Invalid OS" in result["detail"]

    def test_generate_implant_invalid_arch(self) -> None:
        result = self.client.generate_implant("bad", arch="mips")
        assert result["status"] == "error"
        assert "Invalid arch" in result["detail"]


class TestSliverClientTask:
    def setup_method(self) -> None:
        self.cfg = SliverConfig(host="10.0.0.1", port=31337)
        self.client = SliverClient(config=self.cfg)
        self.client.connect()
        self.client.register_session(
            SessionInfo(
                session_id="sess-1",
                remote_address="10.0.0.2:4444",
                username="root",
                os="linux",
                arch="amd64",
            )
        )

    def test_execute_task_ok(self) -> None:
        result = self.client.execute_task("sess-1", "whoami")
        assert result["status"] == "ok"
        assert result["command"] == "whoami"
        assert result["exit_code"] == 0

    def test_execute_task_not_connected(self) -> None:
        client2 = SliverClient(self.cfg)
        result = client2.execute_task("sess-1", "whoami")
        assert result["status"] == "error"

    def test_execute_task_session_not_found(self) -> None:
        result = self.client.execute_task("ghost", "whoami")
        assert result["status"] == "error"
        assert "not found" in result["detail"]

    def test_execute_task_dead_session(self) -> None:
        self.client.register_session(
            SessionInfo(
                session_id="dead-1",
                remote_address="10.0.0.3:4444",
                username="root",
                os="linux",
                arch="amd64",
                is_dead=True,
            )
        )
        result = self.client.execute_task("dead-1", "whoami")
        assert result["status"] == "error"
        assert "dead" in result["detail"]


# ---------------------------------------------------------------------------
# MythicClient
# ---------------------------------------------------------------------------


class TestMythicConfig:
    def test_defaults(self) -> None:
        cfg = MythicConfig()
        assert cfg.server_url == "https://localhost"
        assert cfg.api_port == 17443
        assert cfg.verify_ssl is True


class TestMythicClientAuth:
    def test_authenticate_with_token(self) -> None:
        cfg = MythicConfig(server_url="https://mythic.local", api_token="abc123")
        client = MythicClient(config=cfg)
        assert client.authenticate() is True
        assert client.is_authenticated is True

    def test_authenticate_with_userpass(self) -> None:
        cfg = MythicConfig(server_url="https://mythic.local", username="admin", password="secret")
        client = MythicClient(config=cfg)
        assert client.authenticate() is True

    def test_authenticate_no_url(self) -> None:
        cfg = MythicConfig(server_url="")
        client = MythicClient(config=cfg)
        assert client.authenticate() is False

    def test_authenticate_no_creds(self) -> None:
        cfg = MythicConfig(server_url="https://mythic.local")
        client = MythicClient(config=cfg)
        assert client.authenticate() is False

    def test_disconnect(self) -> None:
        cfg = MythicConfig(server_url="https://x.local", api_token="tok")
        client = MythicClient(config=cfg)
        client.authenticate()
        client.disconnect()
        assert client.is_authenticated is False
        assert client.payload_count == 0


class TestMythicClientPayload:
    def setup_method(self) -> None:
        cfg = MythicConfig(server_url="https://mythic.local", api_token="tok")
        self.client = MythicClient(config=cfg)
        self.client.authenticate()

    def test_create_payload_ok(self) -> None:
        result = self.client.create_payload("test-payload", "http", os="linux", tag="test")
        assert result["status"] == "ok"
        assert result["name"] == "test-payload"

    def test_create_payload_not_authenticated(self) -> None:
        client2 = MythicClient()
        result = client2.create_payload("x", "http")
        assert result["status"] == "error"

    def test_create_payload_missing_name(self) -> None:
        result = self.client.create_payload("", "http")
        assert result["status"] == "error"

    def test_create_payload_missing_profile(self) -> None:
        result = self.client.create_payload("x", "")
        assert result["status"] == "error"

    def test_list_payloads(self) -> None:
        self.client.create_payload("p1", "http", os="linux")
        self.client.create_payload("p2", "websocket", os="windows")
        assert self.client.payload_count == 2
        assert len(self.client.list_payloads()) == 2

    def test_get_payload(self) -> None:
        self.client.create_payload("p1", "http", os="linux")
        payload = self.client.get_payload("payload-p1")
        assert payload is not None
        assert payload.name == "p1"


class TestMythicClientTask:
    def setup_method(self) -> None:
        cfg = MythicConfig(server_url="https://mythic.local", api_token="tok")
        self.client = MythicClient(config=cfg)
        self.client.authenticate()

    def test_create_task_ok(self) -> None:
        result = self.client.create_task("agent-1", "shell", "whoami")
        assert result["status"] == "ok"
        assert result["command"] == "shell"

    def test_create_task_not_authenticated(self) -> None:
        client2 = MythicClient()
        result = client2.create_task("a", "shell")
        assert result["status"] == "error"

    def test_create_task_missing_agent(self) -> None:
        result = self.client.create_task("", "shell")
        assert result["status"] == "error"

    def test_create_task_missing_command(self) -> None:
        result = self.client.create_task("agent-1", "")
        assert result["status"] == "error"

    def test_list_tasks(self) -> None:
        self.client.create_task("agent-1", "shell", "whoami")
        self.client.create_task("agent-1", "download", "/tmp/file")
        self.client.create_task("agent-2", "shell", "id")
        tasks = self.client.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_filtered(self) -> None:
        self.client.create_task("agent-1", "shell")
        self.client.create_task("agent-2", "shell")
        tasks = self.client.list_tasks(agent_id="agent-1")
        assert len(tasks) == 1

    def test_get_task_output(self) -> None:
        self.client.create_task("agent-1", "shell", "whoami")
        task = self.client.list_tasks()[0]
        result = self.client.get_task_output(task.task_id)
        assert result["status"] == "ok"

    def test_get_task_output_not_found(self) -> None:
        result = self.client.get_task_output("nope")
        assert result["status"] == "error"


class TestMythicClientEvents:
    def setup_method(self) -> None:
        cfg = MythicConfig(server_url="https://mythic.local", api_token="tok")
        self.client = MythicClient(config=cfg)
        self.client.authenticate()

    def test_get_event_log(self) -> None:
        events = self.client.get_event_log(count=5)
        assert len(events) > 0
        assert events[0]["level"] == "info"

    def test_get_event_log_not_authenticated(self) -> None:
        client2 = MythicClient()
        assert client2.get_event_log() == []


# ---------------------------------------------------------------------------
# C2Module Orchestrator
# ---------------------------------------------------------------------------


class TestC2ModuleOrchestrator:
    def test_add_backends(self) -> None:
        mod = C2Module()
        mod.add_sliver_backend("sliver-main")
        mod.add_mythic_backend("mythic-main")
        assert len(mod.backend_names) == 2
        assert "sliver-main" in mod.backend_names
        assert "mythic-main" in mod.backend_names

    def test_set_active(self) -> None:
        mod = C2Module()
        mod.add_sliver_backend("slv")
        mod.set_active("slv")
        assert mod.active_backend == "slv"
        active = mod.get_active()
        assert isinstance(active, SliverClient)

    def test_set_active_unknown(self) -> None:
        mod = C2Module()
        with pytest.raises(ValueError, match="Unknown backend"):
            mod.set_active("ghost")

    def test_get_active_none(self) -> None:
        mod = C2Module()
        assert mod.get_active() is None

    def test_status(self) -> None:
        mod = C2Module()
        mod.add_sliver_backend("slv")
        mod.set_active("slv")
        status = mod.status()
        assert status["active"] == "slv"
        assert "slv" in status["backends"]
        assert status["backends"]["slv"]["type"] == "sliver"

    def test_run_no_backends(self) -> None:
        mod = C2Module()
        result = mod.run()
        assert result["status"] == "error"
        assert "No C2 backends" in result["detail"]

    def test_run_with_backends(self) -> None:
        mod = C2Module()
        slv = mod.add_sliver_backend("slv")
        slv.connect()
        myth = mod.add_mythic_backend(
            "myth",
            server_url="https://mythic.local",
            api_token="tok",
        )
        myth.authenticate()
        result = mod.run()
        assert result["status"] == "ok"
        assert len(result["results"]) == 2

    def test_run_partial_when_backend_inactive(self) -> None:
        mod = C2Module()
        # Add a sliver backend but do NOT connect — connect() will
        # auto-succeed inside run() because defaults are valid, so we
        # also add a mythic backend that *cannot* authenticate to force
        # the partial status.
        mod.add_sliver_backend("slv")  # not pre-connected, but connect() succeeds
        mod.add_mythic_backend("myth")  # no creds → authenticate() fails
        result = mod.run()
        assert result["status"] == "partial"


# ---------------------------------------------------------------------------
# redguard.modules.c2.run adapter
# ---------------------------------------------------------------------------


@pytest.mark.skipif(c2_run is None, reason="redguard.modules.c2 not importable on this branch")
class TestC2RunAdapter:
    def test_run_skipped_when_unconfigured(self) -> None:
        result = c2_run({"modules": {}})
        assert result["status"] == "skipped"

    def test_run_with_sliver_and_mythic(self) -> None:
        config = {
            "modules": {
                "c2": {
                    "sliver": {"host": "10.0.0.1", "port": 31337},
                    "mythic": {
                        "server_url": "https://mythic.local",
                        "api_token": "tok",
                    },
                }
            }
        }
        result = c2_run(config)
        assert result["status"] == "ok"
        assert len(result["results"]) == 2
