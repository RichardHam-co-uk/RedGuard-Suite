"""
Tests for OT/ICS scanning module.
"""
import pytest
from modules.ot_ics import OTICSModule
from modules.ot_ics.modbus_scanner import ModbusScanner
from modules.ot_ics.dnp3_scanner import DNP3Scanner
from modules.ot_ics.s7_scanner import S7Scanner

class TestModbusScanner:
    def test_init(self):
        s = ModbusScanner(timeout=3)
        assert s.timeout == 3

    def test_scan(self):
        s = ModbusScanner()
        result = s.scan("192.168.1.100")
        assert result["host"] == "192.168.1.100"
        assert result["port"] == 502
        assert result["reachable"] is True
        assert 1 in result["supported_functions"]

    def test_scan_custom_port(self):
        s = ModbusScanner()
        result = s.scan("10.0.0.1", port=1502)
        assert result["port"] == 1502

    def test_function_codes_defined(self):
        assert 1 in ModbusScanner.FUNCTION_CODES
        assert 16 in ModbusScanner.FUNCTION_CODES

class TestDNP3Scanner:
    def test_init(self):
        s = DNP3Scanner(timeout=10)
        assert s.timeout == 10

    def test_scan(self):
        s = DNP3Scanner()
        result = s.scan("192.168.1.200")
        assert result["host"] == "192.168.1.200"
        assert result["reachable"] is True
        assert "Read" in result["supported_functions"]

    def test_scan_custom_port(self):
        s = DNP3Scanner()
        result = s.scan("10.0.0.2", port=20001)
        assert result["port"] == 20001

class TestS7Scanner:
    def test_init(self):
        s = S7Scanner(timeout=2)
        assert s.timeout == 2

    def test_scan(self):
        s = S7Scanner()
        result = s.scan("192.168.1.50")
        assert result["host"] == "192.168.1.50"
        assert result["port"] == 102
        assert result["reachable"] is True

    def test_scan_custom_port(self):
        s = S7Scanner()
        result = s.scan("10.0.0.3", port=1102)
        assert result["port"] == 1102

class TestOTICSModule:
    def test_init(self):
        mod = OTICSModule(timeout=3)
        assert mod.timeout == 3

    def test_scan_target(self):
        mod = OTICSModule()
        result = mod.scan_target("192.168.1.100")
        assert result["host"] == "192.168.1.100"
        assert "modbus" in result
        assert "dnp3" in result
        assert "s7" in result

    def test_scan_modbus(self):
        mod = OTICSModule()
        result = mod.scan_modbus("10.0.0.1")
        assert "host" in result

    def test_scan_dnp3(self):
        mod = OTICSModule()
        result = mod.scan_dnp3("10.0.0.2")
        assert "host" in result

    def test_scan_s7(self):
        mod = OTICSModule()
        result = mod.scan_s7("10.0.0.3")
        assert "host" in result
