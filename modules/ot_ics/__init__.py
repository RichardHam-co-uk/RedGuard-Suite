"""
OT/ICS Scanning Module
Modbus, DNP3, and Siemens S7 protocol checks.
"""
import logging
from typing import Optional, Dict, Any
from .modbus_scanner import ModbusScanner
from .dnp3_scanner import DNP3Scanner
from .s7_scanner import S7Scanner

logger = logging.getLogger(__name__)

class OTICSModule:
    """Scans OT/ICS systems for vulnerabilities and misconfigurations."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.modbus = ModbusScanner(timeout)
        self.dnp3 = DNP3Scanner(timeout)
        self.s7 = S7Scanner(timeout)

    def scan_target(self, host: str, port: Optional[int] = None) -> Dict[str, Any]:
        """Run all OT protocol scans against a target."""
        results = {
            "host": host,
            "modbus": self.modbus.scan(host),
            "dnp3": self.dnp3.scan(host),
            "s7": self.s7.scan(host),
        }
        return results

    def scan_modbus(self, host: str, port: int = 502) -> dict:
        return self.modbus.scan(host, port)

    def scan_dnp3(self, host: str, port: int = 20000) -> dict:
        return self.dnp3.scan(host, port)

    def scan_s7(self, host: str, port: int = 102) -> dict:
        return self.s7.scan(host, port)
