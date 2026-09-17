# Platypus strong traditional mask controls

This frozen extension tests whether the fixed platypus Tiberius receiver benefits from two strong, independently implemented traditional repeat masks. It uses the already prepared twenty-core, 100 Mb denominator and 100 kb halos from `P3-TIBERIUS-EXTERNAL-20260915`. Discovery is performed once on a pooled FASTA containing the twenty fixed 5.2 Mb halo sequences as independent contigs (104 Mb total); contigs are not concatenated and the original records are retained. No halo intervals overlap in the frozen geometry. The panel discovery runtime is not a whole-genome discovery-runtime claim.

The two new mask arms are:

* **RM2**: one RepeatModeler 2.0.9 discovery on the pooled panel followed by RepeatMasker 4.2.4 using the complete discovered `consensi.fa.classified` library. Unknown discoveries remain in the library. The report separates classified and Unknown rows and coverage without using gene scores to filter them.
* **Red**: one run of the official Red 2.0 source at commit `8fce7b1b7ac724ad92d723318008e06f984f20d7`, compiled with the available GCC 11 compiler (`make CXX=g++`), on the same pooled panel. Red is an all-repeat mask and does not provide RepeatMasker family classification; it is therefore not presented as a TE-family annotation.

Both masks are passed through the identical `mammalia_softmasking_v2` Tiberius 2.0.7 receiver, six-channel observer, 400050-bp input and batch size one used by the completed D/P3 platypus utility. Native GTF/GFF3 equality and uppercase sequence preservation are engineering gates. Final scoring waits for all twenty cores of every new arm and reuses the qualified D, U_soft, U_nosm, R_TE, R_all and P3 results on the same cores. The fixed reference annotation is a comparator, not independent biological truth.

## Frozen scientific contract

The exact inputs, versions, parameters, endpoints, and resource ceilings are in `configs/PLATYPUS-STRONG-MASK-CONTROLS-20260917.json`. The pooled panel correction was made before native execution because independent per-core RepeatModeler libraries would weaken the de novo comparator and multiply discovery costs. No threshold, checkpoint, core, reference mapping, or downstream receiver is selected from intermediate accuracy. Failures and timeouts remain in their own cell directories. The original D/P3 files are not overwritten.

The predeclared outputs are masked ACGT bp and lowercase coverage over the 104 Mb pooled halo panel, RM2 row/class/Unknown coverage, Red all-repeat coverage, reference-relative TP/FP/FN/precision/recall/F1 over the 100 Mb core gene-score denominator, all gain/loss sets, and paired 10,000-resample chromosome-cluster intervals. Comparisons are descriptive unless their uncertainty and comparator dependence support a stronger statement.

## Execution record

To be filled from the scheduler and native cell manifests after the frozen run. Any CPU concurrency or backfill wall-limit adjustment is an execution-only change and will be recorded here; it cannot change the scientific contract.

Before native execution, the initial shared-cpu submissions (12855927, 12855928) remained pending with `PartitionTimeLimit`: that partition permits 12 hours, and the account's pending-job memory ceiling is 64 GB. They were cancelled before start. A scheduler dry run then showed the account permits at most four CPUs per job, so the pooled mask commands use four CPUs/64 GB on `public-longrun-cpu` with a 24-hour limit; this changes only parallelism and execution scheduling, not the pooled input, tool versions, library policy, downstream receiver, or endpoint.

The new Tiberius arm uses `shared-gpu` with the fully qualified `gpu:nvidia_geforce_rtx_3090:1` request because the private partition's 3090 resources were occupied by unrelated work; one new Tiberius cell remains the concurrency cap.

The RM2 receiver smoke is explicitly dependent on both the completed RM2 pooled mask and the completed RED receiver array, so the two new GPU arms cannot overlap. The native RM2 command currently uses `RepeatMasker -pa 4` under a 4-CPU allocation. This records the actual native execution path; it is not a strict CPU-thread cost benchmark because the engine's internal batching/parallelism is tool-specific.

The first RED c00 smoke (12856827) failed before model inference because the initial dynamic Python loader did not register the imported dataclass module in `sys.modules`. Its `tiberius/RED/c00` directory is retained as an engineering failure. The loader is fixed and all retry/complete cells use the separate `tiberius-r2` root; no result from the failed cell enters scoring.
