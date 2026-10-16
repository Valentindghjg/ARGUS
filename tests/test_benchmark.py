# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 ARGUS contributors
"""Plan G5: the synthetic benchmark matches its documented outcomes and stays synthetic."""
from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from argus_security.registry import Registry, is_shared_sender

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("argus_benchmark", ROOT / "scripts" / "benchmark.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(benchmark.CASES.read_text(encoding="utf-8"))

    def test_every_case_has_its_documented_outcome(self):
        report = benchmark.run()
        self.assertEqual(report["problems"], [])
        self.assertEqual(len(report["cases"]), len(self.data["cases"]))
        # Hits, false alarms and limits are all represented.
        self.assertTrue(report["totals"]["account"].get("probable"))
        self.assertTrue(report["totals"]["no_account"].get("none"))
        self.assertTrue(report["limits"])

    def test_cases_contain_only_invented_addresses(self):
        registry = Registry()
        self.assertTrue(all(address.endswith(".invalid") for address in self.data["own"]))
        ids = [case["id"] for case in self.data["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.data["cases"]:
            mail = case["mail"]
            with self.subTest(case=case["id"]):
                self.assertTrue(set(mail["to"]) | set(mail.get("cc", [])) <= {"own", "second", "other"})
                if mail["from"] in {"own", "second"}:
                    continue
                domain = mail["from"].rsplit("@", 1)[1]
                self.assertTrue(domain.endswith((".example", ".invalid")) or registry.match(domain)
                                or is_shared_sender(domain), domain)

    def test_a_changed_outcome_or_an_undocumented_gap_fails(self):
        changed = json.loads(json.dumps(self.data))
        changed["cases"][0]["expect"]["outcome"] = "weak"
        del changed["cases"][-1]["limit"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "cases.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            out = StringIO()
            with redirect_stdout(out):
                self.assertEqual(benchmark.main(["--cases", str(path)]), 1)
        self.assertIn("created-en: expected", out.getvalue())
        self.assertIn("unusual-wording: a gap", out.getvalue())

    def test_report_states_that_it_is_no_proof_of_real_accuracy(self):
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(benchmark.main([]), 0)
        self.assertIn("not proof of accuracy on real mailboxes", out.getvalue())
        out = StringIO()
        with redirect_stdout(out):
            benchmark.main(["--json"])
        self.assertEqual(json.loads(out.getvalue())["about"], benchmark.DISCLAIMER)


if __name__ == "__main__":
    unittest.main()
