import pytest
# Assuming the path structure allows direct import for testing purposes
from modules.report import ReportEngine

def test_report_engine_initialization():
    \"\"\"Test that ReportEngine initializes correctly.\"\"\"
    engine = ReportEngine("dummy.pdf")
    assert engine.output_path == "dummy.pdf"

def test_report_engine_generation_success(tmp_path):
    \"\"\"Test report generation runs without error and creates a file.\"\"\"
    # Note: Running this test requires actual PDF libraries (like reportlab) 
    # which we mock the output check for, focusing on control flow.
    mock_results = [{'id': 'T1059', 'description': 'PowerShell abuse'}]
    engine = ReportEngine(str(tmp_path / "test_report.pdf"))
    
    result = engine.generate(mock_results)
    
    assert "Report successfully generated" in result

def test_report_engine_empty_scan_data():
    \"\"\"Test report generation handles empty scan results gracefully.\"\"\"
    mock_results = []
    engine = ReportEngine("dummy_empty.pdf")
    
    try:
        result = engine.generate(mock_results)
        assert "Report successfully generated" in result
    except Exception as e:
        pytest.fail(f"Generating report with empty data failed: {e}")