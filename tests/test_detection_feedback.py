"""Tests for the detection feedback loop module."""

from redguard.modules.detection_feedback import DetectionFeedbackModule, run


def _config(dry_run: bool = True) -> dict:
    return {
        "safety": {"dry_run": dry_run},
        "detection_feedback": {
            "techniques": [
                {"id": "T1059.001", "name": "PowerShell", "tool": "atomic-red-team"},
                {"id": "T1003", "name": "OS Credential Dumping", "tool": "cred-dump-sim"},
                {"id": "T1566", "name": "Phishing", "tool": "phish-sim"},
            ],
            "detections": [
                {"rule": "SIEM-001", "covers": ["T1059.001"]},
                {"rule": "EDR-014", "covers": ["T1003", "T1059.001"]},
            ],
        },
    }


def test_run_returns_status_and_detail():
    result = run(_config())
    assert "status" in result
    assert "detail" in result


def test_dry_run_defaults_to_true_when_unset():
    module = DetectionFeedbackModule()
    assert module.dry_run is True


def test_run_honors_dry_run_from_config():
    result = run(_config(dry_run=False))
    assert result["dry_run"] is False


def test_coverage_identifies_detected_and_gaps():
    result = run(_config())
    coverage = result["coverage"]
    assert coverage["techniques_total"] == 3
    assert coverage["techniques_detected"] == 2
    # T1566 (Phishing) has no detection rule -> coverage gap.
    assert coverage["gaps"] == ["T1566"]


def test_coverage_ratio_is_fraction_detected():
    result = run(_config())
    assert result["coverage"]["coverage_ratio"] == round(2 / 3, 4)


def test_detecting_rules_are_reported_per_technique():
    result = run(_config())
    by_id = {t["technique_id"]: t for t in result["results"]}
    assert by_id["T1059.001"]["detecting_rules"] == ["SIEM-001", "EDR-014"]
    assert by_id["T1566"]["detected"] is False
    assert by_id["T1566"]["detecting_rules"] == []


def test_empty_config_is_skipped():
    result = run({"safety": {"dry_run": True}})
    assert result["status"] == "skipped"
    assert result["coverage"]["techniques_total"] == 0


def test_full_coverage_status_ok():
    config = {
        "detection_feedback": {
            "techniques": [{"id": "T1003", "name": "Cred Dump"}],
            "detections": [{"rule": "EDR-014", "covers": ["T1003"]}],
        }
    }
    result = run(config)
    assert result["status"] == "ok"
    assert result["coverage"]["coverage_ratio"] == 1.0
    assert result["coverage"]["gaps"] == []
