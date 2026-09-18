# Length-only context diagnostic: retry result

The repaired length-only extraction `12897975` completed with `0:0` in
5:20 on one RTX 3090 (4 CPU, 32G). The CPU readout `12897980` completed with
`0:0` in 20 seconds (4 CPU, 16G). No three-arm SIB extraction was repeated.

The retry used the same seed, models, source records, labels, and train-to-test
readout rules as the original bounded diagnostic. It selected 384 TRAIN, 192
CAL, and 192 DEV half-records (64/32/32 per each of the six D species). Each
context length encoded 768 records for each of the three models, with 1,024-D
features and 768 composition rows. The retry manifest and raw evaluator are in
`results/length-retry-12897975/`.

## Contract verification

The fixed source target is `[1792,2304)` in each 4,096-bp record. The repaired
source/local coordinates were:

| context | source slice | local target | target tokens per record |
|---:|---|---|---:|
| 512 | `[1792,2304)` | `[0,512)` | 87 |
| 2048 | `[1024,3072)` | `[768,1280)` | 86 |
| 4096 | `[0,4096)` | `[1792,2304)` | 86 |

All 3 models x 3 contexts passed the following checks: feature shape
`(768,1024)`, label shape `(768,)`, 768 composition rows, finite feature
values, identical labels across models, and the target-pooling assertion that
overlap weights sum to exactly 512 bp for every record. The status files are
`PASS_EXTRACTION` and `PASS`; there is no remaining offset blocker for this
retry.

The selected target labels are imbalanced: TRAIN has BG/SINE/LINE/LTR/DNA/
KNOWN_OTHER/AMBIGUOUS/UNCLASSIFIED counts `260/19/48/26/23/0/7/1`, CAL has
`125/7/27/12/16/2/3/0`, and DEV has `121/14/23/15/13/1/3/2`. Results should
therefore be read as a bounded context diagnostic, not a balanced species
benchmark. The full DEV support is 192; known-five/BG-versus-main-TE support
is 186 (BG=121, TE=65), and conditional TE-four support is 65.

## DEV macro-F1 by context and arm

All probes fit TRAIN only and evaluate the 192-record DEV split once. The
binary endpoint is the known-five support (BG versus the four main TE classes),
not the full eight-state panel. The composition baseline uses the declared
target/context GC and N fractions plus context length and is included as a
simple covariate reference.

| context | arm | KNN known-five | KNN full-eight | KNN TE-four | KNN binary | linear known-five | linear full-eight | linear TE-four | linear binary | composition binary |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 512 | pretrained | 0.2881 | 0.1780 | 0.3953 | 0.6441 | 0.4614 | 0.2778 | 0.5958 | 0.7410 | 0.3922 |
| 512 | binary D | 0.5887 | 0.3479 | 0.6183 | 0.8401 | 0.7019 | 0.4172 | 0.7336 | 0.8571 | 0.3922 |
| 512 | class D last2 | 0.7964 | 0.4950 | 0.8615 | 0.8703 | 0.7559 | 0.4622 | 0.8412 | 0.8527 | 0.3922 |
| 2048 | pretrained | 0.5734 | 0.3558 | 0.5686 | 0.8360 | 0.6680 | 0.4046 | 0.5790 | 0.8635 | 0.4193 |
| 2048 | binary D | 0.6362 | 0.3905 | 0.5712 | 0.9103 | 0.6725 | 0.4326 | 0.7286 | 0.8998 | 0.4193 |
| 2048 | class D last2 | 0.8438 | 0.5213 | 0.9064 | 0.9116 | 0.8421 | 0.5404 | 0.8929 | 0.9413 | 0.4193 |
| 4096 | pretrained | 0.6012 | 0.4340 | 0.5376 | 0.8690 | 0.6086 | 0.3735 | 0.6604 | 0.8991 | 0.3861 |
| 4096 | binary D | 0.6309 | 0.3880 | 0.6150 | 0.9110 | 0.7573 | 0.4786 | 0.7780 | 0.9223 | 0.3861 |
| 4096 | class D last2 | 0.8438 | 0.5255 | 0.9211 | 0.9172 | 0.8688 | 0.5225 | 0.8769 | 0.9347 | 0.3861 |

The class D last2 arm is strongest for the main representation endpoints at
all three contexts. Its KNN known-five macro-F1 rises from `.7964` at 512 bp
to `.8438` at 2,048 and remains `.8438` at 4,096; its linear known-five
macro-F1 rises from `.7559` to `.8421` and `.8688`. Its KNN TE-four score
increases from `.8615` to `.9064` and `.9211`. Binary-D and pretrained arms
show more endpoint- and readout-specific variation, so context length should
not be described as a universal monotonic effect. The composition baseline is
below the adapted embedding readouts in every context, but this small,
imbalanced diagnostic does not isolate all species or label-source effects.
Because the exact target is held fixed while the native tokenizer represents
it with 87, 86, and 86 overlapping content tokens at 512, 2,048, and 4,096 bp,
the comparison establishes context-setting sensitivity under this tokenizer;
it does not isolate a purely biological flanking-sequence effect from token
boundary/segmentation effects.

## Interpretation boundary

The repaired experiment establishes that target-centered context features can
be extracted and evaluated under the frozen protocol. It supports a bounded
context-sensitivity result for the matched NTv2 representations, especially
the class-adapted arm. The DEV subset remains small and is drawn from the
fixed source-order diagnostic; the known coordinate exposure of the larger SIB
panel and the comparator-derived label ontology remain the previously recorded
limitations. No context length was selected using DEV performance.
