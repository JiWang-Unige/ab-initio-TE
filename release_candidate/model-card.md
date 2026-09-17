---
license: cc-by-nc-sa-4.0
base_model: InstaDeepAI/nucleotide-transformer-v2-500m-multi-species
library_name: pytorch
tags:
  - genomics
  - transposable-elements
  - token-classification
  - biology
---

# Six-species D TE-material model — draft model card

This card describes an existing research checkpoint. A downloadable weight
release has **not** yet been published. The portable package is a release
candidate, not a statement that all planned paper experiments are complete.

## Model and outputs

D is a fine-tuned NTv2-500M model for detecting TE-associated sequence
material. Its supervised training species are human, mouse, pig, chicken,
zebrafish and *Caenorhabditis elegans*. The checkpoint is seed 42, arm D of
`CROSS-SPECIES-L1-UPSTREAM-20260904`.

The standalone runner takes a FASTA file and returns calibrated base-level
scores, connected threshold-positive material runs and a softmasked FASTA.
No TE reference library or target labels are read during inference. Windows
are 4096 bp, aligned from each contig origin; the tail retains its true length.
The native six-base tokenization and base projection are preserved.

The probability calibration was fit on the six-species CAL partition.
Its slope is 0.6984053956932976, intercept −0.8050313412075021 and material
threshold 0.42330056285498807. These are fixed for external-species inference.
The scores are not a validated universal probability of biological truth on
every new species.

Only threshold-positive A/C/G/T bases are lowercased in the softmasked FASTA;
ambiguity characters remain uppercase and have a separate QC track. BED and
BEDGraph use zero-based, half-open coordinates. The probability and material
tracks retain the predictions at ambiguous positions.

## Intended use

- Candidate TE-material tracks for research within the measured animal scope.
- Softmask generation for downstream tools that actually consume softmask
  information. The receiver's input requirements must be checked.
- Reproduction of the fixed D research results with their original protocols.

The output is not a biological TE insertion reconstruction, gap repair, TE
family assignment or gene annotation. The current SF5 broad-class model and
P3 gene-utility model are separate checkpoints and their results do not
describe D.

## Current evaluation scope

The supervised-species DEV bp-F1 values are human 0.940310, mouse 0.941998,
pig 0.893138, chicken 0.831720, zebrafish 0.927836 and *C. elegans* 0.797565.
These are development/reference-agreement results, not external-species
accuracy estimates.

Fixed external screens include platypus, sea urchin, *C. briggsae*,
*X. tropicalis*, honey bee and red flour beetle. They use small, predefined
regions and references of differing coverage. For example, the four-MiB frog
screen recovers 0.885797 of 1,390,306 strict reference-positive bases;
the bee and beetle panels contain only 637 and 3,622 reference-positive bases.
Sparse panels cannot establish genome-wide precision or F1. These screens
are historically observed project candidates; assembly-specific backbone
pretraining exclusion is not established.

On the fixed 100-Mb TE_Bench/GARLIC-derived simulation, D gives precision
0.887689, recall 0.301975 and bp-F1 0.450648. The best traditional methods in
that comparison perform substantially better, and D has no CPU runtime
advantage in that hardware-matched experiment. This result is retained as an
applicability limit. It does not establish that the simulation failure is
caused exclusively by sequence context.

D-specific downstream gene-annotation evaluation is being completed
separately. Earlier P3/Tiberius improvements cannot be claimed for this model.
Training-coordinate and homology exposure must be considered when interpreting
any cached representation analysis.

## Reproduce and limitations

Follow the adjacent [README](README.md) and
[notebook](notebooks/portable_d_smoke.ipynb) after staging the documented D
weights into `bundle/model/`. CPU and CUDA are selected explicitly at runtime.
Small loader-parity checks are engineering validation, not biological
accuracy benchmarks. See the research repository's protocol-specific reports
for the checkpoint lineage, source annotations, denominators and failures:
[ab-initio-TE](https://github.com/JiWang-Unige/ab-initio-TE).

The model is not validated as a universal animal, plant or fungal annotator.
No target-specific expert or MoE routing is included. Fragmented predictions
remain fragmented; no post-processing silently bridges gaps.

## Attribution and licensing

The upstream base model is
[InstaDeepAI NTv2-500M multi-species](https://huggingface.co/InstaDeepAI/nucleotide-transformer-v2-500m-multi-species).
This derived-weight candidate retains the upstream CC-BY-NC-SA-4.0 terms.
Bundled source-file notices and weight terms are documented separately in
[NOTICE.md](NOTICE.md). Do not infer an unrestricted commercial weight license
from the availability of the research code.

The final publication citation, release identifier and downloadable artifact
links will be added when the corresponding release exists.
