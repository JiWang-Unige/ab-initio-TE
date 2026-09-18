# Unified NTv2 representation readout

The fixed three-arm extraction job `12889676` completed with exit code `0:0`
in 2:52. It encoded the exact SIB split (TRAIN 1,843, VAL 809, TEST 1,580)
with the same NTv2-500M tokenizer, final hidden state, max length 2,048, and
attention-mask mean excluding structural special tokens and padding while
retaining input N/UNK tokens. All arms have feature dimension 1,024 and the
same record counts and label supports. CPU evaluators `12889677` (pretrained),
`12889678` (binary D), and `12889679` (class D last2) completed successfully.

The raw per-arm JSON is in
`results/evaluation-12889676/{pretrained,binary_D,class_D_last2}.json`; the
extraction contract is in `extraction_summary.json` in the same directory.
All supervised readouts fit on TRAIN only and evaluate TEST once. K-means is
fit on TRAIN only; its ARI/NMI values are label-scored diagnostics, not
label-free discovery claims.

## Supervised readouts

| endpoint | support | pretrained KNN5 | binary D KNN5 | class D last2 KNN5 | pretrained linear | binary D linear | class D last2 linear |
|---|---:|---:|---:|---:|---:|---:|---:|
| known-five macro-F1 | 1,281 | 0.4885 | 0.6394 | 0.7261 | 0.4827 | 0.6656 | 0.7041 |
| full-eight macro-F1 | 1,580 | 0.4730 | 0.5934 | 0.6512 | 0.4547 | 0.6232 | 0.6329 |
| conditional TE-four macro-F1 | 921 | 0.6342 | 0.7197 | 0.8417 | 0.5972 | 0.7978 | 0.8253 |
| known-five binary macro-F1 | 1,281 | 0.5211 | 0.7211 | 0.7365 | 0.5873 | 0.7031 | 0.6995 |

The known-five and TE-four gains are consistent across both supervised
readouts when moving from pretrained to binary D and then to the matched class
arm. The binary linear probe is slightly lower for class D last2 than for
binary D (`0.6995` vs `0.7031`), while its multi-class and TE-four readouts
improve; this is retained as an observed endpoint-specific difference rather
than selecting a favorable readout.

## Fixed-K unsupervised diagnostics

Each endpoint uses a train-only K-means fit. “Annotation-filtered” means that
the endpoint's declared support is used for the fit; the fit itself does not
use class targets, while ARI/NMI score the resulting partition with labels.

### Known-five support

| arm | K2 ARI/NMI | K4 ARI/NMI | K5 ARI/NMI | K8 ARI/NMI |
|---|---|---|---|---|
| pretrained | 0.0302 / 0.0423 | 0.0452 / 0.0610 | 0.0386 / 0.0533 | 0.0434 / 0.0836 |
| binary D | 0.1175 / 0.1132 | 0.1058 / 0.1399 | 0.1105 / 0.1500 | 0.0907 / 0.1535 |
| class D last2 | 0.1639 / 0.1798 | 0.2185 / 0.2329 | 0.2200 / 0.2588 | 0.2268 / 0.3118 |

### Full-eight support

| arm | K2 ARI/NMI | K4 ARI/NMI | K5 ARI/NMI | K8 ARI/NMI |
|---|---|---|---|---|
| pretrained | 0.0306 / 0.0571 | 0.0536 / 0.1216 | 0.0581 / 0.1164 | 0.0623 / 0.1291 |
| binary D | 0.0780 / 0.0850 | 0.0821 / 0.1261 | 0.1011 / 0.1546 | 0.1096 / 0.1974 |
| class D last2 | 0.0918 / 0.1109 | 0.1902 / 0.2439 | 0.1890 / 0.2623 | 0.2232 / 0.3242 |

### Conditional TE-four support

| arm | K2 ARI/NMI | K4 ARI/NMI | K5 ARI/NMI | K8 ARI/NMI |
|---|---|---|---|---|
| pretrained | 0.0415 / 0.0555 | 0.0713 / 0.0813 | 0.0816 / 0.0961 | 0.0679 / 0.1122 |
| binary D | 0.0175 / 0.0153 | 0.0424 / 0.0612 | 0.0530 / 0.0819 | 0.0475 / 0.0826 |
| class D last2 | 0.1902 / 0.1814 | 0.2287 / 0.2426 | 0.2144 / 0.2531 | 0.2342 / 0.3273 |

The separate full-eight K2 partition scored on the known-five binary support
has ARI/NMI `0.0118/0.0127` (pretrained), `0.2181/0.1851` (binary D), and
`0.3018/0.2250` (class D last2). This is a full-eight fit followed by a
known-support diagnostic and should not be conflated with the endpoint
filtered K2 rows.

## Bounded context-length diagnostic

The first attempt in extraction job `12889676` attempted the predeclared
central-512 target pooling for 512/2,048/4,096-bp contexts. Native
content-token count and input IDs passed before target pooling, but the
explicit target-span coverage check failed with `covered=0, target=512`.
The root cause was an indexing error in the context slice: the code used
`(context_length-512)/2` as a source start while still passing the 4,096-bp
source target coordinates. Thus the 512-bp input was the source prefix rather
than the fixed central target; 2,048 bp was similarly shifted, and the 4,096-bp
slice exceeded the source end. The failure was retained as
`BLOCKED_NATIVE_OFFSET`; no result was silently imputed.

The repair computes the source bounds around the fixed source target
`[1792,2304)`: 512 bp uses source `[1792,2304)` and local target `[0,512)`,
2,048 bp uses `[1024,3072)` and `[768,1280)`, and 4,096 bp uses
`[0,4096)` and `[1792,2304)`. It asserts requested context length and exact
target sequence identity before pooling. A Baobab `te_benchmark` fixture
passed all three coordinate contracts and remote `py_compile` passed. A
length-only retry `12897975` and private CPU-only evaluator `12897980` both
completed successfully. All 3 models x 3 contexts produced 768 finite
1,024-D feature rows, 768 labels, and 768 composition rows; target-pooling
weights summed to exactly 512 bp for every record. The retry's context
readouts are in `LENGTH-RETRY-RESULTS-12897975.md`. Original evaluator
`12889680` finished in three seconds and remains tied to the blocked input; it
is superseded for length reporting. The primary SIB 512-bp representation
results above are complete and unaffected.

## Interpretation boundary

The matched class arm improves most supervised and fixed-K multi-class
readouts relative to the same-backbone pretrained and binary-D arms. The
SIB TEST panel nevertheless contains exact coordinate/sequence exposure to D
TRAIN/CAL/DEV (3 chicken TRAIN, 9 zebrafish CAL, 7 zebrafish DEV, and 149
*C. elegans* DEV records), and the class labels derive from the comparator
ontology painted on the D coordinates. These results support ontology-aligned
representation adaptation on the fixed panel, not an untouched generalization
or independent biological-validation claim.
