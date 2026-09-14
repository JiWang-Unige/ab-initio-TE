# Sea-urchin adaptation and original-species retention

[PNG](sea-adaptation-retention.png), [PDF](sea-adaptation-retention.pdf),
[SVG](sea-adaptation-retention.svg).

**Figure. Small frozen-feature heads improve sea-urchin material agreement but
do not preserve fragment agreement or original-species performance.**
Panels A and B compare five arms on the same sea-urchin region-4 EVAL mask:
frozen D with its historical six-species calibration; frozen D recalibrated on
sea region 3; a dense residual adapter; a learned two-expert gate; and a
constant-average two-expert head. Heads were trained on regions 1–2 only,
with 25 fixed epochs and seed42. Each epoch had 256 nominal tile steps,
255 optimizer updates and one fully masked step retained in the manifest but
skipped for loss. CAL alone selected epochs 5, 6 and 23, respectively.

Region 4 contains 152,710 comparator-positive, 582,987 reference-negative
and 312,879 masked bases. All five arms share these denominators. These
uncurated-library labels are not independent truth, and reference-negative
bases are not validated biological negatives. Panel B uses a different y-axis
range from A and C. Segment agreement is a comparator-topology measure,
not identification of biological insertions.

Panel C evaluates the same original six-species first-32 DEV tiles per species
after sea adaptation. Tan bars apply the sea-selected calibration directly.
Blue bars use a separate shared CAL refit on the original six species after
the head is frozen. The dashed line is the recalibrated frozen-D baseline.
Neither original-species DEV nor sea EVAL chooses an epoch or threshold.
The separate refit is a diagnostic, not one common calibration for seven
domains. The source panel was previously viewed; this is exploratory
adaptation, not independent or zero-shot validation. No initialization-error
bars are implied by this single-seed experiment.

Source: [completed job12709175](../../../../reports/D-ADAPTER-MOE-PILOT-20260914/sea-12709175/sea-summary.json).
Reproduce with `scripts/manuscript/plot_sea_adaptation_20260914.py` from
the repository root using the existing figure Python environment.
