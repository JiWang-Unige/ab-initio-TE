#!/usr/bin/env python3
"""Small same-container checks for the chicken EDTA recovery patch.

This file is executed inside the pinned EDTA container.  It deliberately uses
the container's pandas, swifter, Dask, and Biopython versions rather than the
host environment.  The fixture has no genome-scale work and does not read
benchmark labels.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import multiprocessing as mp
from pathlib import Path
import sys
import traceback


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def invoke_get_fasta(module_name: str, df, record):
    module = sys.modules[module_name]
    return module.get_fasta_pieces_single_seqid_SeqIO(df, record, "chr1", False)


def run_in_pool(module_name: str, df, record):
    # The production failure is specifically nested multiprocessing: this
    # outer Pool creates daemon workers, then swifter's process scheduler tries
    # to create a second child process inside one of them.
    context = mp.get_context("fork")
    with context.Pool(1) as pool:
        return pool.starmap(invoke_get_fasta, [(module_name, df, record)])[0]


def exception_record(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc),
            "traceback_tail": "\n".join(traceback.format_exc().splitlines()[-8:])}


def patch_get_fasta(source: str) -> str:
    old = '''    df["seq"] = df.swifter.progress_bar(flag_verbose).apply(
        lambda x: str(genome_SeqRecord.seq[x["start"]: x["end"]]), axis=1)'''
    new = '''    df["seq"] = df.apply(
        lambda x: str(genome_SeqRecord.seq[x["start"]: x["end"]]), axis=1)'''
    if source.count(old) != 1:
        raise RuntimeError("get_fasta_sequence.py source marker is not unique")
    return source.replace(old, new, 1)


def patch_check(source: str) -> str:
    if source.count("family = x[0]") != 2:
        raise RuntimeError("check_TIR_TSD.py pandas markers are not unique")
    return source.replace("family = x[0]", 'family = x["TIR_type"]')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)

    # const.py is the only import dependency needed by the two extracted
    # modules.  It mirrors the image's imports while keeping the fixture
    # independent of the large TIR-Learner model files.
    const = out / "const.py"
    const.write_text(
        "import multiprocessing as mp\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import re\n"
        "import swifter\n"
        "from Bio import SeqIO\n"
        "from Bio.Seq import Seq\n"
        "TSD = {'DTA': [8], 'DTC': [3, 2], 'DTH': [3], 'DTM': [10, 9, 8, 7], 'DTT': [2]}\n",
        encoding="utf-8",
    )

    source_dir = Path("/usr/local/share/TIR-Learner3.0/bin")
    original_get_source = (source_dir / "get_fasta_sequence.py").read_text(encoding="utf-8")
    original_check_source = (source_dir / "check_TIR_TSD.py").read_text(encoding="utf-8")
    patched_get_source = patch_get_fasta(original_get_source)
    patched_check_source = patch_check(original_check_source)
    original_get = out / "original_get_fasta_sequence.py"
    patched_get = out / "patched_get_fasta_sequence.py"
    original_check = out / "original_check_TIR_TSD.py"
    patched_check = out / "patched_check_TIR_TSD.py"
    original_get.write_text(original_get_source, encoding="utf-8")
    patched_get.write_text(patched_get_source, encoding="utf-8")
    original_check.write_text(original_check_source, encoding="utf-8")
    patched_check.write_text(patched_check_source, encoding="utf-8")
    for path in (original_get, patched_get, original_check, patched_check):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")

    sys.path.insert(0, str(out))
    import numpy as np
    import pandas as pd
    import swifter
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord

    original_get_module = load_module(original_get, "original_get_fasta_sequence")
    patched_get_module = load_module(patched_get, "patched_get_fasta_sequence")
    original_check_module = load_module(original_check, "original_check_TIR_TSD")
    patched_check_module = load_module(patched_check, "patched_check_TIR_TSD")

    n = 8
    df = pd.DataFrame({
        "TIR_type": pd.Series(["DTA"] * n, dtype="string"),
        "id": pd.Series([f"chr1:{i * 20}:{i * 20 + 12}" for i in range(n)], dtype="string"),
        "seqid": pd.Series(["chr1"] * n, dtype="string"),
        "start": np.arange(n, dtype=np.int64) * 20,
        "end": np.arange(n, dtype=np.int64) * 20 + 12,
    })
    record = SeqRecord(Seq("ACGT" * 100), id="chr1")
    scalar_lambda = lambda x: str(record.seq[x["start"]: x["end"]])

    results = {
        "runtime": {
            "python": sys.version,
            "pandas": pd.__version__,
            "swifter": getattr(swifter, "__version__", "unknown"),
            "numpy": np.__version__,
        },
        "input": {
            "rows": n,
            "dtypes": {key: str(value) for key, value in df.dtypes.items()},
            "coordinate_values_are_integer": bool(
                np.issubdtype(df["start"].dtype, np.integer)
                and np.issubdtype(df["end"].dtype, np.integer)
            ),
        },
    }

    # This is the exact operation swifter first probes to decide whether the
    # row function vectorizes.  A DataFrame slice is intentionally invalid;
    # the important question is whether the scalar pandas.apply succeeds.
    try:
        scalar_lambda(df)
        results["swifter_vectorization_probe"] = {"status": "unexpected_success"}
    except Exception as exc:
        results["swifter_vectorization_probe"] = exception_record(exc)
    scalar = df.apply(scalar_lambda, axis=1)
    results["scalar_pandas_apply"] = {
        "status": "PASS",
        "dtype": str(scalar.dtype),
        "values": scalar.tolist(),
    }

    # Force the same swifter Dask branch in a tiny fixture.  The production
    # default is scheduler=processes; dask_threshold=-1,
    # allow_dask_on_strings=True, and force_parallel=True make this branch
    # deterministic in a short
    # fixture.  The latter is a diagnostic switch only and does not alter the
    # recovery; the native genome run already recorded the daemon failure.
    swifter.set_defaults(scheduler="processes", dask_threshold=-1,
                         allow_dask_on_strings=True, force_parallel=True)
    try:
        run_in_pool("original_get_fasta_sequence", df, record)
        results["original_nested_pool"] = {"status": "unexpected_success"}
    except Exception as exc:
        results["original_nested_pool"] = {"status": "expected_failure", **exception_record(exc)}

    patched_result = run_in_pool("patched_get_fasta_sequence", df, record)
    patched_values = patched_result["seq"].tolist()
    results["patched_nested_pool"] = {
        "status": "PASS" if patched_values == scalar.tolist() else "FAIL",
        "values": patched_values,
        "matches_scalar_pandas_apply": patched_values == scalar.tolist(),
        "dtype": str(patched_result["seq"].dtype),
    }

    # pandas 3 also changes Series integer indexing.  The recovered TIR
    # checkpoint names the family column TIR_type, so the named-column patch
    # is checked independently before any genome-scale stage is resumed.
    check_row = pd.Series({"TIR_type": "DTA", "seq": "A" * 1000})
    try:
        original_check_module.check_TIR(check_row)
        results["original_check_TIR_family_access"] = {"status": "unexpected_success"}
    except Exception as exc:
        results["original_check_TIR_family_access"] = {"status": "expected_failure", **exception_record(exc)}
    try:
        patched_check_module.check_TIR(check_row)
        results["patched_check_TIR_family_access"] = {"status": "PASS"}
    except Exception as exc:
        results["patched_check_TIR_family_access"] = {"status": "FAIL", **exception_record(exc)}

    results["patch_scope"] = {
        "get_fasta": "nested-pool swifter apply -> pandas apply(axis=1); no coordinate cast",
        "check_TIR_TSD": 'family=x[0] -> family=x["TIR_type"] at two call sites',
    }
    (out / "fixture-result.json").write_text(
        json.dumps(results, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(results, indent=2, allow_nan=False), flush=True)
    if results["patched_nested_pool"]["status"] != "PASS":
        return 2
    if results["patched_check_TIR_family_access"]["status"] != "PASS":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
