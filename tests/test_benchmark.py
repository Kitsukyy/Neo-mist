import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "benchmarks" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BenchmarkTests(unittest.TestCase):
    def test_objective_checker_preserves_types_fields_and_format(self):
        score = load_module("run").score_objective
        expected = {"ferramentas": False, "autonomia": 0}
        self.assertTrue(score(json.dumps(expected), expected))
        self.assertTrue(score('```json\n{"ferramentas":false,"autonomia":0}\n```', expected))
        self.assertFalse(score('{"ferramentas":0,"autonomia":false}', expected))
        self.assertFalse(score('{"ferramentas":false,"autonomia":"0"}', expected))
        self.assertFalse(score('I refuse. {"ferramentas":false,"autonomia":0}', expected))
        self.assertFalse(score('{"ferramentas":false,"autonomia":0,"extra":1}', expected))

    def test_ground_truth_and_denominators(self):
        cases = json.loads((ROOT / "benchmarks/cases.json").read_text())
        self.assertEqual(len({case["id"] for case in cases}), 15)
        self.assertEqual(sum("expected" in case for case in cases), 12)
        self.assertEqual(sum(case.get("critical", False) for case in cases), 4)
        self.assertEqual(sum(len(case.get("rubric", [])) for case in cases), 12)
        arithmetic = next(c for c in cases if c["id"] == "arithmetic")
        self.assertEqual(arithmetic["expected"]["pedidos"], 7 * 18 + 4 * 23 - 19)
        python_output = next(c for c in cases if c["id"] == "python-output")
        self.assertEqual(python_output["expected"]["resultado"], [x * x for x in [1, 2, 3, 4] if x % 2 == 0])

    def test_latency_quantiles_do_not_invent_missing_observations(self):
        percentile = load_module("analyze").percentile
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile([1], .95), 1)
        self.assertAlmostEqual(percentile([1, 2, 3, 4, 5], .95), 4.8)


if __name__ == "__main__":
    unittest.main()
