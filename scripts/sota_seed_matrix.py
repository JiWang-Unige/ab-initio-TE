#!/usr/bin/env python3
"""Create a randomized-SOTA small-sample retraining manifest.

This script does not train models. It makes the run matrix deterministic so the
agent/user can audit what will be launched before sbatch submission.
"""
from __future__ import annotations
import argparse, csv, json, os, re
from pathlib import Path


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-") or "model"


def parse_list(s: str, cast=str, what="value"):
    out = []
    for x in s.split(','):
        x = x.strip()
        if not x:
            continue
        try:
            out.append(cast(x))
        except (ValueError, TypeError):
            raise SystemExit(f"bad {what}: {x!r} (expected {getattr(cast, '__name__', cast)})")
    return out


def frac_tag(x: float) -> str:
    # Encode the literal fraction value, collision-free + fixed parse:
    # 0.05 -> 0p05, 0.1 -> 0p1, 1.0 -> 1p0, 0.005 -> 0p005 (no width drift, no
    # 0.005/0.0049 collision that the old int(round(x*1000)) had).
    return ("%g" % x).replace(".", "p").replace("-", "m")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build randomized SOTA screen retraining manifest")
    ap.add_argument("--model", required=True, help="Model name or slug")
    ap.add_argument("--sample-fractions", required=True, help="Comma list, e.g. 0.05,0.10")
    ap.add_argument("--seeds", required=True, help="Comma list, e.g. 1,2,3,4,5")
    ap.add_argument("--metric", required=True, help="Primary metric key")
    ap.add_argument("--dataset", required=True, help="Dataset/split identifier")
    ap.add_argument("--init", default="random", choices=["random", "published_pretrained", "both"], help="Initialization condition")
    ap.add_argument("--epochs", default="", help="Epoch budget for screen protocol")
    ap.add_argument("--patience", default="", help="Patience for screen protocol")
    ap.add_argument("--split-scheme", default="", help="Split scheme — MUST match Track A (e.g. chrom-holdout+CD-HIT0.8). Carried so leakage/fairness is auditable.")
    ap.add_argument("--metric-impl", default="", help="Exact metric implementation (script/lib/params) to match comparability with our runs and SOTA.")
    ap.add_argument("--out", default="", help="Output CSV path; default configs/sota_randomized/<model>_matrix.csv")
    ap.add_argument("--json-out", default="", help="Optional JSON copy")
    args = ap.parse_args()

    model_slug = slugify(args.model)
    fracs = parse_list(args.sample_fractions, float, "sample-fraction")
    seeds = parse_list(args.seeds, int, "seed")
    if not fracs or not seeds:
        raise SystemExit("sample fractions and seeds must be non-empty")
    if any(f <= 0 or f > 1 for f in fracs):
        raise SystemExit("sample fractions must be in (0, 1]")
    inits = ["random", "published_pretrained"] if args.init == "both" else [args.init]

    rows = []
    for init in inits:
        for frac in fracs:
            for seed in seeds:
                run_id = f"SOTA-{model_slug}-SF{frac_tag(frac)}-S{seed}"
                if init == "published_pretrained":
                    run_id = f"{run_id}-PT"
                rows.append({
                    "run_id": run_id,
                    "model": model_slug,
                    "init": init,
                    "sample_fraction": frac,
                    "seed": seed,
                    "dataset": args.dataset,
                    "split_scheme": args.split_scheme,
                    "primary_metric": args.metric,
                    "metric_impl": args.metric_impl,
                    "epochs": args.epochs,
                    "patience": args.patience,
                    "config_path": f"configs/{run_id}.yaml",
                    "sbatch_path": f"sbatch/{run_id}.sbatch",
                    "run_dir": f"runs/{run_id}",
                    "report_path": f"reports/{run_id}.json",
                    "status_path": f"outputs/{run_id}/STATUS",
                })

    out = Path(args.out or f"configs/sota_randomized/{model_slug}_matrix.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    json_out = Path(args.json_out) if args.json_out else out.with_suffix(".json")
    with json_out.open("w", encoding="utf-8") as f:
        json.dump({"model": model_slug, "n_runs": len(rows), "runs": rows}, f, ensure_ascii=False, indent=2)

    print(f"wrote {len(rows)} runs → {out}")
    print(f"json copy → {json_out}")
    for r in rows[:10]:
        print(f"- {r['run_id']} ({r['init']}, frac={r['sample_fraction']}, seed={r['seed']})")
    if len(rows) > 10:
        print(f"... {len(rows)-10} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
