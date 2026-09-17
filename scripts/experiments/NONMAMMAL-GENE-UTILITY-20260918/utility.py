#!/usr/bin/env python3
"""Finite paired native AUGUSTUS mask experiment; no predictor training."""
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import gzip
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[3]
NAME = "NONMAMMAL-GENE-UTILITY-20260918"
BASE = ROOT / "outputs" / NAME
CFG = json.loads((ROOT / "configs" / (NAME + ".json")).read_text())


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


b = module(ROOT / "scripts/experiments/P3-TIBERIUS-BASE-MASK-20260911-R1/base_mask.py", "nonmammal_base")


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def run(argv, out, prefix, env=None):
    tick = time.monotonic()
    with (out / (prefix + ".stdout")).open("w") as stdout, (out / (prefix + ".stderr")).open("w") as stderr:
        done = subprocess.run(argv, stdout=stdout, stderr=stderr, env=env)
    row = {"argv": argv, "seconds": time.monotonic() - tick, "exit_code": done.returncode}
    dump(out / (prefix + ".command.json"), row)
    if done.returncode:
        raise RuntimeError(f"{prefix} exited {done.returncode}; see native stderr")
    return row


def fasta_index(path):
    result = {}
    for line in Path(str(path) + ".fai").read_text().splitlines():
        f = line.split("\t")
        result[f[0]] = tuple(map(int, f[1:5]))
    return result


def extract(path, idx, chrom, start, end):
    length, offset, bases, width = idx[chrom]
    if not 0 <= start < end <= length:
        raise ValueError("invalid FASTA interval")
    left = offset + start // bases * width + start % bases
    last = end - 1
    right = offset + last // bases * width + last % bases + 1
    with path.open("rb") as h:
        h.seek(left)
        sequence = h.read(right-left).replace(b"\n", b"").replace(b"\r", b"").decode("ascii").upper()
    if len(sequence) != end-start:
        raise ValueError("FASTA index/extraction length mismatch")
    return sequence


def reference(path, cores):
    """Gene loci follow connected transcript spans, not overlapping CDS spans.

    Alternative complete isoforms can have disjoint coding regions at one locus.
    This rule is frozen before any AUGUSTUS/D output is generated.
    """
    rows = defaultdict(list)
    excluded = Counter()
    selected = {c.chrom: c for c in cores}
    with gzip.open(path, "rt") as h:
        for line in h:
            f = line.rstrip().split("\t")
            if len(f) != 16:
                raise ValueError("Expected 16-column genePredExtended")
            chrom, strand = f[2:4]
            if chrom not in selected:
                continue
            tx_start, tx_end, cds_start, cds_end, n = map(int, f[4:9])
            if cds_start == cds_end or f[13:15] != ["cmpl", "cmpl"]:
                excluded["noncoding_or_incomplete"] += 1
                continue
            starts = [int(v) for v in f[9].rstrip(",").split(",")]
            ends = [int(v) for v in f[10].rstrip(",").split(",")]
            frames = [int(v) for v in f[15].rstrip(",").split(",")]
            if strand not in ("+", "-") or not (len(starts) == len(ends) == len(frames) == n) or not (0 <= tx_start <= cds_start < cds_end <= tx_end):
                raise ValueError("Invalid reference coordinates/strand/exon counts")
            pieces = []
            for s, e, frame in zip(starts, ends, frames):
                if not tx_start <= s < e <= tx_end:
                    raise ValueError("Invalid exon interval")
                left, right = max(s, cds_start), min(e, cds_end)
                if left < right:
                    if frame not in (0, 1, 2):
                        raise ValueError("Invalid coding frame")
                    pieces.append((left, right))
            chain = b.Chain(strand, b.normalize(pieces))
            core = selected[chrom]
            if not core.start <= chain.intervals[0][0] < core.end:
                excluded["outside_fixed_core"] += 1
                continue
            if chain.intervals[-1][1] > core.halo_end:
                excluded["boundary_incomplete"] += 1
                continue
            rows[(chrom, strand, f[12] or f[1])].append({"chain": chain, "transcript_id": f[1], "tx_start": tx_start, "tx_end": tx_end})
    units, disjoint, mapping = [], [], {}
    for (chrom, strand, name), values in sorted(rows.items()):
        groups = []
        end = -1
        for row in sorted(values, key=lambda r: (r["tx_start"], r["tx_end"])):
            if row["tx_start"] > end:
                groups.append([])
            groups[-1].append(row)
            end = max(end, row["tx_end"])
        if len(groups) > 1:
            disjoint.append({"chrom": chrom, "strand": strand, "name2": name, "loci": len(groups)})
        for group in groups:
            lo, hi = min(r["tx_start"] for r in group), max(r["tx_end"] for r in group)
            uid = f"{chrom}|{strand}|{name}|{lo}-{hi}"
            chains = sorted(set(r["chain"] for r in group))
            unit = {"unit_id": uid, "chrom": chrom, "strand": strand, "name2": name, "owner": selected[chrom].key, "span": [lo, hi], "transcript_ids": sorted(r["transcript_id"] for r in group), "isoforms": [{"intervals": [list(v) for v in chain.intervals]} for chain in chains]}
            units.append(unit)
            for chain in chains:
                key = (chrom, chain.strand, chain.intervals)
                if key in mapping and mapping[key] != uid:
                    raise ValueError("Exact reference CDS chain maps to multiple gene loci")
                mapping[key] = uid
    return {"reference_source": str(path), "unit_definition": "(chrom,strand,name2), connected transcript-span locus", "unit_count": len(units), "units": units, "per_core_unit_count": dict(Counter(u["owner"] for u in units)), "excluded_transcript_rows": dict(excluded), "disjoint_name2_keys_split": disjoint}


def prepare(species):
    import numpy as np
    out = BASE / species
    out.mkdir(parents=True, exist_ok=False)
    dump(out / "config.json", CFG)
    source = ROOT / ".backup/data/genome_data/current_eukaryotes/animals" / species
    genome = source / (CFG["species"][species]["assembly"] + ".fa")
    idx = fasta_index(genome)
    excluded = defaultdict(list)
    for split in ("TRAIN", "CAL"):
        path = ROOT / "outputs/CROSS-SPECIES-L1-MATERIAL-TRAIN-20260903/12176202" / split / (species + ".jsonl.gz")
        with gzip.open(path, "rt") as h:
            for line in h:
                r = json.loads(line)
                excluded[r["chrom"]].append((r["start"], r["end"]))
    g = CFG["geometry"]
    core_bp, halo = g["core_bp"], g["halo_bp"]
    geometry, rejected = [], Counter()
    for chrom in sorted((c for c in idx if re.fullmatch(r"chr\d+", c)), key=lambda c: (-idx[c][0], c)):
        n = idx[chrom][0]
        starts = sorted(range(halo, n-core_bp-halo+1, 1000000), key=lambda x: (abs(2*x+core_bp-n), x))
        for start in starts:
            hs, he = start-halo, start+core_bp+halo
            if any(left < he and right > hs for left, right in excluded[chrom]):
                rejected["D_train_cal_overlap"] += 1
                continue
            core = b.Core(chrom, len(geometry), start, start+core_bp, hs, he)
            geometry.append({**asdict(core), "id": f"c{len(geometry):02d}", "record_id": core.record_id})
            break
        if len(geometry) == g["count"]:
            break
    if len(geometry) != g["count"]:
        raise ValueError("Insufficient eligible chromosomes under fixed geometry; no result-based fallback")
    dump(out / "geometry.json", geometry)
    assembly = CFG["species"][species]["assembly"]
    url = f"https://hgdownload.soe.ucsc.edu/goldenPath/{assembly}/database/ncbiRefSeq.txt.gz"
    ref = out / "ncbiRefSeq.txt.gz"
    with urllib.request.urlopen(url) as r, ref.open("wb") as f:
        headers = dict(r.headers)
        import shutil
        shutil.copyfileobj(r, f)
    cores = [b.Core(**{k:row[k] for k in ("chrom", "index", "start", "end", "halo_start", "halo_end")}) for row in geometry]
    report = reference(ref, cores)
    dump(out / "reference.json", report)
    repeat_rows = defaultdict(list)
    with gzip.open(source / "rmsk.txt.gz", "rt") as h:
        for line in h:
            f = line.rstrip().split("\t")
            if len(f) != 17:
                raise ValueError("Expected raw UCSC 17-column rmsk table")
            if f[11].rstrip("?").split("/")[0] in CFG["R_TE"]["included_roots"]:
                repeat_rows[f[5]].append((int(f[6]), int(f[7])))
    red_gnm, red_msk, red_rpt = (out / x for x in ("red_genome", "red_masked", "red_repeats"))
    for p in (red_gnm, red_msk, red_rpt):
        p.mkdir()
    panel = red_gnm / "panel.fa"
    inputs = []
    with panel.open("w") as pooled:
        for row, core in zip(geometry, cores):
            cell = out / row["id"]
            cell.mkdir()
            sequence = extract(genome, idx, core.chrom, core.halo_start, core.halo_end)
            b.write_fasta(cell / "U.fasta", core.record_id, sequence)
            pooled.write(f">{core.record_id}\n{sequence}\n")
            mask = b.interval_mask(repeat_rows[core.chrom], core.halo_start, core.halo_end)
            masked = "".join(v.lower() if flag and v in "ACGT" else v for v, flag in zip(sequence, mask))
            b.write_fasta(cell / "R_TE.fasta", core.record_id, masked)
            inputs.append({"id": row["id"], "length": len(sequence), "N_bp": sequence.count("N"), "R_TE_mask_bp": sum(v in "acgt" for v in masked), "reference_loci": report["per_core_unit_count"].get(core.key, 0)})
    run([str(ROOT / "refs/repos/Red/bin/Red"), "-gnm", str(red_gnm), "-msk", str(red_msk), "-rpt", str(red_rpt), "-cor", "4", "-frm", "2"], out, "red")
    red_files = list(red_msk.glob("*.msk"))
    if len(red_files) != 1:
        raise ValueError("Expected exactly one native Red mask")
    red = dict(b.fasta(red_files[0]))
    if set(red) != {row["record_id"] for row in geometry}:
        raise ValueError("Red record mismatch")
    for row in geometry:
        cell = out / row["id"]
        original = next(b.fasta(cell / "U.fasta"))[1]
        masked = red[row["record_id"]]
        if masked.upper() != original:
            raise ValueError("Red altered sequence letters")
        b.write_fasta(cell / "RED.fasta", row["record_id"], masked)
    dump(out / "preparation.json", {"status": "PREPARED", "genome": str(genome), "gene_reference_url": url, "download_headers": headers, "geometry_rejections": dict(rejected), "input_core_bp": len(cores)*core_bp, "input_with_halos_bp": sum(c.halo_end-c.halo_start for c in cores), "inputs": inputs, "gene_reference_loci": report["unit_count"], "D_train_cal_bp_overlap": 0, "selection_used_labels_or_outcomes": False})
    print(json.dumps({"species": species, "reference_loci": report["unit_count"], "inputs": inputs}), flush=True)


def d_mask(species):
    import numpy as np
    out = BASE / species
    if json.loads((out / "preparation.json").read_text())["status"] != "PREPARED":
        raise ValueError("Preparation incomplete")
    rc = module(ROOT / "scripts/experiments/D-EXTERNAL-RC0-20260914/rc0.py", "nonmammal_D")
    cfg = json.loads((ROOT / CFG["D"]["config"]).read_text())
    args = argparse.Namespace(remote_root=ROOT, model_dir=None, tokenizer_dir=None, model_code_dir=None, calibration_json=None, cpu=False)
    model, tokenizer, device, cal, load_seconds, paths = rc._load_model(cfg, args)
    records = []
    for row in json.loads((out / "geometry.json").read_text()):
        cell = out / row["id"]
        record, sequence = next(b.fasta(cell / "U.fasta"))
        tick = time.monotonic()
        p = rc._infer_sequence(sequence, model, tokenizer, device, CFG["D"]["batch_size"], float(cal["platt_slope"]), float(cal["platt_intercept"]))
        callable_mask = np.fromiter((v in "ACGT" for v in sequence), dtype=bool)
        mask = (p >= float(cal["threshold"])) & callable_mask
        masked = "".join(v.lower() if flag else v for v, flag in zip(sequence, mask))
        b.write_fasta(cell / "D.fasta", record, masked)
        records.append({"id": row["id"], "masked_bp": int(mask.sum()), "seconds": time.monotonic()-tick})
        print(json.dumps(records[-1]), flush=True)
    dump(out / "D_mask.json", {"status": "COMPLETED", "records": records, "calibration": cal, "paths": paths, "load_seconds": load_seconds})


def native_smoke(species):
    out = BASE / species / "native_smoke"
    out.mkdir()
    record, sequence = next(b.fasta(BASE / species / "c00/U.fasta"))
    sequence = sequence[:100000]
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = "/opt/ebsofts/bzip2/1.0.8-GCCcore-12.2.0/lib:" + env.get("LD_LIBRARY_PATH", "")
    env["AUGUSTUS_CONFIG_PATH"] = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/config"
    binary = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/bin/augustus"
    results = {}
    for arm in ("uppercase", "lowercase_control"):
        content = sequence if arm == "uppercase" else sequence[:1000] + sequence[1000:1200].lower() + sequence[1200:]
        b.write_fasta(out / (arm + ".fa"), "native_mask_control", content)
        run([binary, "--species="+CFG["species"][species]["augustus_species"], "--gff3=on", "--softmasking=1", "--printHints=true", "--UTR=off", "--stopCodonExcludedFromCDS=false", "--alternatives-from-evidence=false", "--alternatives-from-sampling=false", str(out / (arm + ".fa"))], out, arm, env)
        lines = [line for line in (out / (arm + ".stdout")).read_text().splitlines() if "nonexonpart" in line]
        results[arm] = {"masked_bp": sum(v in "acgt" for v in content), "native_repeat_hint_lines": lines}
    if not results["lowercase_control"]["native_repeat_hint_lines"] or results["uppercase"]["native_repeat_hint_lines"]:
        raise ValueError("Native lowercase-to-repeat-hint observation not established; inspect smoke output")
    dump(out / "result.json", {"status": "PASS_NATIVE_LOWERCASE_HINT_MECHANISM", "scope": "100 kb engineering input control, not a scientific utility result", "observations": results})


def predict(species, index):
    out = BASE / species
    row = json.loads((out / "geometry.json").read_text())[index]
    cell = out / row["id"]
    core = b.Core(**{k:row[k] for k in ("chrom", "index", "start", "end", "halo_start", "halo_end")})
    if (cell / "status.json").exists():
        raise FileExistsError("Preserve previous native prediction cells")
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = "/opt/ebsofts/bzip2/1.0.8-GCCcore-12.2.0/lib:" + env.get("LD_LIBRARY_PATH", "")
    env["AUGUSTUS_CONFIG_PATH"] = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/config"
    binary = "/opt/ebsofts/AUGUSTUS/3.5.0-foss-2022b/bin/augustus"
    status = {"status": "RUNNING", "core": row, "species": species, "job_id": os.environ.get("SLURM_JOB_ID"), "arms": {}}
    dump(cell / "status.json", status)
    run([binary, "--version"], cell, "augustus_version", env)
    original = next(b.fasta(cell / "U.fasta"))[1]
    for arm in CFG["arms"]:
        record, sequence = next(b.fasta(cell / (arm + ".fasta")))
        if record != core.record_id or sequence.upper() != original:
            raise ValueError("Paired mask sequence identity failed")
        argv = [binary, "--species=" + CFG["species"][species]["augustus_species"], "--gff3=on", "--softmasking=1", "--UTR=off", "--stopCodonExcludedFromCDS=false", "--alternatives-from-evidence=false", "--alternatives-from-sampling=false", str(cell / (arm + ".fasta"))]
        command = run(argv, cell, arm, env)
        (cell / (arm + ".stdout")).rename(cell / (arm + ".gff3"))
        chains, _ = b.parse_predictions(cell / (arm + ".gff3"), core, "gff3")
        status["arms"][arm] = {**command, "masked_bp": sum(v in "acgt" for v in sequence), "same_uppercase_letters": True, "predicted_chains": len(chains)}
        dump(cell / "status.json", status)
    status["status"] = "COMPLETED"
    dump(cell / "status.json", status)
    print(json.dumps(status), flush=True)


def score(species):
    import numpy as np
    out = BASE / species
    refs = json.loads((out / "reference.json").read_text())
    units = {u["unit_id"]: u for u in refs["units"]}
    mapping = {(u["chrom"], u["strand"], tuple(map(tuple, iso["intervals"]))): uid for uid, u in units.items() for iso in u["isoforms"]}
    totals = {a: Counter() for a in CFG["arms"]}
    correct = {a: set() for a in CFG["arms"]}
    rows = []
    for row in json.loads((out / "geometry.json").read_text()):
        cell = out / row["id"]
        status = json.loads((cell / "status.json").read_text())
        if status["status"] != "COMPLETED" or set(status["arms"]) != set(CFG["arms"]):
            raise ValueError("Full paired denominator not complete")
        core = b.Core(**{k:row[k] for k in ("chrom", "index", "start", "end", "halo_start", "halo_end")})
        truth = {uid for uid, u in units.items() if u["owner"] == core.key}
        entry = {"id": row["id"], "chrom": core.chrom, "reference_loci": len(truth), "metrics": {}}
        for arm in CFG["arms"]:
            chains, _ = b.parse_predictions(cell / (arm + ".gff3"), core, "gff3")
            matched = {c for c in chains if (core.chrom, c.strand, c.intervals) in mapping}
            found = {mapping[(core.chrom, c.strand, c.intervals)] for c in matched}
            if not found <= truth:
                raise ValueError("Locus ownership mismatch")
            m = b.metrics(len(found), len(chains-matched), len(truth-found))
            totals[arm].update({k:m[k] for k in ("tp", "fp", "fn")})
            correct[arm].update(found)
            entry["metrics"][arm] = m
        rows.append(entry)
    metrics = {a:b.metrics(**v) for a, v in totals.items()}
    comparisons = {}
    for control in ("U", "R_TE", "RED"):
        rng = np.random.default_rng(42)
        values = []
        for _ in range(CFG["score"]["bootstrap"]["replicates"]):
            counts = {a:Counter() for a in ("D", control)}
            for i in rng.integers(0, len(rows), len(rows)):
                for a in counts:
                    counts[a].update({k:rows[i]["metrics"][a][k] for k in ("tp", "fp", "fn")})
            scores = {a:b.metrics(**v)["f1"] for a,v in counts.items()}
            values.append(scores["D"]-scores[control])
        comparisons["D_minus_" + control] = {"f1_delta": metrics["D"]["f1"]-metrics[control]["f1"], "ci95": np.quantile(values,[.025,.975]).tolist(), "gained_loci": sorted(correct["D"]-correct[control]), "lost_loci": sorted(correct[control]-correct["D"])}
    result = {"protocol": NAME, "status": "COMPLETED", "species": species, "reference_loci": len(units), "metrics": metrics, "comparisons": comparisons, "per_core": rows, "scope": CFG["scope"], "reference_exclusions": refs["excluded_transcript_rows"]}
    dump(out / "result.json", result)
    print(json.dumps({k:result[k] for k in ("species", "reference_loci", "metrics")}), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("prepare", "native-smoke", "d-mask", "predict", "score"))
    p.add_argument("species", choices=tuple(CFG["species"]))
    p.add_argument("--index", type=int)
    a = p.parse_args()
    if a.action == "prepare": prepare(a.species)
    elif a.action == "native-smoke": native_smoke(a.species)
    elif a.action == "d-mask": d_mask(a.species)
    elif a.action == "predict": predict(a.species, a.index)
    else: score(a.species)
