"""S5 held-out validation — randomised synthetic cases (no author-chosen culprit positions).

Run: python3 -m unittest _lib.test_held_out -v
"""
from __future__ import annotations

import os
import random
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from minimise import (  # type: ignore
    Fingerprint,
    bsearch_workload,
    ddmin,
    ddmin_lines,
    flaky_probe,
)


SEED = int(time.time())  # deterministic per-run; recorded in report


class TestHeldOutBugVariant(unittest.TestCase):
    """Random N-line repros with random culprit position. No author preview."""

    def _make_random_repro(self, n_lines: int, seed: int) -> tuple[Path, int]:
        """Return (repro_path, culprit_index)."""
        rng = random.Random(seed)
        culprit = rng.randint(2, n_lines - 2)  # avoid edges
        td = tempfile.mkdtemp(prefix="ddmin-heldout-")
        repro = Path(td) / "repro.sh"
        body = ["#!/usr/bin/env bash\n", "set -e\n"]
        for i in range(n_lines):
            if i == culprit:
                body.append(f"exit 1  # culprit (random idx={i})\n")
            else:
                body.append(f"echo line-{i}\n")
        repro.write_text("".join(body))
        os.chmod(repro, 0o755)
        return repro, culprit

    def _validate(self, n: int, sub_seed: int):
        repro, culprit = self._make_random_repro(n, SEED + sub_seed)
        fp = Fingerprint(exit_code=1)
        out = repro.with_name("repro-min.sh")
        final, stats = ddmin_lines(repro, fp, max_probes=200, out_path=out, timeout=10)

        # Correctness: minimised file still triggers fingerprint
        import subprocess
        r = subprocess.run([str(out)], capture_output=True, timeout=10)
        self.assertTrue(fp.match(type("R", (), {
            "exit": r.returncode,
            "stdout": r.stdout.decode(errors="ignore"),
            "stderr": r.stderr.decode(errors="ignore"),
            "wall_ms": 0,
        })()), f"minimised repro stopped reproducing for n={n} seed={sub_seed}")

        # Shrink ratio: final size much smaller than original
        original_size = n
        final_non_structural = sum(1 for ln in final
                                    if not ln.startswith("#!") and not ln.strip().startswith("set "))
        ratio = final_non_structural / original_size
        self.assertLess(ratio, 0.5, f"shrink ratio {ratio:.2f} >= 50% for n={n} seed={sub_seed}")

        # Sanity: minimised contains the culprit (line with `exit 1`)
        joined = "".join(final)
        self.assertIn("exit 1", joined, f"culprit at idx={culprit} got stripped (n={n})")

        return {"n": n, "seed": sub_seed, "culprit": culprit, "final_size": final_non_structural,
                "shrink_ratio": ratio, "probes": stats.probes}

    def test_n8_random(self):
        r = self._validate(8, sub_seed=1)
        print(f"\nHeld-out bug n=8: {r}")

    def test_n15_random(self):
        r = self._validate(15, sub_seed=2)
        print(f"\nHeld-out bug n=15: {r}")

    def test_n30_random(self):
        r = self._validate(30, sub_seed=3)
        print(f"\nHeld-out bug n=30: {r}")


class TestHeldOutFlakyVariant(unittest.TestCase):
    """Random subset of items where 'bug present' = subset includes culprit at random idx."""

    def test_random_culprit_n12(self):
        rng = random.Random(SEED + 100)
        items = list(range(12))
        culprit = rng.choice(items)
        # Synthetic flaky: probe is True 70% of the time when culprit in subset
        def raw_probe(subset):
            from minimise import ProbeResult  # type: ignore
            in_subset = culprit in subset
            # Flaky: 70% match if in subset, 0% if not
            should_match = (rng.random() < 0.7) if in_subset else False
            return ProbeResult(exit=1 if should_match else 0, stdout="", stderr="", wall_ms=0)

        fp = Fingerprint(exit_code=1)
        oracle = flaky_probe(raw_probe, fp, runs=10, threshold=0.4)
        result, stats = ddmin(items, oracle, max_probes=200)
        self.assertIn(culprit, result, f"flaky ddmin lost culprit {culprit}; got {result}")
        self.assertLess(len(result), len(items), f"no shrink: {len(result)}/{len(items)}")
        print(f"\nHeld-out flaky: culprit={culprit} found_in={result} probes={stats.probes}")


class TestHeldOutPerfVariant(unittest.TestCase):
    """Random regression-knee position; bsearch must find smallest size >= knee."""

    def test_random_knee(self):
        rng = random.Random(SEED + 200)
        knee = rng.randint(20, 80)
        baseline_ms = 100
        threshold = 150  # 1.5x

        def perf_fn(size):
            # Below knee: fast (50ms); at/above knee: slow (200ms)
            return 50 if size < knee else 200

        smallest, stats = bsearch_workload(1, 100, perf_fn, baseline_ms, target_ratio=1.5, max_probes=20)
        self.assertEqual(smallest, knee,
                         f"bsearch found {smallest} but knee was at {knee}")
        print(f"\nHeld-out perf: knee={knee} found={smallest} probes={stats.probes}")


if __name__ == "__main__":
    print(f"# S5 held-out validation seed: {SEED}")
    unittest.main(verbosity=2)
