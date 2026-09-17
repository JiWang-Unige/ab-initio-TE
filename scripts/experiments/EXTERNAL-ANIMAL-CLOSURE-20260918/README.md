# External animal closure, 2026-09-18

This directory contains a fixed external screen for the frozen six-species D
NTv2-500M seed-42 checkpoint.  It is deliberately separate from the earlier
4-MiB frog/bee/beetle screen and from the sealed horse/opossum/fruit-fly panel.

The two preselected sources are `fr3` *Takifugu rubripes* and `taeGut2`
*Taeniopygia guttata*.  Each uses the 20 longest source contigs, with the
center 5,242,880 bp retained from each contig (104,857,600 bp/species).  The
source RepeatMasker `.out` files are same-assembly, classified historical
layers.  They qualify the panel as label-rich source coverage; they do not
provide independent biological truth.  Unknown, ambiguous and non-TE repeat
classes are not negative labels.

The order is:

```text
python qualify.py --config configs/EXTERNAL-ANIMAL-CLOSURE-20260918.json --species torafugu --output .../quality.json
python prepare.py --config ... --species torafugu --output .../prepared
sbatch infer.sbatch torafugu
python score.py --panel .../prepared --inference ... --output .../score
python class_breakdown.py --panel .../prepared --inference ... --reference ... --output .../class_breakdown
python summarize.py --reports ...
```

Qualification and source metadata are recorded before inference.  No target
specific calibration, model selection, reverse-complement ensemble, phase
search or threshold search is allowed.  A successful run supports a fixed
regional positive-layer recovery statement, not whole-genome F1 or universal
species generalization.

After both frozen-D inference jobs completed, `class_breakdown.py` was run as
CPU-only array job `12889181_[0-1]` (4 CPUs, 16G, 30 minutes). It reused the
existing `material_runs.bed` files and reports strict-known `DNA`, `LINE`,
`SINE`, `LTR`, `RC`, and `Retroposon` recovery by independent interval union
from the original `.class` field. N/non-callable bases and uncertain source
classes follow the pooled score convention, and cross-class overlap is
reported rather than added to a total.
