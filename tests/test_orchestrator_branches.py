from redguard.orchestrator import run


def test_run_executes_llm_garak_when_enabled():
    config = {"targets": ["example.com"], "modules": {"llm_garak": True}}
    result = run(config)
    assert "llm_garak" in result
    assert result["llm_garak"]["status"] == "skipped"


def test_run_executes_all_modules_when_enabled():
    config = {
        "targets": ["example.com"],
        "modules": {"recon": True, "scan": True, "llm_garak": True, "report": True},
    }
    result = run(config)
    assert set(result.keys()) == {"recon", "scan", "llm_garak", "report"}


def test_run_report_receives_prior_results():
    config = {"targets": ["example.com"], "modules": {"recon": True, "report": True}}
    result = run(config)
    assert result["report"]["summary"]["modules_executed"] == ["recon"]
