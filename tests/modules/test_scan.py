from redguard.modules.scan import run


def test_scan_returns_status_and_detail(sample_config: dict):
    result = run(sample_config)
    assert result["status"] == "skipped"
    assert "detail" in result


def test_scan_returns_dict_for_empty_config():
    result = run({})
    assert isinstance(result, dict)
    assert {"status", "detail"} <= result.keys()
