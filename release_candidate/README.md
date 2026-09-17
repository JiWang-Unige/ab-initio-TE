# Portable D TE-material inference (release candidate)

This package turns an unlabelled FASTA into three practical sequence tracks:

* `material_probability.bedGraph`: calibrated TE-material probability for every
  input base;
* `material_runs.bed`: connected threshold-positive material runs;
* `softmasked.fa`: threshold-positive canonical A/C/G/T bases lowercased for
  downstream masking workflows; predicted IUPAC/N bases stay uppercase.

`ambiguity_qc.bed` records non-ACGT IUPAC input bases separately. The input is
not censored, and the output is a material mask rather than a TE insertion or
family annotation. No labels, reference library, gap filling, smoothing or
post-hoc length filter is used.

## Install and run

Use a torch build appropriate for the target CPU or CUDA runtime, then install
the package from this directory:

```bash
python -m pip install -r requirements.txt
python -m pip install .
portable-d \
  --bundle-root bundle \
  --fasta examples/human_hs1_example.fa \
  --output-dir run-tiny \
  --device cpu \
  --batch-size 2
```

The same command accepts `--device cuda` on a CUDA host. `--device auto`
selects CUDA when available and otherwise uses CPU. `--cpu-threads N` can set
the torch CPU thread count.

The human example contains two 4096-bp windows from the public hs1 reference,
chr4:2326528–2334720 (zero-based, half-open). They are the first two records
of an already observed research DEV stream, not an independent test. The
frozen D CPU parity run predicted 3,418 positive bases; this is an output
example, not a biological accuracy score. `examples/tiny.fa` remains a small
synthetic syntax example and need not produce any positive TE prediction.

## Bundle and model identity

`bundle/manifest.json` and `bundle/calibration.json` contain only relative
paths. They identify the frozen seed-42 arm-D checkpoint from
`CROSS-SPECIES-L1-UPSTREAM-20260904`, its six-species CAL Platt calibration,
4096-bp windows and six-base token projection. The approximately 2 GB
`bundle/model/pytorch_model.bin` is intentionally absent from this candidate;
place the verified checkpoint there before running inference. The supplied
tokenizer and model-code files are sufficient for the loader and do not import
the research repository.

The calibration JSON contains both the historical `protocol` field and the
explicit `calibration_protocol` field. The loader validates the explicit
`calibration_protocol`; the other field is retained as provenance.

## Reproducibility boundary

The implementation preserves the original D evaluator's `sequence_tokens`,
`infer_half_margins`, 4096-bp windowing, float32 token-margin to base-margin
projection, and Platt transform. It is an engineering release candidate. A
successful run does not establish new accuracy, external-species generalization,
gap recovery or downstream gene-annotation utility.

See `notebooks/portable_d_smoke.ipynb` for a step-by-step local smoke and
`bundle/README.md` for the weight staging rule.

The [benchmark score replay](benchmark/README.md) reproduces the recorded
long-input benchmark aggregation with standard Python and an explicit public
input bundle. It does not rerun annotation tools or measure inference speed.
