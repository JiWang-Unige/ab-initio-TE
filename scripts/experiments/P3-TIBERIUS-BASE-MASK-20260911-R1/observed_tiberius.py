#!/usr/bin/env python3
"""Record genuine Tiberius softmask encoding without changing inference."""
import json
import os
from pathlib import Path
import runpy
import sys

import numpy as np
from bricks2marble.struct.fasta import Fasta

TARGET = Path(os.environ["BASE_MASK_OBSERVATION"])
original = Fasta.one_hot
audit = {"calls": 0, "passed": True, "masked_positions": 0, "positions": 0,
         "semantics": "first five tracks ACGTN; sixth track lowercase acgt"}


def observed(self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    nuc = self.nuc
    if result.shape != (*nuc.shape, 6):
        raise ValueError("inference did not use six-channel softmask input")
    mask = nuc > 4
    base = np.where(mask, nuc-5, np.where(nuc == -1, 4, nuc))
    for index in range(5):
        if not np.array_equal(result[..., index], base == index):
            raise ValueError("inference base channel differs from FASTA input")
    if not np.array_equal(result[..., 5], mask):
        raise ValueError("inference softmask channel differs from FASTA input")
    audit["calls"] += 1
    audit["positions"] += int(nuc.size)
    audit["masked_positions"] += int(mask.sum())
    return result


Fasta.one_hot = observed
sys.path.insert(0, "/opt/Tiberius")
sys.argv[0] = "/opt/Tiberius/tiberius.py"
try:
    runpy.run_path("/opt/Tiberius/tiberius.py", run_name="__main__")
except BaseException as error:
    if not isinstance(error, SystemExit) or error.code not in (0, None):
        audit["passed"] = False
        audit["error"] = repr(error)
    raise
finally:
    with TARGET.open("x") as handle:
        json.dump(audit, handle, indent=2)
        handle.write("\n")
    Fasta.one_hot = original
