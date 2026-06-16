import pytest
from modules.garak import GarakModule # Assuming module is correctly imported

# Fixture to create a dummy GarakModule instance
@pytest.fixture
def garak_module():
    # Use a temporary path for testing
    return GarakModule("dummy_config.yaml")

def test_garak_initialization():
    """Test that the GarakModule initializes correctly."""
    garak = GarakModule("test_config.yaml")
    assert garak.garak_config_path == "test_config.yaml"

@pytest.mark.parametrize("probes, expected_status", [
    ([], "success"), # Test case for no probes (should still attempt run)
    (["llm"], "success"), # Test basic successful probe list
])
def test_run_probes_success(garak_module, probes, expected_status):
    """Test GarakModule.run_probes runs and returns success structure."""
    # We mock subprocess.run to ensure the test doesn't rely on external 'garak' executable state
    with pytest.MonkeyPatch().context() as mp:
        def mock_subprocess_run(command, capture_output, text, check):
            mock_result = MagicMock()
            mock_result.stdout = "Garak scan successful output for probes."
            mock_result.stderr = ""
            # Mocking the return code success (0)
            return mock_result

        mp.setattr("subprocess", "run", mock_subprocess_run)

        if probes:
             results = garak_module.run_probes(probes_to_run=probes)
        else:
             # For the empty probe case, we might need a different mock setup or adjust test logic
            results = garak_module.run_probes() 

        assert results["status"] == "success"
        assert isinstance(results["probes_data"], dict)
        if probes:
             assert all(p in results['probes_data'] for p in probes)


def test_run_probes_garak_not_found(garak_module):
    """Test handling when the 'garak' command is not available."""
    with pytest.MonkeyPatch().context() as mp:
        # Force FileNotFoundError on subprocess call
        mp.setattr("subprocess.run", lambda *args, **kwargs: exec("raise FileNotFoundError")) 

        results = garak_module.run_probes(probes_to_run=["mock"])
        assert results["status"] == "failure"
        assert "Garak executable not found." in str(results["error"])

def test_run_probes_garak_failure(garak_module):
    """Test handling of non-zero exit code from Garak."""
    with pytest.MonkeyPatch().context() as mp:
        # Mock CalledProcessError for failure simulation
        mock_e = subprocess.CalledProcessError(1, ["garak"], stdout="", stderr="Access denied.")
        mp.setattr("subprocess", "run", lambda *args, **kwargs: exec(f"raise {mock_e}"))

        results = garak_module.run_probes(probes_to_run=["llm"])
        assert results["status"] == "failure"
        assert "Access denied." in str(results["error"])
        assert "Access denied." in str(results["details"])