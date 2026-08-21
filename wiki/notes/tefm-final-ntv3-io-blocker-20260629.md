# TEFM final NTv3 access and BeeGFS blocker note - 2026-06-29

NTv3 access blocker for the final model-size/window supplement has changed.
HuggingFace auth and remote code now work for the requested NTv3 variants, and
`InstaDeepAI/NTv3_8M_pre` completes a 512 bp `AutoModelForMaskedLM` forward pass
in the `te_benchmark` environment.

The current blocker is BeeGFS content-read failure (`Errno 121`) affecting key
project files including the final pipeline config, `make_jobs.py`,
`te_token_task.py`, the sbatch template, `docs/11_master_plan.md`, and
`human_h0_w2048/train/data.jsonl.gz`.

No NTv3 training was submitted while the training chain is unreadable. The
fallback council verdict is to submit only an isolated, fully checksummed,
screen-only NTv3 runner before shared pipeline recovery; otherwise wait for
BeeGFS recovery and rerun the standard gate.
