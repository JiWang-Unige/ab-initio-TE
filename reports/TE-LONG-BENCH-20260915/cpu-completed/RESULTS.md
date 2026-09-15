# Completed fixed-D CPU inference

CB4 job 12731959 completed with Slurm exit0 in 07:15:16. The recorded model-load-through-inference/output wall time is 26112.050487 seconds (about 7 h 15 min). All 367 input sequences, totaling 108384165 bp, were processed; their recorded lengths sum exactly to the common input denominator.

The process reported 16 allocated CPUs, Intel Xeon E5-2630 v4 at 2.20 GHz, CPU execution, the frozen 4096-bp window and batch size12. Model weights, calibration and threshold were unchanged. Per-sequence timing details and probability arrays remain on Baobab; the compact status retains total input, runtime and model provenance.

The post-run Slurm node metadata for cpu238/239/240/241/243/244 identifies the same E5-2630V4 family, two ten-core sockets and one thread per core. These cover the original native CPU nodes, the D CPU nodes and the verified EarlGrey continuations. The snapshot is infrastructure metadata rather than an in-process measurement for every native attempt; final reporting must retain the actual node for each selected continuation.

Sim100 CPU job 12731960 also completed with exit0 (Slurm 06:37:45); its recorded model-load-through-output time is 23861.162315 seconds for the full 100000000-bp sequence. It used the same E5-2630 v4 CPU family, 16 CPUs, window and batch size. Thus both requested complete CPU inference cells are finished. Final CPU/native ranking still waits for the remaining EDTA cells and complete scoring bundle; GPU timings remain a separate hardware category.

| input | model-load-through-output seconds | complete input bp | throughput bp/s |
|---|---:|---:|---:|
| c_briggsae | 26112.050 | 108384165 | 4150.734 |
| sim100 | 23861.162 | 100000000 | 4190.911 |

Throughput uses total input length, including N-containing positions traversed by the runner; accuracy uses its separately qualified callable-base denominator. It is whole-workflow throughput on these two inputs, not isolated model-forward throughput.
