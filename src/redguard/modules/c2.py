"""C2 adapter registered under the ``redguard.modules`` namespace.

This module provides the :func:`run` entry-point expected by the
RedGuard orchestrator, delegating to the full
:class:`~modules.c2.C2Module` implementation under the hood.
"""

from __future__ import annotations

from typing import Any

from modules.c2 import C2Module


def run(config: dict[str, Any]) -> dict[str, Any]:
    """Execute the C2 module based on orchestrator configuration.

    Expected config layout::

        {
            "modules": {
                "c2": {
                    "sliver": {"host": "...", "port": ...},
                    "mythic": {"server_url": "...", "api_token": "..."},
                }
            }
        }

    When the ``"c2"`` key is absent the module is considered
    unconfigured and returns a ``"skipped"`` status so the orchestrator
    can continue gracefully.

    Args:
        config: Full orchestrator configuration dictionary.

    Returns:
        A result dict with at least a ``"status"`` key
        (``"ok"``, ``"partial"``, ``"error"``, or ``"skipped"``).
    """
    c2_cfg = config.get("modules", {}).get("c2")
    if not c2_cfg:
        return {"status": "skipped", "detail": "C2 module not configured"}

    mod = C2Module()

    sliver_cfg = c2_cfg.get("sliver")
    if sliver_cfg:
        mod.add_sliver_backend(
            "sliver",
            host=sliver_cfg.get("host", "localhost"),
            port=sliver_cfg.get("port", 31337),
            operator_name=sliver_cfg.get("operator_name", "operator"),
            ca_cert=sliver_cfg.get("ca_cert"),
            client_cert=sliver_cfg.get("client_cert"),
            client_key=sliver_cfg.get("client_key"),
        )

    mythic_cfg = c2_cfg.get("mythic")
    if mythic_cfg:
        mod.add_mythic_backend(
            "mythic",
            server_url=mythic_cfg.get("server_url", "https://localhost"),
            api_port=mythic_cfg.get("api_port", 17443),
            api_token=mythic_cfg.get("api_token"),
            username=mythic_cfg.get("username"),
            password=mythic_cfg.get("password"),
            verify_ssl=mythic_cfg.get("verify_ssl", True),
        )

    return mod.run()
