"""Mythic C2 backend client.

Provides a lightweight, dependency-free client that mirrors the essential
operations of the Mythic C2 framework's REST API:

* Token-based and username/password authentication
* Callback (agent) management
* Task creation and output retrieval
* Payload generation
* Event log access

The implementation is intentionally self-contained so that tests can run
without the actual Mythic server or ``mythic_rest`` Python package
installed.  In production the private methods would dispatch real HTTP
requests.
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
class MythicConfig:
    """Connection parameters for a Mythic server.

    Args:
        server_url: Base URL of the Mythic instance.
        api_port: Port the Mythic API listens on.
        api_token: Pre-shared bearer token for API auth.
        Username and password for login-based auth (alternative to token).
        verify_ssl: Whether to verify TLS certificates.
    """

    server_url: str = "https://localhost"
    api_port: int = 17443
    api_token: str | None = None
    username: str | None = None
    password: str | None = None
    verify_ssl: bool = True


# ---------------------------------------------------------------------------
# Payload info
# ---------------------------------------------------------------------------


@dataclass
class PayloadInfo:
    """Metadata about a generated Mythic payload."""

    payload_id: str
    name: str
    c2_profile: str
    os: str = "unknown"
    tag: str = ""
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Task info
# ---------------------------------------------------------------------------


@dataclass
class TaskInfo:
    """Metadata about a Mythic task."""

    task_id: str
    agent_id: str
    command: str = ""
    arguments: str = ""
    status: str = "created"
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MythicClient:
    """Lightweight Mythic C2 REST client.

    The client manages in-memory stores for payloads and tasks,
    validating inputs before dispatching to the (mocked) HTTP layer.

    Args:
        config: Optional :class:`MythicConfig`.  Defaults to
            ``MythicConfig()`` when *None*.
    """

    VALID_C2_PROFILES = {"http", "websocket", "tcp", "dynamichttp", "dns"}

    def __init__(self, config: MythicConfig | None = None) -> None:
        self.config = config or MythicConfig()
        self._authenticated: bool = False
        self._token: str | None = None
        self._payloads: dict[str, PayloadInfo] = {}
        self._tasks: dict[str, TaskInfo] = {}

    # -- properties -----------------------------------------------------

    @property
    def is_authenticated(self) -> bool:
        """Whether the client holds a valid Mythic session token."""
        return self._authenticated

    @property
    def payload_count(self) -> int:
        """Number of payloads tracked by this client."""
        return len(self._payloads)

    # -- authentication -------------------------------------------------

    def authenticate(self) -> bool:
        """Authenticate with the Mythic server.

        Supports token-based auth (via
        :attr:`MythicConfig.api_token`) or username/password login.

        Returns:
            ``True`` on success, ``False`` otherwise.
        """
        if not self.config.server_url:
            return False

        if self.config.api_token:
            self._token = self.config.api_token
            self._authenticated = True
            return True

        if self.config.username and self.config.password:
            self._token = str(uuid.uuid4())
            self._authenticated = True
            return True

        return False

    def disconnect(self) -> None:
        """Clear the session token and all cached state."""
        self._authenticated = False
        self._token = None
        self._payloads.clear()
        self._tasks.clear()

    # -- payload management ---------------------------------------------

    def create_payload(
        self,
        name: str,
        c2_profile: str,
        os: str = "linux",
        tag: str = "",
    ) -> dict[str, Any]:
        """Generate a new C2 payload (mocked).

        Args:
            name: Human-readable payload name.
            c2_profile: C2 transport profile name.
            os: Target operating system.
            tag: Free-form tag for organisation.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._authenticated:
            return {
                "status": "error",
                "detail": "Not authenticated with Mythic server",
            }
        if not name:
            return {"status": "error", "detail": "Payload name is required"}
        if not c2_profile:
            return {"status": "error", "detail": "C2 profile is required"}

        payload_id = f"payload-{name}"
        info = PayloadInfo(
            payload_id=payload_id,
            name=name,
            c2_profile=c2_profile,
            os=os,
            tag=tag,
        )
        self._payloads[payload_id] = info
        return {"status": "ok", "payload_id": payload_id, "name": name}

    def list_payloads(self) -> list[PayloadInfo]:
        """Return all tracked payloads."""
        return list(self._payloads.values())

    def get_payload(self, payload_id: str) -> PayloadInfo | None:
        """Look up a payload by ID."""
        return self._payloads.get(payload_id)

    # -- task management ------------------------------------------------

    def create_task(
        self,
        agent_id: str,
        command: str,
        arguments: str = "",
    ) -> dict[str, Any]:
        """Create a task for a Mythic agent (callback) to execute.

        Args:
            agent_id: Target agent/callback ID.
            command: Command name (e.g. ``shell``, ``download``).
            arguments: Optional command arguments.

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._authenticated:
            return {
                "status": "error",
                "detail": "Not authenticated with Mythic server",
            }
        if not agent_id:
            return {"status": "error", "detail": "Agent ID is required"}
        if not command:
            return {"status": "error", "detail": "Command is required"}

        task_id = str(uuid.uuid4())
        task = TaskInfo(
            task_id=task_id,
            agent_id=agent_id,
            command=command,
            arguments=arguments,
        )
        self._tasks[task_id] = task
        return {"status": "ok", "task_id": task_id, "command": command}

    def list_tasks(self, agent_id: str | None = None) -> list[TaskInfo]:
        """List tasks, optionally filtered by agent.

        Args:
            agent_id: If given, only return tasks for this agent.

        Returns:
            A list of :class:`TaskInfo` objects.
        """
        tasks = list(self._tasks.values())
        if agent_id:
            tasks = [t for t in tasks if t.agent_id == agent_id]
        return tasks

    def get_task_output(self, task_id: str) -> dict[str, Any]:
        """Retrieve the output (stdout / stderr) for a completed task.

        Args:
            task_id: The task to query.

        Returns:
            A result dict with ``"status"`` and, on success,
            ``"output"``.
        """
        task = self._tasks.get(task_id)
        if task is None:
            return {"status": "error", "detail": f"Task {task_id!r} not found"}

        return {
            "status": "ok",
            "task_id": task_id,
            "output": f"[mock output for {task.command} {task.arguments}]",
            "exit_code": 0,
        }

    # -- event log ------------------------------------------------------

    def get_event_log(self, count: int = 10) -> list[dict[str, Any]]:
        """Return the most recent Mythic event-log entries (mocked).

        Args:
            count: Maximum number of entries to return.

        Returns:
            A list of event dicts.  Returns an empty list when not
            authenticated.
        """
        if not self._authenticated:
            return []
        return [
            {
                "id": i,
                "level": "info",
                "message": f"Mock event {i}",
                "timestamp": time.time(),
            }
            for i in range(count)
        ]
