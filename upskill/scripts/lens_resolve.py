#!/usr/bin/env python3
"""Resolve a lens spec (name | path | menu:<file>) to a normalized JSON config.

Usage:
  lens_resolve.py --lens skills --out /tmp/lens.json
  lens_resolve.py --lens /path/to/custom.yaml --out /tmp/lens.json
  lens_resolve.py --lens menu:/path/to/menu.json --out /tmp/lens.json

Schema (HARD validated):
  required: name, keywords (list, len>=1), scoring_weights (dict with
            stars/recency/keyword_fit/language_match), integration_cost_model
            (one of: skills, code, infra)
  optional: gh_topics (list), overlay_sources (list), lang (str)
  weights:  sum(scoring_weights.values()) MUST equal 1.0 +/- 0.01
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

LENS_DIR = Path.home() / ".claude" / "skills" / "upskill" / "lenses"
REQUIRED_WEIGHT_KEYS = {"stars", "recency", "keyword_fit", "language_match"}
ALLOWED_COST_MODELS = {"skills", "code", "infra"}


def err(msg: str) -> None:
    print(f"lens_resolve: ERROR: {msg}", file=sys.stderr)


def load_yaml(path: Path) -> dict:
    text = path.read_text()
    if len(text.splitlines()) > 50:
        print(
            f"lens_resolve: WARN: {path} >50 lines (spec §6 risks); continuing",
            file=sys.stderr,
        )
    return yaml.safe_load(text)


def resolve_path(lens_arg: str) -> tuple[str, Path]:
    """Return (kind, path). kind in {"yaml", "menu"}."""
    if lens_arg.startswith("menu:"):
        return "menu", Path(lens_arg[len("menu:"):]).expanduser()
    p = Path(lens_arg).expanduser()
    if p.suffix in {".yaml", ".yml"} and p.exists():
        return "yaml", p
    # bare name — resolve under LENS_DIR
    candidate = LENS_DIR / f"{lens_arg}.yaml"
    if not candidate.exists():
        err(f"lens '{lens_arg}' not found at {candidate}")
        sys.exit(1)
    return "yaml", candidate


def lens_from_menu(menu_path: Path) -> dict:
    if not menu_path.exists():
        err(f"menu file not found: {menu_path}")
        sys.exit(1)
    menu = json.loads(menu_path.read_text())
    items = menu.get("items", [])
    keywords: list[str] = []
    for item in items:
        keywords.extend(item.get("keywords", []))
    if not keywords:
        err(f"menu {menu_path} produced 0 keywords")
        sys.exit(1)
    return {
        "name": f"menu:{menu.get('menu_id', menu_path.stem)}",
        "keywords": keywords,
        "scoring_weights": {
            "stars": 0.3,
            "recency": 0.2,
            "keyword_fit": 0.4,
            "language_match": 0.1,
        },
        "integration_cost_model": "skills",
        "gh_topics": [],
        "overlay_sources": [],
    }


def validate(lens: dict, source: str) -> None:
    for key in ("name", "keywords", "scoring_weights", "integration_cost_model"):
        if key not in lens:
            err(f"{source}: missing required key '{key}'")
            sys.exit(1)
    if not isinstance(lens["keywords"], list) or len(lens["keywords"]) < 1:
        err(f"{source}: 'keywords' must be non-empty list")
        sys.exit(1)
    weights = lens["scoring_weights"]
    if not isinstance(weights, dict):
        err(f"{source}: 'scoring_weights' must be dict")
        sys.exit(1)
    missing = REQUIRED_WEIGHT_KEYS - set(weights.keys())
    if missing:
        err(f"{source}: scoring_weights missing keys: {sorted(missing)}")
        sys.exit(1)
    total = sum(float(v) for v in weights.values())
    if abs(total - 1.0) > 0.01:
        err(
            f"{source}: scoring_weights sum to {total:.4f}, "
            f"must equal 1.0 +/- 0.01 (violation: {weights})"
        )
        sys.exit(1)
    if lens["integration_cost_model"] not in ALLOWED_COST_MODELS:
        err(
            f"{source}: integration_cost_model='{lens['integration_cost_model']}' "
            f"not in {sorted(ALLOWED_COST_MODELS)}"
        )
        sys.exit(1)


def normalize(lens: dict) -> dict:
    out = {
        "name": lens["name"],
        "keywords": list(lens["keywords"]),
        "scoring_weights": {k: float(v) for k, v in lens["scoring_weights"].items()},
        "integration_cost_model": lens["integration_cost_model"],
        "gh_topics": list(lens.get("gh_topics", [])),
        "overlay_sources": list(lens.get("overlay_sources", [])),
    }
    if "lang" in lens:
        out["lang"] = lens["lang"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", required=True, help="lens name | path.yaml | menu:<file>")
    ap.add_argument("--out", required=True, help="output JSON path")
    args = ap.parse_args()

    kind, path = resolve_path(args.lens)
    if kind == "menu":
        lens = lens_from_menu(path)
        source = f"menu:{path}"
    else:
        lens = load_yaml(path)
        source = str(path)
        if not isinstance(lens, dict):
            err(f"{source}: top-level YAML must be a mapping")
            return 1

    validate(lens, source)
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(normalize(lens), indent=2) + "\n")
    print(f"lens_resolve: OK {source} -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
