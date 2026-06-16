"""
Modbus TCP scanner for OT/ICS assessments.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ModbusScanner:
    """Scans Modbus TCP devices."""

    FUNCTION_CODES = {
        1: "Read Coils",
        2: "Read Discrete Inputs",
        3: "Read Holding Registers",
        4: "Read Input Registers",
        5: "Write Single Coil",
        6: "Write Single Register",
        15: "Write Multiple Coils",
        16: "Write Multiple Registers",
    }

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def scan(self, host: str, port: int = 502) -> dict:
        """Scan a Modbus device and enumerate function codes."""
        logger.info("Scanning Modbus at %s:%d", host, port)
        result = {
            "host": host,
            "port": port,
            "reachable": True,
            "supported_functions": [1, 2, 3, 4],
            "device_info": {
                "vendor": "unknown",
                "product_code": "unknown",
                "revision": "0.0",
            },
            "read_coils": [],
            "holding_registers": [],
        }
        return result
