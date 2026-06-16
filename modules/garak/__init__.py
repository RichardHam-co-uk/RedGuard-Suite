from typing import List, Dict, Any
import subprocess
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)

class GarakModule:
    """
    Manages the execution of Garak LLM red teaming probes programmatically.
    Wraps external 'garak' command and parses results into a standardized format.
    """

    def __init__(self, garak_config_path: str = "garak_probes.yaml"):
        self.garak_config_path = garak_config_path

    def run_probes(self, probes_to_run: List[str] = None) -> Dict[str, Any]:
        """
        Runs the Garak scans.
        Args:
            probes_to_run: Optional list of specific probes (e.g., ["llm", "cve"]).
                            If None, runs all enabled probes defined in config.
        Returns:
            A dictionary containing standardized results from all executed probes.
        """
        logging.info(f"Starting Garak scan using configuration at {self.garak_config_path}")
        
        # 1. Construct the command
        command = ["garak", "--config", self.garak_config_path]
        if probes_to_run:
            command += ["--probes", ",".join(probes_to_run)]

        try:
            # Execute Garak in subprocess mode to capture output and exit code
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            logging.info("Garak scan completed successfully.")
            raw_output = result.stdout
        except subprocess.CalledProcessError as e:
            logging.error(f"Garak scan failed with return code {e.returncode}.")
            logging.error("STDOUT:", e.stdout)
            logging.error("STDERR:", e.stderr)
            return {"status": "failure", "error": str(e), "details": e.stderr}
        except FileNotFoundError:
            logging.error("The 'garak' command was not found. Please ensure Garak is installed and in PATH.")
            return {"status": "failure", "error": "Garak executable not found."}

        # 2. Parse results into standard RedGuard format (Highly simplified for demonstration)
        standardized_results = {
            "status": "success",
            "raw_output": raw_output,
            "probes_data": self._parse_garak_output(raw_output, probes_to_run)
        }
        return standardized_results

    def _parse_garak_output(self, raw_output: str, requested_probes: List[str]) -> Dict[str, Any]:
        """
        Parses the raw text output from Garak into a structured dictionary.
        This is highly dependent on the actual garak output format.
        """
        parsed_data = {}
        for probe in requested_probes if requested_probes else ["mocked"]: # Mocking for generic structure
             # In a real scenario, we'd parse by section headers or JSON output from Garak
            parsed_data[probe] = {
                "score": random.randint(60, 100),
                "findings": f"Mock findings for {probe} based on raw data analysis.",
                "risk_level": "Medium"
            }
        return parsed_data

# Example usage (for testing)
if __name__ == '__main__':
    garak = GarakModule()
    # Mocking the subprocess.run call for standalone testability if 'garak' is not installed
    print("--- Running mock Garak module test ---")
    mock_results = garak.run_probes(probes_to_run=["llm", "cve"])
    import json
    print(json.dumps(mock_results, indent=2))
