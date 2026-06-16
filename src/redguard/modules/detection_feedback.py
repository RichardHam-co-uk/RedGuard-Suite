"""Detection feedback loop module.

Closes the loop between red-team activity and blue-team detections: it takes the
set of techniques an engagement plans to exercise, runs them against the
configured detection rules, measures detection coverage, and reports the gaps so
the blue team can tune their detections.

This is a **safe, simulation-only** implementation suitable for the public repo:
no real offensive tooling is invoked. "Running" a technique means recording that
it was exercised (or simulated, in dry-run) and mapping it against the detection
rules supplied in the config. Real tool execution belongs in the private
``internal/`` overlay, gated behind a signed Rules of Engagement.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TechniqueResult:
    """Outcome of exercising a single technique against the detection set."""

    technique_id: str
    name: str
    tool: str
    executed: bool
    detected: bool
    detecting_rules: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "technique_id": self.technique_id,
            "name": self.name,
            "tool": self.tool,
            "executed": self.executed,
            "detected": self.detected,
            "detecting_rules": self.detecting_rules,
        }


class DetectionFeedbackModule:
    """Run red-team techniques against detections and measure coverage."""

    def __init__(self, dry_run: bool = True) -> None:
        self.dry_run = dry_run

    def run_tools(self, techniques: list[dict]) -> list[TechniqueResult]:
        """Exercise each configured technique.

        In dry-run (the default and only mode in the public repo) nothing is
        actually executed; each technique is recorded as exercised so coverage
        can still be assessed.
        """
        results: list[TechniqueResult] = []
        for technique in techniques:
            technique_id = str(technique.get("id", "")).strip()
            if not technique_id:
                logger.warning("Skipping technique with no 'id': %r", technique)
                continue
            name = str(technique.get("name", technique_id))
            tool = str(technique.get("tool", "unknown"))
            mode = "simulated" if self.dry_run else "executed"
            logger.info("Exercising %s (%s) via %s [%s]", technique_id, name, tool, mode)
            results.append(
                TechniqueResult(
                    technique_id=technique_id,
                    name=name,
                    tool=tool,
                    executed=True,
                    detected=False,
                )
            )
        return results

    def check_coverage(
        self, results: list[TechniqueResult], detections: list[dict]
    ) -> list[TechniqueResult]:
        """Annotate each result with the detection rules that cover it."""
        coverage_map: dict[str, list[str]] = {}
        for detection in detections:
            rule = str(detection.get("rule", "")).strip()
            if not rule:
                logger.warning("Skipping detection with no 'rule': %r", detection)
                continue
            for technique_id in detection.get("covers", []):
                coverage_map.setdefault(str(technique_id), []).append(rule)

        for result in results:
            rules = coverage_map.get(result.technique_id, [])
            result.detecting_rules = rules
            result.detected = bool(rules)
        return results

    def report(self, results: list[TechniqueResult]) -> dict:
        """Summarise coverage across all exercised techniques."""
        total = len(results)
        detected = [r for r in results if r.detected]
        gaps = [r.technique_id for r in results if not r.detected]
        ratio = round(len(detected) / total, 4) if total else 0.0
        summary = {
            "techniques_total": total,
            "techniques_detected": len(detected),
            "gaps": gaps,
            "coverage_ratio": ratio,
        }
        logger.info(
            "Detection coverage: %d/%d techniques detected (%.0f%%); %d gap(s)",
            len(detected),
            total,
            ratio * 100,
            len(gaps),
        )
        return summary

    def execute(self, config: dict) -> dict:
        """Run the full feedback loop and return a result dict."""
        feedback = config.get("detection_feedback", {})
        techniques = feedback.get("techniques", [])
        detections = feedback.get("detections", [])

        results = self.run_tools(techniques)
        results = self.check_coverage(results, detections)
        coverage = self.report(results)

        if not results:
            status = "skipped"
            detail = "No techniques configured under 'detection_feedback.techniques'."
        elif not coverage["gaps"]:
            status = "ok"
            detail = f"Full detection coverage across {coverage['techniques_total']} technique(s)."
        else:
            status = "ok"
            detail = (
                f"{coverage['techniques_detected']}/{coverage['techniques_total']} "
                f"technique(s) detected; gaps: {', '.join(coverage['gaps'])}."
            )

        return {
            "status": status,
            "detail": detail,
            "dry_run": self.dry_run,
            "coverage": coverage,
            "results": [r.as_dict() for r in results],
        }


def run(config: dict) -> dict:
    """Module entry point following the standard ``run(config) -> dict`` contract."""
    dry_run = config.get("safety", {}).get("dry_run", True)
    module = DetectionFeedbackModule(dry_run=dry_run)
    return module.execute(config)
