#!/usr/bin/env python3
"""Deterministic pre-training data-leakage / contract gate.

Turns CLAUDE.md §10 prose checklist into a hard, scriptable check. Run BEFORE any
real training (and before sanity smoke). Borrowed (lightweight) from Research OS
data_contracts: split-ID overlap, temporal leakage, schema/target presence.

Supports CSV and JSONL/JSON-lines (one record per line) and HDF5-via-sidecar
(point at a .json describing ids/splits if data is binary).

Exit codes: 0 = pass, 2 = usage/IO error, 3 = LEAKAGE/contract violation (hard block).

Usage:
  python3 scripts/check_data.py --train <train> --val <val> \
      --id-col id [--time-col t] [--target-col y] [--format csv|jsonl|auto]
  # or pass a contract file describing columns:
  python3 scripts/check_data.py --contract data_contract.json
"""
import argparse, json, os, sys, csv

def _load_rows(path, fmt):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if fmt == "auto":
        fmt = "jsonl" if path.endswith((".jsonl", ".ndjson")) else (
              "json" if path.endswith(".json") else "csv")
    rows = []
    if fmt == "csv":
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    elif fmt == "jsonl":
        with open(path) as f:
            rows = [json.loads(l) for l in f if l.strip()]
    elif fmt == "json":
        with open(path) as f:
            data = json.load(f)
        rows = data if isinstance(data, list) else data.get("records", [])
    else:
        raise ValueError(f"unknown format {fmt}")
    return rows, fmt


def _col(rows, name):
    return [r.get(name) for r in rows if name in r]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train"); ap.add_argument("--val"); ap.add_argument("--test")
    ap.add_argument("--id-col"); ap.add_argument("--time-col"); ap.add_argument("--target-col")
    # Genomic split-leakage contract: groups (chromosome/species) and/or homology
    # clusters must be DISJOINT across splits — random split leaks paralogs/co-located loci.
    ap.add_argument("--group-col", help="column whose values (e.g. chromosome/species) must not span splits")
    ap.add_argument("--homology-col", help="homology/ortholog cluster column that must not span splits")
    ap.add_argument("--cluster-file", help="JSON mapping id -> homology cluster (alternative to --homology-col)")
    ap.add_argument("--genomic-scope", dest="genomic_scope", action="store_true", default=None,
                    help="REQUIRE a group/homology split contract (DEFAULT ON for this genomic-DL framework)")
    ap.add_argument("--no-genomic-scope", dest="genomic_scope", action="store_false",
                    help="opt OUT for a non-genomic project (don't require group/homology split contract)")
    ap.add_argument("--format", default="auto", choices=["auto", "csv", "jsonl", "json"])
    ap.add_argument("--contract", help="JSON: {train,val,test,id_col,time_col,target_col,group_col,homology_col,cluster_file,genomic_scope,format}")
    args = ap.parse_args()

    if args.contract:
        with open(args.contract) as f:
            c = json.load(f)
        args.train = args.train or c.get("train"); args.val = args.val or c.get("val")
        args.test = args.test or c.get("test")
        args.id_col = args.id_col or c.get("id_col"); args.time_col = args.time_col or c.get("time_col")
        args.target_col = args.target_col or c.get("target_col"); args.format = c.get("format", args.format)
        args.group_col = args.group_col or c.get("group_col")
        args.homology_col = args.homology_col or c.get("homology_col")
        args.cluster_file = args.cluster_file or c.get("cluster_file")
        if args.genomic_scope is None and "genomic_scope" in c:
            args.genomic_scope = bool(c.get("genomic_scope"))

    # DEFAULT ON: genomic-DL split-leakage (paralog/same-chromosome) is a project hard
    # constraint (CLAUDE §0). Unset → required; opt out only via --no-genomic-scope or
    # contract genomic_scope:false for a genuinely non-genomic task.
    if args.genomic_scope is None:
        args.genomic_scope = True

    report = {"status": "pass", "checks": [], "violations": []}

    def add(name, ok, note):
        report["checks"].append({"check": name, "ok": ok, "note": note})
        if not ok:
            report["violations"].append(f"{name}: {note}")

    if not args.train or not args.val:
        print(json.dumps({"status": "error", "violations": ["--train and --val required (or --contract)"]}, indent=2))
        sys.exit(2)

    try:
        train, fmt = _load_rows(args.train, args.format)
        val, _ = _load_rows(args.val, fmt)
        test = []
        if args.test:
            test, _ = _load_rows(args.test, fmt)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as e:
        print(json.dumps({"status": "error", "violations": [f"load: {e}"]}, indent=2))
        sys.exit(2)

    # splits dict for N-way disjointness checks (test optional)
    splits = {"train": train, "val": val}
    if args.test:
        splits["test"] = test

    add("non_empty", len(train) > 0 and len(val) > 0, f"train={len(train)} val={len(val)}" + (f" test={len(test)}" if args.test else ""))

    def pairwise_disjoint(col_or_map, label, is_map=False):
        """Hard-fail if any value of `col` (or cluster from map) appears in >1 split."""
        seen = {}  # value -> first split that had it
        clash = []
        for sname, rows in splits.items():
            if is_map:
                vals = {col_or_map.get(str(r.get(args.id_col))) for r in rows if args.id_col}
                vals.discard(None)
            else:
                vals = set(_col(rows, col_or_map))
            for v in vals:
                if v in seen and seen[v] != sname:
                    clash.append((v, seen[v], sname))
                else:
                    seen.setdefault(v, sname)
        ok = len(clash) == 0
        ex = "; ".join(f"{v} in {a}&{b}" for v, a, b in clash[:3])
        add(label, ok, "disjoint across splits" if ok else f"{len(clash)} value(s) span splits (e.g. {ex})")

    # --- ID overlap (split leakage) — now N-way (train/val/test) ---
    if args.id_col:
        idsets = {s: set(_col(rows, args.id_col)) for s, rows in splits.items()}
        present = all(len(idsets[s]) == len(splits[s]) and idsets[s] for s in splits)
        add("id_col_present", present, " ".join(f"{s}_ids={len(idsets[s])}" for s in splits))
        clash = []
        names = list(splits)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ov = idsets[names[i]] & idsets[names[j]]
                if ov:
                    clash.append(f"{len(ov)} in {names[i]}&{names[j]} (e.g. {list(ov)[:3]})")
        add("split_id_leakage", not clash, "no overlap" if not clash else "; ".join(clash))

    # --- Genomic split contract: groups (chromosome/species) + homology disjoint ---
    if args.group_col:
        pairwise_disjoint(args.group_col, f"group_split_disjoint[{args.group_col}]")
    if args.homology_col:
        pairwise_disjoint(args.homology_col, f"homology_split_disjoint[{args.homology_col}]")
    elif args.cluster_file:
        try:
            with open(args.cluster_file) as f:
                cmap = {str(k): v for k, v in json.load(f).items()}
            pairwise_disjoint(cmap, "homology_split_disjoint[cluster-file]", is_map=True)
        except (OSError, ValueError, json.JSONDecodeError) as e:
            add("homology_cluster_file", False, f"could not read --cluster-file: {e}")

    # --- Genomic scope HARD contract: random split leaks paralogs/co-located loci ---
    if args.genomic_scope and not (args.group_col or args.homology_col or args.cluster_file):
        add("genomic_split_contract", False,
            "genomic-DL scope declared but NO chromosome/species (--group-col) nor homology "
            "(--homology-col/--cluster-file) split contract given — random split would leak "
            "paralogs/co-located loci and invalidate the SOTA claim. Provide a group/homology split.")

    # --- Temporal leakage ---
    if args.time_col:
        tt, vt = _col(train, args.time_col), _col(val, args.time_col)
        try:
            tt = [float(x) for x in tt]; vt = [float(x) for x in vt]
            ok = (not tt or not vt) or (min(vt) >= max(tt))
            add("temporal_leakage", ok,
                f"max(train_time)={max(tt) if tt else 'NA'} min(val_time)={min(vt) if vt else 'NA'}"
                + ("" if ok else "  ← val has timestamps BEFORE train max (future leakage)"))
        except (ValueError, TypeError):
            add("temporal_leakage", True, "time col non-numeric; skipped numeric check")

    # --- Target presence + non-degenerate ---
    if args.target_col:
        ty = _col(train, args.target_col)
        present = len(ty) == len(train) and bool(ty)
        add("target_col_present", present, f"{len(ty)}/{len(train)} have target")
        if present:
            uniq = set(map(str, ty))
            add("target_not_constant", len(uniq) > 1, f"{len(uniq)} unique target values")

    # --- Schema consistency (keys match across splits) ---
    if train and val:
        ks_t = set(train[0].keys())
        mismatch = []
        for s, rows in splits.items():
            if s == "train" or not rows:
                continue
            ks = set(rows[0].keys())
            if ks != ks_t:
                mismatch.append(f"{s}: train-only={ks_t - ks} {s}-only={ks - ks_t}")
        add("schema_match", not mismatch, "same columns" if not mismatch else "; ".join(mismatch))

    if report["violations"]:
        report["status"] = "leakage"
        print(json.dumps(report, indent=2)); sys.exit(3)
    print(json.dumps(report, indent=2)); sys.exit(0)


if __name__ == "__main__":
    main()
