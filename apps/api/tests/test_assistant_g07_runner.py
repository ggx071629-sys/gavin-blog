"""Expose the standalone evaluation runner checks to the API's isolated gate."""
import importlib.util
from pathlib import Path

path = (Path(__file__).resolve().parents[3] / "plan-build/assistant-gap-closure"
        / "evaluation/test_injection_runner.py")
spec = importlib.util.spec_from_file_location("g07_offline_checks", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RunnerChecks = module.RunnerChecks
