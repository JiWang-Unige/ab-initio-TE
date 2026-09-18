# Whole-genome benchmark submission record

The preflight was completed before the first jobs were submitted. The
complete-input chicken set is running under the frozen protocol; it has no
label-dependent model choice.

| cell | job | resource contract | submission state |
|---|---:|---|---|
| chicken EDTA | 12888133 | private, 16 CPU, 128 GB, no GPU, 7 d | failed engineering attempt; preserved |
| chicken EDTA retry | 12888165 | private, 16 CPU, 128 GB, no GPU, 7 d | running at submission |
| chicken RM2→RepeatMasker | 12888134 | private, 16 CPU, 128 GB, no GPU, 7 d | running at submission |
| chicken D CPU pilot | 12888135 | private, 16 CPU, 128 GB, no GPU, 2 h | running at submission |
| chicken D GPU | 12888136 | private, RTX 3090, 8 CPU, 96 GB, 7 d | running at submission |

The initial EDTA attempt `12888133` failed in 27 seconds before any EDTA
stage because the container could not resolve the long host-path overlay
invocation (`Can't open perl script .../EDTA.pl`). The failed directory is
preserved as `native/chicken/EDTA-failed-12888133`. The runner was repaired to
bind the same frozen source overlay at `/opt/edta230` (the path was validated
with the pinned image help command), and the unchanged chicken EDTA contract
was resubmitted as `12888165`. This is an engineering retry, not a new
scientific arm or a parameter change.

After the chicken design and first execution set were active, the matching
zebrafish native/pilot cells were submitted with the same frozen contract:

| cell | job | resource contract |
|---|---:|---|
| zebrafish EDTA | 12888196 | private, 16 CPU, 128 GB, no GPU, 7 d |
| zebrafish RM2→RepeatMasker | 12888197 | private, 16 CPU, 128 GB, no GPU, 7 d |
| zebrafish D CPU pilot | 12888198 | private, 16 CPU, 128 GB, no GPU, 2 h |
| zebrafish D GPU | 12889199 | private, RTX 3090, 8 CPU, 96 GB, 7 d; `afterok:12888136` |

The zebrafish D GPU cell `12889199` is serialized after chicken D GPU
`12888136`; this is an execution scheduling choice with no change to the frozen
scientific design and does not add a second benchmark GPU lane.

## Exposure audit and live state

The D-independent accuracy stratum follows the actual checkpoint exposure
manifest, rather than the older SF5 chromosome split. D TRAIN contains chicken
`chr2/chr3/chr4/chr7/chr8` and zebrafish `chr1/chr3/chr4/chr7/chr9`; D CAL and
model-selection DEV contain chicken `chr1/chr5/chr6` and zebrafish
`chr2/chr5/chr6`. The fixed independent chromosomes are chicken `chr10/chr20`
and zebrafish `chr10/chr20`. SF5 remains a retrospective reporting stratum.
Native discovery and timing continue to use complete assemblies. The binary D
arm has no class/family output, so its class field is N/A; native Unknown rows
remain in the audit.

At the latest scheduler snapshot, chicken EDTA retry `12888165`, chicken RM2
`12888134`, chicken D CPU pilot `12888135`, chicken D GPU `12888136`, and
zebrafish EDTA `12888196` were RUNNING. Zebrafish RM2 `12888197` and D CPU
pilot `12888198` were PENDING; no terminal scientific score had been read.
Zebrafish D GPU `12889199` was submitted with `afterok:12888136` and was
therefore dependency-pending at submission. The earlier failed EDTA attempt remains preserved under
`native/chicken/EDTA-failed-12888133`.

The chicken RM2 process `12888134` was submitted just before the explicit
`-e rmblast` flag was added to the runner. Its immutable status manifest records
the actual `RepeatMasker -pa 4` command; the pinned RepeatMasker 4.2.4 image's
default search engine is RMBlast. The subsequent native cell uses the explicit
`-e rmblast` command, and both cells remain in the same frozen RM2 library and
masking contract. This execution-level difference is retained in the audit
rather than silently rewritten.

The two native jobs operate on complete `galGal6.fa`. The D pilot operates on
the fixed first 1,048,576 bp of the first FASTA contig and is a feasibility
measurement only. D GPU operates on complete `galGal6.fa`. Jobs are not
selected or stopped by an interim scientific metric. Terminal status and
outputs will be collected under the experiment output root; missing, failed,
or time-limited cells remain explicit.

## CPU execution audit

The running CPU pilot was inspected without restarting it. The frozen
checkpoint contains `torch FloatStorage` tensors and its config has no reduced
precision dtype; the inference code has no autocast or BF16/FP16 path. The live
pilot process is bound to CPUs `0-15` and has `OMP_NUM_THREADS=16`, but the
runner also sets `MKL_NUM_THREADS=1` and `OPENBLAS_NUM_THREADS=1`. A light
probe under the same environment reports Torch intra-op threads `1` and
inter-op threads `128`; repeated `/proc` samples of the live pilot show two
process threads and approximately one core of CPU time. Thus the current
pilot is FP32 but is a one-intra-op-thread CPU deployment under a 16-CPU
allocation. This execution fact is retained with the original timing; it is
not interpreted as a hardware-independent 16-thread CPU benchmark. The GPU
process is separately bound to CPUs `80-87` with `CUDA_VISIBLE_DEVICES=0`.

The runner has now been repaired for subsequent CPU cells: `MKL_NUM_THREADS`
and `OMP_NUM_THREADS` follow the allocated CPU count, OpenBLAS remains one
thread to avoid nested pools, and the inference process explicitly sets Torch
intra-op to the allocation and inter-op to one. The inference summary now
records the realized Torch thread counts, CPU affinity, and model dtype. The
original one-thread pilot is preserved as an engineering attempt; any new
fixed pilot uses a fresh output directory and is not merged with its timing.

## CPU contract repair and fresh pilot

The original chicken CPU pilot `12888135` was cancelled by the parent
controller after the execution audit identified a one-intra-op-thread runtime
under the nominal 16-CPU allocation. Its output directory
`d/chicken/cpu_pilot` and `status.json` are preserved verbatim; the status is
left `RUNNING` because Slurm cancellation interrupted the wrapper before its
exception handler could publish a terminal state. Slurm records the actual
terminal state as `CANCELLED`, elapsed `00:41:08`, allocation `16 CPU/128 GB`,
and exit `0:0`. This attempt is an engineering-invalid CPU datum and is not
combined with the corrected pilot.

The corrected chicken pilot was submitted as `12889857` with the same fixed
1,048,576-bp input contract, checkpoint, calibration, batch size, and threshold
under a fresh output directory:
`d/chicken/cpu_pilot_fixed16`. The child inference process now emits a flushed
`runtime_contract_realized` JSON line immediately after model loading, and the
terminal summary repeats the realized Torch intra/inter-op counts, CPU
affinity, device, and checkpoint dtype. The corrected pilot remains a
feasibility measurement; its result controls only whether a full CPU run fits
the frozen seven-day budget.

The zebrafish pilot `12888198` remains on the original fixed input/output
contract and reads the same repaired runner before child startup. In fact, its
terminal Slurm state is `FAILED`, elapsed `00:00:20`, exit `1:0`: the first
FASTA record was the 304,771-bp alternate scaffold
`chr1_KZ114997v1_alt`, shorter than the fixed 1,048,576-bp pilot. The failure
occurred before model loading, so it has no scientific result; its empty output
directory, exact stderr, and an explicit `FAILED_ENGINEERING` status manifest
are preserved. The frozen replacement pilot uses `chr1`, the first primary
chromosome record long enough for the fixed prefix, and a fresh output
directory. It is fixed from assembly structure before labels or model output,
and does not silently reuse the failed directory.

The fresh zebrafish pilot will read the repaired runner before child startup;
its runtime evidence will be taken from the immediate child log line and
terminal summary. No result is selected by an interim score.

The replacement zebrafish pilot was submitted as `12891218`, with
`afterany:12889857` solely to serialize the one-D-CPU-pilot execution lane.
It uses the frozen `chr1` primary-record prefix and fresh output directory
`d/zebrafish/cpu_pilot_chr1_fixed16`; the failed `d/zebrafish/cpu_pilot`
directory remains untouched.

The corrected chicken child has now started on `gpu035`. Its flushed
`inference.stdout` line reports `torch_intra_op_threads=16`,
`torch_inter_op_threads=1`, affinity `[0,1,...,15]`, `model_dtype=torch.float32`,
and `device=cpu`; the output status remains `RUNNING` while the pilot loop
continues.

The corrected chicken pilot completed as `12889857` in 7 minutes 30 seconds.
Its terminal summary repeats the same 16/1 Torch runtime, affinity, and FP32
checkpoint dtype; observed end-to-end throughput was 2,467.58 bp/s and peak
RSS was 4,531,736 kB. The frozen linear feasibility estimate for the
1,065,365,425-bp galGal6 assembly is approximately 5.0 days, within the
seven-day CPU ceiling. This authorizes the pre-specified full CPU feasibility
gate, but the pilot remains a deployment datum and is not a whole-genome
timing claim.

The corrected zfish pilot `12891218` is now resource-pending after the chicken
pilot's `afterany` serialization dependency. The terminal score job was
submitted as `12891298` with `afterok` dependencies on chicken/zebrafish
EDTA, RM2, and D GPU cells (`12888165`, `12888134`, `12888196`, `12888197`,
`12888136`, `12889199`). It will use the repaired geometry and native parser;
CPU full-genome inference remains a separate gate.

## Scoring geometry repair

Before any score job is run, the scorer now excludes comparator rows marked
`Unknown`, `?`, or `ARTEFACT` from both positive truth and negative callable
truth, while keeping them in the label audit. The callable denominator is the
number of A/C/G/T bases after that exclusion; raw FASTA length and excluded
uncertain bp are reported separately. Each species receives only its own
`whole_assembly` and `d_independent_test` strata. EDTA GFF parsing retains the
`repeat_region` material span and skips its child LTR/target-site subfeatures,
while excluding rRNA and target-site rows. RM2 is parsed from `annotation.out`
using its native class column: LINE/SINE/LTR/DNA/RC/Retroposon and Unknown are
retained, while simple/low-complexity/satellite/RNA classes are excluded. The
native class output remains a composition audit only: no class precision,
recall, or confusion matrix is claimed by this binary score, and D remains
class N/A.

The lightweight pre-score geometry fixtures passed: an uncertain-only
prediction contributes zero FP, N bases are absent from the denominator, an
EDTA parent-plus-child fixture retains the parent material span without child
double-counting, and a RepeatMasker `.out` fixture excludes simple/low-
complexity classes while retaining an Unknown row.

The native hierarchy rule was reconciled against the independent class-map
parser on the real EDTA sample
`outputs/TE-LONG-BENCH-20260915/native-12738464/sim100-edta/work/panel.fa.mod.EDTA.anno/panel.fa.mod.EDTA.TEanno.gff3`.
After merging intervals by chromosome, the binary parser and class-map parser
produced exactly the same `(chrom,start,end)` list: 91,257 intervals with a
40,921,429-bp union. The class-map parser's pre-paint row span was 42,977,794
bp due to overlap; it reported 122,867 retained rows and 7 suppressed parent
containers. Exact interval equality, rather than only equal total bp, confirms
that the binary and class-map material geometry agree on this actual EDTA
output without treating overlapping rows as additive bp.

The companion class-map parser smoke (`parser_smoke.py`) also passed on the
remote Python environment, including DNA? ambiguity, Unknown, native
non-TE-class filtering, and EDTA complete-body hierarchy cases.

## CPU hardware class

The shared-node audit in `hardware-cpu.json` records `gpu034.baobab` and
`gpu035.baobab` as the same AMD EPYC 7742 64-core processor class (2 sockets,
SMT1, 8 NUMA nodes). These are distinct shared nodes; matching hardware class
does not imply exclusive allocation or identical instantaneous load.

## Full chicken CPU inference

The fixed pilot's observed 2,467.58 bp/s satisfies the pre-specified linear
feasibility gate (approximately 5.0 days for galGal6 under the seven-day
limit). The full chicken CPU cell was therefore submitted as `12891439` with
the unchanged 16-CPU/128-GB/7-day contract. Its execution is serialized with
`afterany:12890969:12889062:12889063` so short class-map and non-mammal gene
utility jobs have the first scheduling opportunity; this dependency does not
condition the scientific endpoint or select a result. Output is the fresh
`d/chicken/cpu` directory. Full-genome CPU timing and the 1-Mb pilot timing
will remain separate fields.

## Metadata-only provenance adjustment

Future benchmark cells now record lightweight file metadata (path, size, and
mtime) instead of reading multi-gigabyte source/container files solely to
compute registration hashes. The original completed/running manifests that
already contain SHA-256 values are preserved and are not rewritten. Native
software versions, image paths, commands, and preflight artifact records remain
explicit in the frozen config and historical report.
