from redguard.modules.llm_garak import run


def test_llm_garak_returns_status_and_detail(sample_config: dict):
    result = run(sample_config)
    assert result["status"] == "skipped"
    assert "placeholder" in result["detail"]


def test_llm_garak_returns_dict_for_empty_config():
    result = run({})
    assert isinstance(result, dict)
    assert {"status", "detail"} <= result.keys()
