#!/usr/bin/env python3
"""Finalize existing de novo benchmark outputs into standardized root artifacts."""

from __future__ import annotations

import argparse
import gzip
import json
import os
from pathlib import Path
import shutil


TOOLS = ("repeatmodeler", "edta", "repeatscout", "earlgrey")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text)
    tmp.replace(path)


def find_first(paths: list[Path]) -> Path | None:
    existing = [path for path in paths if path.exists() and path.stat().st_size > 0]
    return existing[0] if existing else None


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", errors="ignore")
    return path.open("rt", errors="ignore")


def load_id_mapping(path: Path | None) -> dict[str, str]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def escape_attr(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace(";", "%3B")
        .replace("=", "%3D")
        .replace("&", "%26")
        .replace(",", "%2C")
        .replace("\t", " ")
        .replace("\n", " ")
    )


def iter_repeatmasker_records(path: Path, id_mapping: dict[str, str] | None = None):
    mapping = id_mapping or {}
    with open_text(path) as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) < 11 or not parts[0].isdigit():
                continue
            seqid = mapping.get(parts[4], parts[4])
            start_1 = int(parts[5])
            end_1 = int(parts[6])
            if end_1 < start_1:
                continue
            strand = "-" if parts[8] == "C" else "+"
            yield {
                "score": parts[0],
                "div": parts[1],
                "dele": parts[2],
                "ins": parts[3],
                "seqid": seqid,
                "start_1": start_1,
                "end_1": end_1,
                "start_0": start_1 - 1,
                "end_0": end_1,
                "repeat_name": parts[9],
                "class_family": parts[10],
                "strand": strand,
                "repeat_id": parts[14] if len(parts) > 14 else "",
            }


def write_gff3_from_repeatmasker(
    src: Path,
    dst: Path,
    source_name: str,
    id_mapping: dict[str, str] | None = None,
) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    with tmp.open("w") as out:
        out.write("##gff-version 3\n")
        for idx, rec in enumerate(iter_repeatmasker_records(src, id_mapping=id_mapping), start=1):
            attrs = [
                f"ID={source_name}_{idx}",
                f"Name={escape_attr(rec['repeat_name'])}",
                f"ClassFamily={escape_attr(rec['class_family'])}",
                f"RepeatMaskerScore={rec['score']}",
                f"RepeatMaskerDiv={rec['div']}",
                f"RepeatMaskerDel={rec['dele']}",
                f"RepeatMaskerIns={rec['ins']}",
            ]
            if rec["repeat_id"]:
                attrs.append(f"RepeatMaskerID={escape_attr(rec['repeat_id'])}")
            out.write(
                "\t".join(
                    [
                        rec["seqid"],
                        source_name,
                        "repeat_region",
                        str(rec["start_1"]),
                        str(rec["end_1"]),
                        rec["score"],
                        rec["strand"],
                        ".",
                        ";".join(attrs),
                    ]
                )
                + "\n"
            )
    tmp.replace(dst)
    return dst


def write_bed_from_repeatmasker(
    src: Path,
    dst: Path,
    id_mapping: dict[str, str] | None = None,
) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    with tmp.open("w") as out:
        for rec in iter_repeatmasker_records(src, id_mapping=id_mapping):
            out.write(
                "\t".join(
                    [
                        rec["seqid"],
                        str(rec["start_0"]),
                        str(rec["end_0"]),
                        rec["repeat_name"],
                        rec["score"],
                        rec["strand"],
                    ]
                )
                + "\n"
            )
    tmp.replace(dst)
    return dst


def count_gff_features(path: Path) -> int:
    count = 0
    with path.open() as handle:
        for line in handle:
            if line.strip() and not line.startswith("#"):
                count += 1
    return count


def materialize(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    tmp = dst.with_name(dst.name + ".tmp")
    if tmp.exists():
        tmp.unlink()
    try:
        os.link(src, tmp)
    except OSError:
        shutil.copy2(src, tmp)
    tmp.replace(dst)
    return dst


def discover_repeatmodeler(outdir: Path) -> tuple[Path | None, str, Path | None]:
    rm_dir = outdir / "repeatmodeler_output"
    mask_dir = outdir / "repeatmasker_output"
    lib = find_first(
        list(rm_dir.glob("RM_*/consensi.fa.classified"))
        + list(rm_dir.glob("RM_*/consensi.fa"))
        + [outdir / "database" / "genome_db-families.fa"]
    )
    gff = find_first(list(mask_dir.rglob("*.out.gff")))
    if gff:
        return gff, "gff", lib
    rm_out = find_first(list(mask_dir.rglob("*.out")) + list(mask_dir.rglob("*.cat.gz")) + list(mask_dir.rglob("*.cat.all.gz")))
    return rm_out, "repeatmasker_out", lib


def discover_edta(outdir: Path) -> tuple[Path | None, str, Path | None, dict[str, str]]:
    edta_dir = outdir / "edta_output"
    id_mapping = load_id_mapping(edta_dir / "id_mapping.json")
    lib = find_first(
        list(edta_dir.rglob("*.EDTA.TElib.fa"))
        + list(edta_dir.rglob("*.LTR.TIR.Helitron.others.fa.stg2.clean"))
        + list(edta_dir.rglob("*.LTR.TIR.Helitron.fa.stg1"))
        + list(edta_dir.rglob("*.RM.consensi.fa.rexdb.cls.lib"))
    )
    gff = find_first(list(edta_dir.rglob("*.EDTA.TEanno.gff3")))
    if gff:
        return gff, "gff", lib, id_mapping
    rm_out = find_first(
        list(edta_dir.rglob("*.mod.out"))
        + list(edta_dir.rglob("*.mod.cat.gz"))
        + list(edta_dir.rglob("*.mod.cat.all.gz"))
    )
    return rm_out, "repeatmasker_out", lib, id_mapping


def discover_earlgrey(outdir: Path, species: str) -> tuple[Path | None, str, Path | None, Path | None]:
    root = outdir / "work" / "output" / f"{species}_EarlGrey"
    summary = root / f"{species}_summaryFiles"
    gff = find_first(
        [
            summary / f"{species}.filteredRepeats.gff",
            root / f"{species}_mergedRepeats" / "looseMerge" / f"{species}.filteredRepeats.gff",
            root / f"{species}_mergedRepeats" / f"{species}.filteredRepeats.gff",
        ]
    )
    bed = find_first(
        [
            summary / f"{species}.filteredRepeats.bed",
            root / f"{species}_mergedRepeats" / "looseMerge" / f"{species}.filteredRepeats.bed",
            root / f"{species}_mergedRepeats" / f"{species}.filteredRepeats.bed",
        ]
    )
    lib = find_first(sorted(root.glob(f"{species}_summaryFiles/*.fa*")) + sorted(root.glob(f"{species}_strainer/*.strained")))
    if gff and bed and lib:
        return gff, "gff", bed, lib
    rm_out = find_first(
        list(root.glob(f"{species}_RepeatMasker_Against_Custom_Library/*.out"))
        + list(root.glob(f"{species}_RepeatMasker_Against_Custom_Library/*.cat.gz"))
    )
    return rm_out, "repeatmasker_out", None, lib


def load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}


def finalize_dir(species: str, tool: str, outdir: Path) -> tuple[str, str]:
    status_path = outdir / "status.json"
    done = outdir / "DONE"
    failed = outdir / "FAILED"
    status = load_status(status_path)

    if tool == "repeatscout":
        ann = outdir / "annotation.gff3"
        lib = outdir / "library.fasta"
        if done.exists() and ann.exists() and ann.stat().st_size > 0 and lib.exists() and lib.stat().st_size > 0:
            return "already_ok", "repeatscout already standardized"
        return "skip", "repeatscout missing complete root outputs"

    if tool == "repeatmodeler":
        src_ann, ann_kind, src_lib = discover_repeatmodeler(outdir)
    elif tool == "edta":
        src_ann, ann_kind, src_lib, id_mapping = discover_edta(outdir)
    elif tool == "earlgrey":
        src_ann, ann_kind, bed, src_lib = discover_earlgrey(outdir, species)
        if not src_ann or not src_lib:
            return "incomplete", "earlgrey missing gff/bed/library"
        if ann_kind == "gff":
            if not bed:
                return "incomplete", "earlgrey missing gff/bed/library"
            materialize(bed, outdir / "annotation.bed")
            status["bed_path"] = str(bed)
            status["standardized_bed_path"] = str(outdir / "annotation.bed")
        else:
            std_bed = write_bed_from_repeatmasker(src_ann, outdir / "annotation.bed")
            status["bed_path"] = str(src_ann)
            status["standardized_bed_path"] = str(std_bed)
    else:
        return "skip", f"unsupported tool {tool}"

    if tool == "edta":
        mapping = id_mapping
    else:
        mapping = {}

    if not src_ann or not src_lib:
        return "incomplete", f"{tool} missing gff/library"

    if ann_kind == "gff":
        if tool == "edta" and mapping:
            std_gff = write_gff3_from_repeatmasker(src_ann, outdir / "annotation.gff3", source_name=tool, id_mapping=mapping) if src_ann.suffix == ".out" else None
            if std_gff is None:
                std_gff = materialize(src_ann, outdir / "annotation.gff3")
        else:
            std_gff = materialize(src_ann, outdir / "annotation.gff3")
    else:
        std_gff = write_gff3_from_repeatmasker(src_ann, outdir / "annotation.gff3", source_name=tool, id_mapping=mapping)
    std_lib = materialize(src_lib, outdir / "library.fasta")
    feature_count = count_gff_features(std_gff)
    if feature_count == 0:
        return "incomplete", f"{tool} produced empty standardized gff"

    status.update(
        {
            "species": species,
            "tool": tool,
            "status": "success",
            "error_message": None,
            "annotation_source_path": str(src_ann),
            "annotation_source_kind": ann_kind,
            "gff3_path": str(std_gff),
            "library_path": str(std_lib),
            "gff3_bytes": std_gff.stat().st_size,
            "gff3_feature_count": feature_count,
            "library_bytes": std_lib.stat().st_size,
            "raw_output_dir": str(outdir),
        }
    )
    if tool == "earlgrey":
        status["standardized_gff3_path"] = str(std_gff)
        status["standardized_library_path"] = str(std_lib)

    atomic_write_text(status_path, json.dumps(status, indent=2, sort_keys=True) + "\n")
    if failed.exists():
        failed.unlink()
    atomic_write_text(done, "OK\n")
    return "finalized", f"{tool} standardized"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    raw_root = run_root / "raw_outputs"
    if not raw_root.exists():
        raise SystemExit(f"missing raw_outputs: {raw_root}")

    summary: list[tuple[str, str, str, str]] = []
    for spdir in sorted(p for p in raw_root.iterdir() if p.is_dir() and not p.name.startswith("_")):
        for tool in TOOLS:
            outdir = spdir / tool
            if not outdir.exists():
                summary.append((spdir.name, tool, "missing_dir", "directory absent"))
                continue
            action, note = finalize_dir(spdir.name, tool, outdir)
            summary.append((spdir.name, tool, action, note))

    for row in summary:
        print("\t".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
