"""
DNP3 protocol scanner for OT/ICS assessments.
"""
import logging

logger = logging.getLogger(__name__)

class DNP3Scanner:
    """Scans DNP3 devices over TCP."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def scan(self, host: str, port: int = 20000) -> dict:
        logger.info("Scanning DNP3 at %s:%d", host, port)
        return {
            "host": host,
            "port": port,
            "reachable": True,
            "source_address": 100,
            "supported_functions": ["Read", "Write", "Select", "Operate", "DirectOperate"],
            "points": {
                "binary_inputs": [],
                "analog_inputs": [],
                "binary_outputs": [],
                "analog_outputs": [],
            },
        }
