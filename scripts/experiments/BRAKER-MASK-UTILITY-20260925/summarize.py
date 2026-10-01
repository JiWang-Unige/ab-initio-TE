#!/usr/bin/env python3
"""Close the fixed six-arm comparison; retain compact evidence and old cores."""
from collections import Counter
import json
import os
from pathlib import Path
import re
import subprocess

import evaluation as e
from common import ROOT, OUT, dump


ARMS = ("D", "RM2_FULL", "RED_FULL")
SCORE_JOBS = {"chicken": "13323815", "zebrafish": "13323816"}
PREPARATION_JOBS = ("13194294", "13194295", "13194296", "13194304",
                    "13194313", "13194314", "13194346", "13194364", "13194397")
EARLIER_SCORE_JOBS = ("13233773", "13246903", "13290194", "13291916")


def accounting():
    ids = PREPARATION_JOBS + EARLIER_SCORE_JOBS + ("13194349",) + tuple(SCORE_JOBS.values())
    text = subprocess.check_output([
        "sacct", "-j", ",".join(ids), "--format=JobID,State,ExitCode,ElapsedRaw,AllocCPUS,Start,End,MaxRSS", "-P"
    ], text=True, env={**os.environ, "TZ": "UTC"})
    rows = [dict(zip(text.splitlines()[0].split("|"), line.split("|"))) for line in text.splitlines()[1:]]
    jobs = {}
    for row in rows:
        jid = row["JobID"]
        if "." in jid or jid == "13194349":
            continue
        batch = next((r for r in rows if r["JobID"] == jid + ".batch"), {})
        rss = batch.get("MaxRSS", "")
        jobs[jid] = {"job_id": jid, "state": row["State"], "exit_code": row["ExitCode"],
            "started_utc": row["Start"] + "Z", "ended_utc": row["End"] + "Z",
            "elapsed_seconds": int(row["ElapsedRaw"]), "allocated_cpus": int(row["AllocCPUS"]),
            "allocated_cpu_hours": int(row["ElapsedRaw"]) * int(row["AllocCPUS"]) / 3600,
            "batch_max_rss_kb": int(rss[:-1]) if rss.endswith("K") else None}
    return jobs


def compact(raw, source):
    result = {k: raw[k] for k in ("reference", "comparisons", "bootstrap", "primary_endpoint")}
    result["full_score_source"] = str(source)
    result["arms"] = {}
    for arm, row in raw["arms"].items():
        m = row["metrics"]
        assert m["tp"] + m["fn"] == raw["reference"]["gene_loci"]
        assert m == e.metric(m["tp"], m["fp"], m["fn"])
        assert {k: sum(v[k] for v in row["per_chromosome"].values()) for k in ("tp", "fp", "fn")} == {k: m[k] for k in ("tp", "fp", "fn")}
        chains = row["predicted_chains"]
        matched = sum(c["matched"] for c in chains)
        assert len(chains) == row["unique_cds_chains"] == row["complete_cds_feature_chains"] + row["partial_cds_feature_chains"]
        assert len(chains) - matched == m["fp"]
        result["arms"][arm] = {k: row[k] for k in ("metrics", "unique_cds_chains", "complete_cds_feature_chains", "partial_cds_feature_chains", "per_chromosome", "skipped")}
        result["arms"][arm].update(matched_chains=matched, multiple_matching_isoforms_beyond_one_per_locus=matched - m["tp"])
    for name, comparison in raw["comparisons"].items():
        right = name.removeprefix("D_minus_")
        assert len(comparison["gained_units"]) - len(comparison["lost_units"]) == raw["arms"]["D"]["metrics"]["tp"] - raw["arms"][right]["metrics"]["tp"]
    if "long_read" in raw:
        lr = raw["long_read"]
        result["long_read"] = {k: v for k, v in lr.items() if k != "arms"}
        result["long_read"]["arms"] = {}
        for arm, groups in lr["arms"].items():
            result["long_read"]["arms"][arm] = {}
            for name, values in groups.items():
                assert sum(v["observed"] for v in values["per_chromosome"].values()) == values["observed"]
                assert sum(v["recovered"] for v in values["per_chromosome"].values()) == values["recovered"] <= values["observed"]
                result["long_read"]["arms"][arm][name] = {k: v for k, v in values.items() if k != "recovered_structure_ids"}
        for name, groups in lr["comparisons"].items():
            right = name.removeprefix("D_minus_")
            for group, c in groups.items():
                assert len(c["gained_structure_ids"]) - len(c["lost_structure_ids"]) == lr["arms"]["D"][group]["recovered"] - lr["arms"][right][group]["recovered"]
    return result


def old_panel(species, full):
    """Reuse the original 10-core reference and its CDS-start ownership rule."""
    old = ROOT / "outputs/NONMAMMAL-GENE-UTILITY-20260918" / species
    report = json.loads((old / "reference.json").read_text())
    geometry = json.loads((old / "geometry.json").read_text())
    assert report["unit_count"] == {"chicken": 1064, "zebrafish": 984}[species]
    mapping = e.ref_mapping(report)
    results = {}
    for arm, data in full["arms"].items():
        selected = []
        for row in data["predicted_chains"]:
            if not any(g["chrom"] == row["chrom"] and g["start"] <= row["intervals"][0][0] < g["end"] and row["intervals"][-1][1] <= g["halo_end"] for g in geometry):
                continue
            key = (row["chrom"], row["strand"], tuple(tuple(v) for v in row["intervals"]))
            unit = mapping.get(key)
            selected.append({**row, "unit_id": unit, "matched": unit is not None})
        matched = sorted({r["unit_id"] for r in selected if r["matched"]})
        results[arm] = {"predicted_chains": selected, "matched_units": matched,
            "metrics": e.metric(len(matched), sum(not r["matched"] for r in selected), report["unit_count"] - len(matched))}
        results[arm]["per_chromosome"] = {k: dict(v) for k, v in e._per_chrom_counts(results[arm], report).items()}
    comparisons = {"D_minus_" + arm: e.bootstrap_difference(results, report, arm) for arm in ARMS[1:]}
    for c, comparison in comparisons.items():
        right = c.removeprefix("D_minus_")
        assert len(comparison["gained_units"]) - len(comparison["lost_units"]) == results["D"]["metrics"]["tp"] - results[right]["metrics"]["tp"]
    return {"domain": "old_panel", "reference_gene_loci": report["unit_count"],
        "reference_source": str(old / "reference.json"), "geometry_source": str(old / "geometry.json"),
        "ownership": "CDS first coordinate in original 5 Mb core; CDS last coordinate <= original halo_end, as in frozen pilot; BRAKER normalized codon-inclusive CDS chains",
        "bootstrap": {"seed": 42, "replicates": 10000, "unit": "chromosome regional sensitivity, not biological replication"},
        "arms": {a: {k: r[k] for k in ("metrics", "per_chromosome")} for a, r in results.items()},
        "comparisons": comparisons,
        "interpretation": "Previously exposed 10-core panel; descriptive overlap check of new whole-genome ETP predictions, not a new replicate or a reproduction of the old fixed AUGUSTUS predictor."}


def main():
    destination = OUT / "final-summary"
    if destination.exists():
        raise FileExistsError(destination)
    jobs = accounting()
    preparation = json.loads((OUT / "evaluation/preparation.json").read_text())
    summaries, native = {}, {}
    for species_index, species in enumerate(("chicken", "zebrafish")):
        evidence = []
        for arm_index, arm in enumerate(ARMS):
            path = OUT / species / "arms" / arm
            status = json.loads((path / "status.json").read_text())
            jid = "13194349_" + str(arm_index * 2 + species_index)
            job = jobs[jid]
            assert status["status"] == "PREDICTION_READY" and status["native"]["returncode"] == 0
            assert job["state"] == "COMPLETED" and job["exit_code"] == "0:0" and job["allocated_cpus"] == 16 and job["elapsed_seconds"] <= 72 * 3600
            argv = status["native"]["argv"]
            assert not any("skipOptimize" in a or "gm_max_intergenic" in a for a in argv)
            assert "--threads=16" in argv
            evidence.append({k: next(a for a in argv if a.startswith(k)) for k in ("--bam=", "--prot_seq=")})
            gtf = Path(status["final_gtf"])
            assert gtf.stat().st_size > 0 and "BRAKER RUN FINISHED" in (path / "run/braker.log").read_text()
            if arm == "RED_FULL":
                value = {k: v for k, v in status.items() if k != "input_sources"}
                text = (path / "braker.time").read_text()
                value.update(final_gtf_bytes=gtf.stat().st_size, native_run_finished_marker=True, slurm=job,
                    native_time={"user_seconds": float(re.search(r"User time \(seconds\): ([\d.]+)", text)[1]),
                        "system_seconds": float(re.search(r"System time \(seconds\): ([\d.]+)", text)[1]),
                        "max_rss_kb": int(re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)[1]),
                        "scope": "GNU time native child process tree; distinct from Slurm batch MaxRSS and allocated CPU-hours"})
                native[species] = value
        assert evidence[0] == evidence[1] == evidence[2]
        directory = Path(preparation["species"][species]["evaluation_dir"])
        previous = json.loads((ROOT / "reports" / e.NAME / (species + "-D-RM2_FULL-score-summary.json")).read_text())
        summary = {"protocol": e.NAME, "species": species, "arms": list(ARMS), "matrix_complete": True,
            "domains": {}, "score_job": jobs[SCORE_JOBS[species]], "replay_verified": True}
        assert summary["score_job"]["state"] == "COMPLETED" and summary["score_job"]["exit_code"] == "0:0"
        for domain in ("primary", "full"):
            source = directory / ("score-D-RM2_FULL-RED_FULL-" + domain + ".json")
            raw = json.loads(source.read_text())
            value = compact(raw, source)
            for arm in ARMS[:2]:
                assert value["arms"][arm] == previous["domains"][domain]["arms"][arm]
                if species == "zebrafish":
                    assert value["long_read"]["arms"][arm] == previous["domains"][domain]["long_read"]["arms"][arm]
            assert value["comparisons"]["D_minus_RM2_FULL"] == previous["domains"][domain]["comparisons"]["D_minus_RM2_FULL"]
            if species == "zebrafish":
                assert value["long_read"]["comparisons"]["D_minus_RM2_FULL"] == previous["domains"][domain]["long_read"]["comparisons"]["D_minus_RM2_FULL"]
            summary["domains"][domain] = value
            if domain == "full":
                summary["old_panel"] = old_panel(species, raw)
        summaries[species] = summary
    costs = {"protocol": e.NAME, "scope": "registered jobs in this complete BRAKER protocol; old experiments and prior shared container preflight remain separately reported",
        "jobs": jobs, "etp_allocated_cpu_hours": sum(jobs["13194349_" + str(i)]["allocated_cpu_hours"] for i in range(6)),
        "preparation_allocated_cpu_hours_including_failed_preparation": sum(jobs[j]["allocated_cpu_hours"] for j in PREPARATION_JOBS),
        "scoring_allocated_cpu_hours_before_this_summary": sum(jobs[j]["allocated_cpu_hours"] for j in EARLIER_SCORE_JOBS + tuple(SCORE_JOBS.values())),
        "summary_job_id": os.environ.get("SLURM_JOB_ID")}
    destination.mkdir()
    for species in summaries:
        dump(destination / (species + "-RED_FULL-prediction-summary.json"), native[species])
        dump(destination / (species + "-three-arm-score-summary.json"), summaries[species])
        print(json.dumps({"species": species, "metrics": {d: {a: x["metrics"] for a, x in v["arms"].items()} for d, v in summaries[species]["domains"].items()}, "old_panel": {a: r["metrics"] for a, r in summaries[species]["old_panel"]["arms"].items()}}))
    dump(destination / "cost-summary.json", costs)
    print(json.dumps({k: v for k, v in costs.items() if k != "jobs"}))


if __name__ == "__main__":
    main()
