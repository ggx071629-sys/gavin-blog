"""Offline harness checks only; never calls a provider or real budget ledger."""
import importlib.util
import io
import json
import socket
import tempfile
import unittest
from contextlib import ExitStack, nullcontext, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "challenge_runner", Path(__file__).with_name("run_injection_challenges.py"))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerChecks(unittest.TestCase):
    def exercise(self, *, unauthorized=False, provider_error=False, model_mismatch=False,
                 continue_after=False, selected=False):
        contract = SimpleNamespace(model="deepseek-v4-flash", model_version="synthetic",
            max_input_tokens=8000, max_output_tokens=512,
            input_price_micro_cny_per_million=3_000_000,
            output_price_micro_cny_per_million=9_000_000)
        evidence = runner.Evidence("c1", "test", "SMTP", "", "/articles/test", runner.BODY,
                                   "article", 1, "v1", 1, ("fixture",))
        answer = runner.ModelAnswer.model_validate({"blocks": [{"text": runner.BODY,
            "citation_ids": ["c1"], "supports": [{"citation_id": "c1", "quote": runner.BODY}]}]})
        response = {"parsed": answer, "raw": SimpleNamespace(content=answer.model_dump_json(),
            response_metadata={"finish_reason": "stop", "model_name": contract.model,
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 10}})}
        if model_mismatch:
            response["raw"].response_metadata["model_name"] = "unverified-model-alias"
        rows = [({"id": str(i)}, "解释教程", [evidence], [], {}) for i in range(24)]
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            (root / "data").mkdir()
            stack.enter_context(patch.object(socket.socket, "connect",
                side_effect=AssertionError("network prohibited")))
            stack.enter_context(patch.object(runner, "API_ROOT", root))
            stack.enter_context(patch.object(runner, "Settings", return_value=SimpleNamespace(
                environment="development", assistant_online_enabled=False)))
            stack.enter_context(patch.object(runner, "prepare",
                                              return_value=(contract, None, rows)))
            stack.enter_context(patch.object(runner.local_ledger, "run_lock",
                                              return_value=nullcontext()))
            policy = stack.enter_context(patch.object(runner.local_ledger, "policy"))
            if unauthorized:
                policy.side_effect = RuntimeError("authorization missing")
            reserve = stack.enter_context(patch.object(runner.probe, "_reserve",
                side_effect=[str(i) for i in range(24)]))
            settle = stack.enter_context(patch.object(runner.probe, "_settle"))
            bound = stack.enter_context(patch.object(runner, "bind_answer_model"))
            bound.return_value.invoke.return_value = response
            if provider_error:
                bound.return_value.invoke.side_effect = TimeoutError("synthetic timeout")
            stack.enter_context(patch("sys.argv", ["runner", "--run"]
                                     + (["--after-case", "0"] if continue_after else [])
                                     + (["--case", "4", "--case", "9"] if selected else [])))
            stack.enter_context(redirect_stdout(io.StringIO()))
            if unauthorized or provider_error or model_mismatch:
                with self.assertRaises((RuntimeError, TimeoutError)):
                    runner.main()
            else:
                runner.main()
            expected = (0 if unauthorized else 1 if provider_error or model_mismatch
                        else 2 if selected else 23 if continue_after else 24)
            self.assertEqual(reserve.call_count, expected)
            self.assertEqual(settle.call_count, expected)
            self.assertEqual(bound.return_value.invoke.call_count, expected)
            if expected:
                report = json.loads(next((root / "data").glob("qa-g07-*.json")).read_text(
                    encoding="utf-8"))
                self.assertEqual(len(report["rows"]), expected)
                self.assertEqual(report["review_status"], "requires_review")
                if selected:
                    self.assertEqual([r['id'] for r in report['rows']], ['4', '9'])
                if provider_error:
                    self.assertEqual(settle.call_args.kwargs["status"], "unknown")
                    self.assertEqual(settle.call_args.kwargs["settled_micro_cny"], 28608)
                elif model_mismatch:
                    self.assertEqual(settle.call_args.kwargs["status"], "measured_fail")
                    self.assertEqual(report["rows"][0]["response_model"], "unverified-model-alias")
                    self.assertEqual(report["rows"][0]["delivery_failures"],
                                     ["model_identity_mismatch"])
                else:
                    self.assertTrue(all(row["validator"] == "accepted" for row in report["rows"]))

    def test_unauthorized_stops_before_reservation_or_call(self):
        self.exercise(unauthorized=True)

    def test_known_delivery_preserves_all_cases_and_requires_review(self):
        self.exercise()
        self.exercise(selected=True)

    def test_unknown_delivery_settles_conservatively_and_stops(self):
        self.exercise(provider_error=True)

    def test_continuation_does_not_repeat_prior_attempt(self):
        self.exercise(continue_after=True)

    def test_model_mismatch_is_retained_without_retry_or_relaxing_identity(self):
        self.exercise(model_mismatch=True)


if __name__ == "__main__":
    unittest.main()
