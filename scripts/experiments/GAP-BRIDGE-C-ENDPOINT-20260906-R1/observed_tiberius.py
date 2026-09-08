#!/usr/bin/env python3
"""Observe actual inference one_hot calls without changing arguments or return."""
import json
import os
from pathlib import Path
import runpy
import sys
import numpy as np
from bricks2marble.struct.fasta import Fasta

original = Fasta.one_hot
audit = {"calls": 0, "passed": True, "masked_positions": 0, "positions": 0,
         "semantics": "first five tracks ACGTN; sixth lowercase acgt; padding N"}

def observed(self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    nuc = self.nuc
    # Library's input encoding is ACGTNacgt=0..8; padding is -1.
    if result.shape != (*nuc.shape, 6):
        raise ValueError("inference must preserve six-track softmask input")
    mask = nuc > 4
    base = np.where(mask, nuc-5, np.where(nuc == -1, 4, nuc))
    for i in range(5):
        if not np.array_equal(result[..., i], base == i):
            raise ValueError("inference first five tracks do not match uppercase bases")
    if not np.array_equal(result[..., 5], mask):
        raise ValueError("inference sixth track lost softmask")
    audit["calls"] += 1
    audit["positions"] += int(nuc.size)
    audit["masked_positions"] += int(mask.sum())
    return result

def main():
    target = Path(os.environ["C_ENDPOINT_OBSERVATION"])
    Fasta.one_hot = observed
    sys.path.insert(0, "/opt/Tiberius")
    sys.argv[0] = "/opt/Tiberius/tiberius.py"
    try:
        runpy.run_path("/opt/Tiberius/tiberius.py", run_name="__main__")
    except BaseException as exc:
        if not isinstance(exc, SystemExit) or exc.code not in (0, None):
            audit["passed"] = False
            audit["error"] = repr(exc)
        raise
    finally:
        with target.open("x") as handle:
            json.dump(audit, handle, indent=2)
        Fasta.one_hot = original

if __name__ == "__main__":
    main()
