#!/usr/bin/env python3
"""Classify a failed run's log and propose a BOUNDED repair plan.

Lightweight port of Research OS REPAIR_AND_RESUBMIT. It does NOT auto-apply big
changes — it emits a single bounded repair suggestion that /pursue applies once
before re-submitting; if the same class fails twice, escalate to the human.

Reads the tail of a stderr/stdout log (or stdin) and emits JSON:
  {failure_class, bounded, action, patch_hint, confidence}

failure_class ∈ {oom, timeout, missing_dependency, nan_loss, cuda_device,
                 disk_full, data_error, unknown}
bounded=true means /pursue may auto-apply + resubmit once. unknown/cuda_device/
data_error are bounded=false → escalate to human.

Usage:
  python3 scripts/repair_advisor.py --log outputs/<exp>/logs/err.log
  tail -c 20000 err.log | python3 scripts/repair_advisor.py -
"""
import argparse, json, re, sys

# (regex, class, bounded, action, patch_hint)
RULES = [
    (r"CUDA out of memory|OutOfMemoryError|CUBLAS_STATUS_ALLOC_FAILED|RuntimeError: .*memory",
     "oom", True, "halve batch_size (and/or enable gradient checkpointing / grad accumulation)",
     "set --batch_size to floor(bs/2); if already small, add --gradient_checkpointing / increase --grad_accum_steps"),
    (r"DUE TO TIME LIMIT|slurmstepd:.*TIME LIMIT|CANCELLED AT.*DUE TO TIME|Job .* exceeded .* time",
     "timeout", True, "add checkpoint+resume and/or raise --time",
     "ensure --signal=B:USR1@600 + load_from_checkpoint; resubmit with larger --time within partition limit"),
    (r"ModuleNotFoundError: No module named '([\w\.\-]+)'|ImportError: .*cannot import name|No module named ([\w\.\-]+)",
     "missing_dependency", True, "pip install the missing module then resubmit",
     "pip install <module from the error> into the job env; pin version if known"),
    (r"loss.*(nan|inf)|Loss is NaN|nan loss|gradient.*(overflow|nan)|FloatingPointError",
     "nan_loss", True, "reduce lr and add gradient clipping",
     "set --learning_rate to lr/3; add --max_grad_norm 1.0; check fp16->bf16"),
    (r"CUDA error: device-side assert|no CUDA-capable device|NVIDIA driver.*version|CUDA_ERROR_NO_DEVICE|RuntimeError: CUDA error",
     "cuda_device", False, "infrastructure/device issue — escalate",
     "likely node/driver problem; do NOT blindly resubmit; report node + try --constraint or different partition"),
    (r"No space left on device|Disk quota exceeded|OSError: .*\[Errno 28\]",
     "disk_full", False, "disk full — escalate",
     "clean outputs/old checkpoints or change output_dir; needs human/quota action"),
    (r"FileNotFoundError|KeyError:|shape mismatch|size mismatch|expected .* got |dtype",
     "data_error", False, "data/shape/dtype error — escalate (likely code or data bug)",
     "inspect the offending tensor/file; this is a correctness bug, not a resource tweak"),
]


def classify(text):
    for pat, cls, bounded, action, hint in RULES:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            extra = ""
            if cls == "missing_dependency":
                mod = next((g for g in m.groups() if g), "")
                extra = f" (module: {mod})"
            return {"failure_class": cls, "bounded": bounded,
                    "action": action + extra, "patch_hint": hint,
                    "confidence": "high", "matched": m.group(0)[:120]}
    return {"failure_class": "unknown", "bounded": False,
            "action": "could not classify — escalate to human with the log tail",
            "patch_hint": "read the last 50 lines manually; do not auto-resubmit",
            "confidence": "low", "matched": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", default="-", help="log path or - for stdin")
    ap.add_argument("--log", dest="log_opt", default=None)
    args = ap.parse_args()
    src = args.log_opt or args.log
    if src in ("-", None):
        text = sys.stdin.read()
    else:
        try:
            with open(src, errors="replace") as f:
                text = f.read()[-40000:]  # tail
        except OSError as e:
            print(json.dumps({"failure_class": "unknown", "bounded": False,
                              "action": f"cannot read log: {e}"}, indent=2)); sys.exit(2)
    print(json.dumps(classify(text), indent=2))


if __name__ == "__main__":
    main()
