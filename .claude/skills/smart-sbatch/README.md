# smart-sbatch

LWCR Claude Skill for Teodoro Slurm sbatch submission planning. Acts as the policy guard + routing layer between `/goal-prompt` and a live sbatch submission.

## Key behavior

- **CPU-only fast path** — CPU commands route to `private-teodoro-gpu` with 0 GPUs.
- **Large-model VRAM filter** — Default ≥20GB; RTX 3080 nodes (`gpu023,gpu024,gpu036-gpu043`) excluded by default.
- **Private vs shared routing** — Prefer free `private-teodoro-gpu` (7-day), but switch to `shared-gpu` (12-hour) when queue delay, low GPU count, or checkpointability make shared faster.
- **Maintenance-aware walltime** — Never hardcodes 7 days; reduces `--time` when maintenance reservations cut the window.
- **Phase 1 / Phase 2 hard split** — Policy guard is non-negotiable; optimization only runs if guard passes.
- **Mode A / Mode B** — Generate new sbatch OR review an existing script without rewriting.
- **Track A orthogonality** — Parallel architecture batches must declare structural axes; hyperparameter-only sweeps are hard-failed.

## Files

```
smart-sbatch/
├── SKILL.md                              # main skill prompt
├── README.md                             # this file
├── references/
│   ├── cluster_inventory.md              # gpu017-gpu050 nodes, VRAM, default-exclude list
│   ├── decision_policy.md                # detailed routing policy (CPU / GPU / maintenance / checkpointing)
│   ├── diagnostics_commands.md           # sinfo / squeue / scontrol / sacct templates
│   ├── sbatch_templates.md               # 5 sbatch starter templates with USR1 trap
│   └── cluster_config_schema.md          # cluster_config.yaml 4-section schema
├── scripts/
│   └── choose_partition.py               # deterministic Python helper (advisory)
├── examples/
│   └── scenarios.md                      # 6 worked scenarios
└── evals/
    └── test_cases.md                     # skill behavior evals
```

## Integration with lwcr

This skill is invoked from `/goal-prompt`'s `## 运行说明` fixed block. Both Phase 1 and the orthogonality check are mandatory before any sbatch submission. After submission, hand off to `/result-log` once the job completes; if running in submit-and-handoff mode, kick off the *While-waiting Scout plan* described in `/goal-prompt`.

## Provenance

The `references/`, `scripts/`, `examples/`, and `evals/` content originated from the standalone `teodoro-slurm-job-routing` Claude Skill (v1, 2026-05-18) and was merged into `smart-sbatch` on 2026-05-18 to preserve the lwcr Phase 1/2 guard, Mode A/B split, Track A orthogonality check, and `/goal-prompt`/`/result-log` hand-offs while gaining the Teodoro-specific cluster knowledge, CPU-only fast path, and deterministic helper.
