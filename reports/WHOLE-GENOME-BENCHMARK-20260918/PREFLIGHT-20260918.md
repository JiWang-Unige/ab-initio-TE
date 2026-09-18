# Whole-genome benchmark preflight

Protocol: `WHOLE-GENOME-BENCHMARK-20260918`.

The input and method selection was frozen before any new native output was
read. The primary matrix is complete `galGal6` and complete `danRer11`, each
with its same-assembly UCSC `rmsk.txt.gz` comparator layer. The full FASTA is
passed to native callers without train/test truncation. For D accuracy, the
pre-run exposure audit excludes the actual D TRAIN, CAL, and model-selection
DEV chromosome sets: chicken TRAIN `chr2/chr3/chr4/chr7/chr8` and CAL/DEV
`chr1/chr5/chr6`, with independent test `chr10/chr20`; zebrafish TRAIN
`chr1/chr3/chr4/chr7/chr9` and CAL/DEV `chr2/chr5/chr6`, with independent test
`chr10/chr20`. The SF5 split is retained only as a retrospective stratum and
is not called D-independent. These strata do not change the full-input native
discovery task.

Native methods are EDTA 2.3.0 and RepeatModeler2 2.0.9 followed by
RepeatMasker 4.2.4. Native jobs are CPU-only with 16 CPUs and 128 GB. RM2
uses `-threads 16`; RepeatMasker uses `-pa 4` because RMBlast 4.2.4's help
specifies four cores per parallel worker. EDTA's discovery and annotation are
timed as one combined native stage. No method receives the comparator labels.

D uses the existing six-species CAL calibration, 4096-bp non-overlapping
windows, batch size 12, and the frozen threshold. A fixed first-contig 1-Mb
CPU pilot is required before any full CPU inference. A pilot is a feasibility
measurement, and a seven-day budget failure is recorded as a typed resource
limit rather than replaced by a runtime extrapolation. GPU timing is a
separate RTX 3090 deployment measurement.

At this preflight stage no new native or D benchmark result is claimed. The
submission IDs, terminal statuses, input metadata, native class/family
counts, Unknown counts, and comparator-relative score will be appended only
after the corresponding jobs produce terminal manifests.

## Observed remote preflight

The source files and pinned artifacts were present on Baobab before
submission. The existing `.fai` files report 464 records and 1,065,365,425 bp
for galGal6, and 1,923 records and 1,679,203,469 bp for danRer11. The FASTA
file sizes are 1,086,683,182 and 1,712,826,111 bytes, respectively. The two
same-assembly comparator files were present (17,915,053 and 118,116,022
bytes). Apptainer is 1.5.3-1.el9.

Pinned artifact SHA-256 values observed remotely:

| artifact | SHA-256 |
|---|---|
| RepeatModeler 2.0.9 SIF | `93f5801a64dcc8adaec9b3307f188ff5feb65ed8c893764d0e5ab56f75020384` |
| RepeatMasker 4.2.4 SIF | `3a2d62dec0b930fa6a6aa463132976fb8de5405eedd1c4ce122ec7511689cd8c` |
| EDTA SIF | `812f277d85d575ba745c08ff2a3876d36aeb8fc0e0a08d95db28404b3837f40e` |
| EDTA source `EDTA.pl` | `255ba6ee8061224d81e3ea0685d02becf694c8a1f12796c276588085e9d78014` |

## Initial chicken submission

The first chicken execution set was submitted after the preflight:

| cell | Slurm job | frozen role |
|---|---:|---|
| EDTA native full assembly | `12888133` | CPU-only, 16 CPU/128 GB, combined discovery+annotation |
| RM2→RepeatMasker native full assembly | `12888134` | CPU-only, 16 CPU/128 GB, pooled full-assembly library |
| D CPU feasibility pilot | `12888135` | CPU-only, first 1,048,576 bp of the first source contig |
| D GPU full assembly | `12888136` | one RTX 3090, 8 CPU/96 GB, frozen sequence-only inference |

At submission all four jobs were running on the private partition. This is an
execution state, not a scientific result. Zebrafish cells and any full D CPU
cell remain gated on the fixed pilot and terminal manifest checks; no interim
score will choose a species, method, or checkpoint.

## Pilot-record correction

The fixed CPU pilot record is `chr1` in both assemblies. In danRer11 the FASTA
starts with short alternate records (`chr1_KZ114997v1_alt`, 304,771 bp), so the
original pilot `12888198` failed before model loading when it attempted the
1,048,576-bp prefix of that first record. The replacement explicitly selects
the named primary `chr1` record based on assembly structure, before labels or
model output are read. The failed directory and exact stderr are retained.
