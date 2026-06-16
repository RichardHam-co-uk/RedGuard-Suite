"""C2 / Adversary Emulation module.

Orchestrates multiple C2 backends (Sliver, Mythic) through a unified
interface.  Callers add backends, set an active backend, and invoke
:meth:`C2Module.run` to execute the emulation workflow across all
configured backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from modules.c2.mythic_client import MythicClient, MythicConfig
from modules.c2.sliver_client import SliverClient, SliverConfig

__all__ = [
    "C2Module",
    "MythicClient",
    "MythicConfig",
    "SliverClient",
    "SliverConfig",
]


@dataclass
class C2Module:
    """High-level orchestrator that manages one or more C2 backends.

    Backends are registered by name and can be either
    :class:`SliverClient` or :class:`MythicClient` instances.
    The *active* backend is the one returned by :meth:`get_active`.
    """

    _backends: dict[str, SliverClient | MythicClient] = field(
        default_factory=dict, init=False, repr=False
    )
    _active_backend: str | None = field(default=None, init=False, repr=False)

    # -- backend registration -------------------------------------------

    def add_sliver_backend(
        self,
        name: str,
        host: str = "localhost",
        port: int = 31337,
        operator_name: str = "operator",
        ca_cert: str | None = None,
        client_cert: str | None = None,
        client_key: str | None = None,
    ) -> SliverClient:
        """Register a Sliver C2 backend.

        Args:
            name: Unique backend identifier.
            host: Sliver gRPC server host.
            port: Sliver gRPC server port.
            operator_name: Operator name for mTLS auth.
            ca_cert: Path to CA certificate.
            client_cert: Path to client certificate.
            client_key: Path to client key.

        Returns:
            The configured (but not yet connected) :class:`SliverClient`.
        """
        cfg = SliverConfig(
            host=host,
            port=port,
            operator_name=operator_name,
            ca_cert=ca_cert,
            client_cert=client_cert,
            client_key=client_key,
        )
        client = SliverClient(config=cfg)
        self._backends[name] = client
        return client

    def add_mythic_backend(
        self,
        name: str,
        server_url: str = "https://localhost",
        api_port: int = 17443,
        api_token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        verify_ssl: bool = True,
    ) -> MythicClient:
        """Register a Mythic C2 backend.

        Args:
            name: Unique backend identifier.
            server_url: Mythic server base URL.
            api_port: Mythic API port.
            api_token: Pre-shared API token (preferred).
            username: Username for password auth.
            password: Password for password auth.
            verify_ssl: Whether to verify TLS certificates.

        Returns:
            The configured (but not yet authenticated) :class:`MythicClient`.
        """
        cfg = MythicConfig(
            server_url=server_url,
            api_port=api_port,
            api_token=api_token,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )
        client = MythicClient(config=cfg)
        self._backends[name] = client
        return client

    # -- active backend management --------------------------------------

    @property
    def backend_names(self) -> list[str]:
        """Return the names of all registered backends."""
        return list(self._backends.keys())

    @property
    def active_backend(self) -> str | None:
        """Return the name of the active backend, or ``None``."""
        return self._active_backend

    def set_active(self, name: str) -> None:
        """Set the active backend by name.

        Raises:
            ValueError: If *name* is not a registered backend.
        """
        if name not in self._backends:
            raise ValueError(f"Unknown backend: {name!r}")
        self._active_backend = name

    def get_active(self) -> SliverClient | MythicClient | None:
        """Return the active backend instance, or ``None``."""
        if self._active_backend is None:
            return None
        return self._backends.get(self._active_backend)

    # -- status ---------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return a summary of all registered backends."""
        backends: dict[str, Any] = {}
        for name, be in self._backends.items():
            info: dict[str, Any] = {
                "type": "sliver" if isinstance(be, SliverClient) else "mythic",
            }
            if isinstance(be, SliverClient):
                info["connected"] = be.is_connected
                info["sessions"] = be.session_count
            elif isinstance(be, MythicClient):
                info["authenticated"] = be.is_authenticated
                info["payloads"] = be.payload_count
            backends[name] = info
        return {"active": self._active_backend, "backends": backends}

    # -- run ------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """Execute the C2 workflow across all registered backends.

        For each backend the method attempts to connect/authenticate and
        collect basic health information.  Backends that fail to come
        online are reported with an ``"error"`` status.

        Returns:
            A dict with ``"status"`` (``"ok"``, ``"partial"``, or
            ``"error"``) and per-backend ``"results"``.
        """
        if not self._backends:
            return {"status": "error", "detail": "No C2 backends configured"}

        results: list[dict[str, Any]] = []
        any_ok = False
        any_fail = False

        for name, be in self._backends.items():
            try:
                if isinstance(be, SliverClient):
                    ok = be.is_connected or be.connect()
                    if ok:
                        any_ok = True
                        results.append(
                            {
                                "backend": name,
                                "type": "sliver",
                                "status": "ok",
                                "sessions": be.session_count,
                            }
                        )
                    else:
                        any_fail = True
                        results.append(
                            {
                                "backend": name,
                                "type": "sliver",
                                "status": "error",
                                "detail": "Connection failed",
                            }
                        )
                elif isinstance(be, MythicClient):
                    ok = be.is_authenticated or be.authenticate()
                    if ok:
                        any_ok = True
                        results.append(
                            {
                                "backend": name,
                                "type": "mythic",
                                "status": "ok",
                                "payloads": be.payload_count,
                            }
                        )
                    else:
                        any_fail = True
                        results.append(
                            {
                                "backend": name,
                                "type": "mythic",
                                "status": "error",
                                "detail": "Authentication failed",
                            }
                        )
            except Exception as exc:  # noqa: BLE001
                any_fail = True
                results.append(
                    {
                        "backend": name,
                        "type": "unknown",
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
