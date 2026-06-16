"""Sliver C2 backend client.

Provides a lightweight, dependency-free client that mirrors the essential
operations of the Sliver framework's gRPC API:

* mTLS connection management
* Session registration / listing / removal
* Implant generation
* Task execution against sessions

The implementation is intentionally self-contained so that tests can run
without the actual Sliver gRPC stubs installed.  In a production
deployment the private methods would be replaced with real gRPC calls.
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
class SliverConfig:
    """Connection parameters for a Sliver gRPC server.

    Args:
        host: Server hostname or IP.
        port: Server gRPC port (default ``31337``).
        operator_name: Operator identity for mTLS.
        ca_cert: Path to the CA certificate file.
        client_cert: Path to the client certificate file.
        client_key: Path to the client private-key file.
    """

    host: str = "localhost"
    port: int = 31337
    operator_name: str = "operator"
    ca_cert: str | None = None
    client_cert: str | None = None
    client_key: str | None = None


# ---------------------------------------------------------------------------
# Session info
# ---------------------------------------------------------------------------


@dataclass
class SessionInfo:
    """Metadata about an active Sliver session (beacon / session)."""

    session_id: str
    remote_address: str
    username: str = "unknown"
    os: str = "unknown"
    arch: str = "amd64"
    is_dead: bool = False
    last_checkin: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class SliverClient:
    """Lightweight Sliver C2 client.

    The client manages an in-memory session store and validates inputs
    before dispatching to the (mocked) gRPC layer.  This keeps the
    interface identical to what real Sliver integration would look like
    while remaining fully testable without external dependencies.

    Args:
        config: Optional :class:`SliverConfig`.  Defaults to
            ``SliverConfig()`` when *None*.
    """

    # Valid OS / arch combinations for implant generation
    VALID_OS = {"linux", "windows", "darwin", "android", "ios"}
    VALID_ARCH = {"amd64", "arm64", "386", "arm"}

    def __init__(self, config: SliverConfig | None = None) -> None:
        self.config = config or SliverConfig()
        self._connected: bool = False
        self._sessions: dict[str, SessionInfo] = {}

    # -- properties -----------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """Whether the gRPC channel is currently open."""
        return self._connected

    @property
    def session_count(self) -> int:
        """Number of registered sessions."""
        return len(self._sessions)

    # -- connection management ------------------------------------------

    def connect(self) -> bool:
        """Open the gRPC channel to the Sliver server.

        Returns:
            ``True`` if the connection succeeded, ``False`` otherwise.
        """
        if not self.config.host or not self.config.port:
            return False
        self._connected = True
        return True

    def disconnect(self) -> None:
        """Close the gRPC channel and clear all session state."""
        self._connected = False
        self._sessions.clear()

    # -- session management ---------------------------------------------

    def list_sessions(self) -> list[SessionInfo]:
        """Return all registered sessions.

        Returns:
            A list of :class:`SessionInfo` objects.  Always returns an
            empty list when not connected.
        """
        if not self._connected:
            return []
        return list(self._sessions.values())

    def get_session(self, session_id: str) -> SessionInfo | None:
        """Look up a session by ID.

        Args:
            session_id: The unique session identifier.

        Returns:
            The matching :class:`SessionInfo`, or ``None`` if not found.
        """
        return self._sessions.get(session_id)

    def register_session(self, info: SessionInfo) -> None:
        """Register or update a session in the local store.

        Args:
            info: Session metadata to register.
        """
        self._sessions[info.session_id] = info

    def remove_session(self, session_id: str) -> bool:
        """Remove a session from the store.

        Args:
            session_id: The session to remove.

        Returns:
            ``True`` if the session existed and was removed.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    # -- implant generation ---------------------------------------------

    def generate_implant(
        self,
        name: str,
        os: str = "linux",
        arch: str = "amd64",
        format: str = "exe",
    ) -> dict[str, Any]:
        """Generate a new implant binary (mocked).

        Args:
            name: Human-readable implant name.
            os: Target operating system.
            arch: Target architecture.
            format: Output format (``exe``, ``shared``, ``service``).

        Returns:
            A result dict with at least a ``"status"`` key.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to Sliver server"}
        if not name:
            return {"status": "error", "detail": "Implant name is required"}
        if os not in self.VALID_OS:
            return {"status": "error", "detail": f"Invalid OS: {os}"}
        if arch not in self.VALID_ARCH:
            return {"status": "error", "detail": f"Invalid arch: {arch}"}

        return {
            "status": "ok",
            "implant_name": name,
            "os": os,
            "arch": arch,
            "format": format,
            "build_id": str(uuid.uuid4()),
        }

    # -- task execution -------------------------------------------------

    def execute_task(
        self,
        session_id: str,
        command: str,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Execute a command on a remote session (mocked).

        Args:
            session_id: Target session ID.
            command: Shell command to execute.
            timeout: Maximum wait time in seconds.

        Returns:
            A result dict with ``"status"``, ``"command"``, and
            ``"exit_code"`` keys on success.
        """
        if not self._connected:
            return {"status": "error", "detail": "Not connected to Sliver server"}

        session = self._sessions.get(session_id)
        if session is None:
            return {
                "status": "error",
                "detail": f"Session {session_id!r} not found",
            }

        if session.is_dead:
            return {
                "status": "error",
                "detail": f"Session {session_id!r} is dead",
            }

        return {
            "status": "ok",
            "session_id": session_id,
            "command": command,
            "output": f"[mock] {command}",
            "exit_code": 0,
        }
