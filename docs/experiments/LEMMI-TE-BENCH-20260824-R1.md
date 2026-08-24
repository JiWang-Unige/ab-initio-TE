# LEMMI-TE-BENCH-20260824-R1

## Scope and finding

LEMMI is the EZlab continuous benchmarking framework for metagenomics
classifiers, not a transposable-element caller or a TE truth generator. This
cell adopts only its useful benchmark discipline: a frozen instance, explicit
tool-cell status, and provenance. The official LEMMI documentation is linked in
`configs/LEMMI-TE-BENCH-20260824-R1.yaml`.

The repository contains reusable engineering-smoke material for RepeatModeler2
2.0.9 + RepeatMasker 4.2.4, EDTA 2.3.0, HiTE 3.3.3, EarlGrey 7.3.0 and
TEtrimmer 1.7.4. Those outputs validate runtime identity and conversion only;
they are not predictions on the frozen FlyBase instance. Existing EDTA rice
reference output is explicitly not used as independent truth for an EDTA cell.

The remote checkout also contains reusable BED/GFF payloads under
`software_outputs/de_novo_benchmark/DENOVO_B_ANIMAL_EVAL_20260620/` (for
example pig RepeatModeler/EDTA and cattle EarlGrey). They are recorded in the
config as audit-only candidates: they are Dfam-augmented, use different
assemblies/species, and therefore cannot be silently promoted into this frozen
FlyBase comparison.

## Implemented

`adapter.py` accepts BED, GFF3 and RepeatMasker `.out`, emits the canonical
zero-based half-open TSV consumed by the FM strict evaluator, and computes
matching bp, segment IoU/F1, boundary and fragmentation fields. It uses the
same IoU/boundary defaults (`0.8`, `5 bp`) as the strict screen and has a
deterministic synthetic smoke fixture. The CLI has explicit `convert`,
`evaluate`, and `self-test` subcommands. Flat strict masks use interval union
by default while reporting raw interval, overlap-pair, and union-run counts;
`require_nonoverlap` is available for an instance/topology track.

For T1 positive-only truth, the evaluator sets whole-genome FP, TN,
precision/F1, and true-backed prediction rates to `null`; it retains positive
coverage/recall, matched boundary recall/error, and fragments-per-truth. It
never treats unlabeled sequence as negative.

## Current status / blockers

The config freezes FlyBase FB2026_02 D. melanogaster r6.68 as independent T1
curated-positive truth and a genome-level holdout split. It deliberately marks
all five tool cells `BLOCKED`: no frozen FlyBase-cell BED/GFF output and no
locally verified contig-length manifest are present in this checkout. No
caller, Slurm job, or biological benchmark was run here; the engineering
smoke is claim-ineligible.

The FlyBase truth manifest also records overlapping instances (812 intervals
participate in an overlap). The default flat-union track preserves this in
audit counts; an instance/topology track must explicitly use
`require_nonoverlap` or a topology-aware evaluator amendment.

Required before a real cell: verify assembly/truth bytes and contig lengths,
register one output artifact per tool with its tool/database provenance, and
run the common evaluator against this same truth/split. Self-Dfam truth and
same-run homologous-caller output must never be compared as independent
evidence.

## CPU preflight and next cell

`sbatch/LEMMI-TE-BENCH-20260824-preflight.sbatch` is a CPU-only, no-caller
preflight. It requires a numeric `SLURM_JOB_ID`, creates a unique
`attempt-$SLURM_JOB_ID`, verifies the frozen assembly/truth SHA-256 values,
streams the gzip FASTA into contig-length TSV/JSON, converts the FlyBase BED,
audits raw/overlap/union counts, and writes a manifest plus terminal `STATUS`.
Resource flags are supplied externally through `sbatch`; this worker only ran
`bash -n` and did not submit it.

`sbatch/LEMMI-TE-BENCH-20260824-hite-claim-screen.sbatch` is the dependent
same-instance cell. It requires `PREFLIGHT_ATTEMPT` pointing to a PASS
preflight, revalidates the preflight manifest identity, streams the frozen
assembly into `/work/input/hite.fa`, runs the exact direct HiTE argv with the
known loopback-discard proxy policy, requires exactly one non-empty
`HiTE.gff`, then writes canonical output and `metrics.json` from the preflight
contig lengths/truth. It records `claim_eligible=false`; T1 positive-only
metrics never treat Dfam or unlabelled sequence as truth/negative.
The runner also repeats the exact `main.py -h`/version-3.3.3 identity gate
before the long minimum command.

On a successful cell, the per-run metrics/manifest set
`claim_eligible=true` only for the declared
`T1_positive_only_recall_boundary_fragmentation` scope; whole-genome
precision/F1 remains explicitly non-claimable. The thread count is read from
numeric `SLURM_CPUS_PER_TASK` and passed through to HiTE, so the 40-CPU
recommendation is not silently reduced to the earlier 2-thread smoke setting.
The D. melanogaster cell also passes `--plant 0`; HiTE's plant default is not
valid for this animal genome.

The most executable same-instance caller cell within a 12-hour window is
HiTE 3.3.3: the exact 3.6-GB SIF, source commit, direct argv, and output GFF
contract are already hash-verified, and the prior isolated demo completed in
about 22 minutes on 4 CPU/48 GiB. The D. melanogaster assembly is 145.9 Mb
uncompressed. A conservative proposed cell is 40 CPU/128 GiB/0 GPU with a
12-hour cap, writing `HiTE.gff` and then using the T1 evaluator. RepeatModeler2
+ RepeatMasker is less executable in this window because it requires the
multi-step BuildDatabase/RepeatModeler/RepeatMasker chain plus Dfam/FamDB
configuration; its existing outputs remain audit-only.

Read-only remote audit found Apptainer 1.4.5, the exact HiTE SIF and manifest
under `software_outputs/tefm_new_directions/BENCH-5TOOL-DENOMINATOR-CLOSURE-20260811-R2/hite/`,
and RM2/RM SIFs plus a Dfam 4.0 FamDB manifest. The existing HiTE runner uses
direct `python /HiTE/main.py` argv with isolated `/work`, loopback-discard
proxies, and no network; the existing RM runner adds BuildDatabase and a
RepeatModeler minimum before RepeatMasker. No caller command was executed in
this task.
