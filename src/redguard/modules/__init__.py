"""RedGuard attack-phase modules.

Each module exposes a ``run(config) -> dict`` entrypoint and is dispatched
by :mod:`redguard.orchestrator` based on the active configuration.
"""
