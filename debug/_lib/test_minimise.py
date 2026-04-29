"""Unit tests for ddmin engine. Run: python3 -m unittest _lib.test_minimise -v"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from minimise import (  # type: ignore
    Fingerprint,
    MinimiseStats,
    ProbeResult,
    bsearch_workload,
    ddmin,
    ddmin_lines,
    flaky_probe,
    render_log,
)


class TestDdminCore(unittest.TestCase):
    """Synthetic tests of pure ddmin algorithm — no subprocess."""

    def test_single_culprit(self):
        # Bug = subset contains item 5
        items = list(range(10))
        result, stats = ddmin(items, lambda s: 5 in s)
        self.assertEqual(result, [5])
        self.assertGreater(stats.probes, 0)

    def test_two_culprits_independent(self):
        # Bug = subset contains BOTH 3 AND 7
        items = list(range(10))
        result, stats = ddmin(items, lambda s: 3 in s and 7 in s)
        self.assertEqual(set(result), {3, 7})

    def test_no_reduction_possible(self):
        # Bug = subset has length >= 5 (every item matters equally)
        items = list(range(10))
        result, stats = ddmin(items, lambda s: len(s) >= 5)
        # ddmin can't isolate which 5; should land at some 5-element minimal
        self.assertEqual(len(result), 5)

    def test_max_probes_cap(self):
        items = list(range(20))
        result, stats = ddmin(items, lambda s: 5 in s and 10 in s and 15 in s, max_probes=3)
        self.assertTrue(stats.cap_reached)
        self.assertLessEqual(stats.probes, 3)

    def test_already_minimal(self):
        items = [42]
        result, stats = ddmin(items, lambda s: 42 in s)
        self.assertEqual(result, [42])

    def test_empty_input(self):
        items = []
        result, stats = ddmin(items, lambda s: True)
        self.assertEqual(result, [])


class TestFingerprint(unittest.TestCase):

    def test_exit_code_match(self):
        from _lib.minimise import ProbeResult
        fp = Fingerprint(exit_code=1)
        self.assertTrue(fp.match(ProbeResult(exit=1, stdout="", stderr="", wall_ms=0)))
        self.assertFalse(fp.match(ProbeResult(exit=0, stdout="", stderr="", wall_ms=0)))

    def test_stderr_regex(self):
        from _lib.minimise import ProbeResult
        fp = Fingerprint(exit_nonzero=True, stderr_regex=r"OOM|out of memory")
        self.assertTrue(fp.match(ProbeResult(exit=137, stdout="", stderr="OOM killed", wall_ms=0)))
        self.assertFalse(fp.match(ProbeResult(exit=137, stdout="", stderr="something else", wall_ms=0)))

    def test_no_criteria_raises(self):
        from _lib.minimise import ProbeResult
        fp = Fingerprint()
        with self.assertRaises(ValueError):
            fp.match(ProbeResult(exit=1, stdout="", stderr="", wall_ms=0))


class TestDdminLines(unittest.TestCase):
    """Real subprocess + file I/O — synthetic shell repro."""

    def test_shrink_repro_to_one_line(self):
        # Repro: 6 echo lines + one `exit 1` — bug is the exit 1
        with tempfile.TemporaryDirectory() as td:
            repro = Path(td) / "repro.sh"
            repro.write_text(
                "#!/usr/bin/env bash\n"
                "set -e\n"
                "echo line-A\n"
                "echo line-B\n"
                "echo line-C\n"
                "exit 1\n"
                "echo line-after\n"
            )
            os.chmod(repro, 0o755)

            out = Path(td) / "repro-min.sh"
            fp = Fingerprint(exit_code=1)
            final, stats = ddmin_lines(repro, fp, max_probes=50, out_path=out, timeout=10)

            # The minimal candidate is `exit 1\n`; structural lines (#!, set -e) survive
            non_structural = [ln for ln in final if not ln.startswith("#!") and not ln.startswith("set ")]
            self.assertEqual(non_structural, ["exit 1\n"])
            self.assertTrue(out.exists())
            self.assertIn("exit 1", out.read_text())

    def test_preserves_when_no_strip_helps(self):
        with tempfile.TemporaryDirectory() as td:
            repro = Path(td) / "repro.sh"
            repro.write_text("#!/usr/bin/env bash\nexit 1\n")
            os.chmod(repro, 0o755)
            fp = Fingerprint(exit_code=1)
            final, stats = ddmin_lines(repro, fp, max_probes=20, timeout=10)
            self.assertIn("exit 1\n", final)


class TestBsearchWorkload(unittest.TestCase):

    def test_finds_smallest_regressing(self):
        # Synthetic: wall_ms = size * 10
        baseline_ms = 100
        # threshold = 150ms ⇒ smallest regressing size = 15
        smallest, stats = bsearch_workload(
            low=1, high=100,
            perf_fn=lambda s: s * 10,
            baseline_ms=baseline_ms,
            target_ratio=1.5,
        )
        self.assertEqual(smallest, 15)

    def test_no_regression(self):
        # Workload always under threshold
        smallest, stats = bsearch_workload(
            low=1, high=100,
            perf_fn=lambda s: 10,
            baseline_ms=100,
            target_ratio=1.5,
        )
        # No regression → returns high as best-known
        self.assertEqual(smallest, 100)


class TestFlakyProbe(unittest.TestCase):

    def test_majority_oracle(self):
        from _lib.minimise import ProbeResult
        # raw_probe returns fail 7/10 times deterministically
        counter = {"i": 0}

        def raw(_subset):
            counter["i"] += 1
            # fail on i in {1..7}
            return ProbeResult(exit=1 if counter["i"] <= 7 else 0, stdout="", stderr="", wall_ms=0)

        fp = Fingerprint(exit_code=1)
        oracle = flaky_probe(raw, fp, runs=10, threshold=0.5)
        self.assertTrue(oracle([]))  # 7/10 >= 0.5

    def test_below_threshold(self):
        from _lib.minimise import ProbeResult
        counter = {"i": 0}

        def raw(_subset):
            counter["i"] += 1
            return ProbeResult(exit=1 if counter["i"] <= 2 else 0, stdout="", stderr="", wall_ms=0)

        fp = Fingerprint(exit_code=1)
        oracle = flaky_probe(raw, fp, runs=10, threshold=0.5)
        self.assertFalse(oracle([]))  # 2/10 < 0.5

    def test_runs_below_2_raises(self):
        with self.assertRaises(ValueError):
            flaky_probe(lambda s: None, Fingerprint(exit_code=1), runs=1)


class TestRenderLog(unittest.TestCase):

    def test_log_table(self):
        stats = MinimiseStats(probes=2, kept_strips=1)
        stats.log = [
            {"probe": 1, "label": "complement-of-chunk-1/2", "size": 5, "reproduces": True},
            {"probe": 2, "label": "isolate-chunk-1/2", "size": 3, "reproduces": False},
        ]
        out = render_log(stats, "test")
        self.assertIn("probes=2", out)
        self.assertIn("complement-of-chunk-1/2", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
