# Bundle layout

All paths in `manifest.json` are relative to this directory. The model weights
are omitted from this candidate because the derived NTv2 checkpoint is large
and its upstream non-commercial terms must be carried with any public release.
For a local run, place the verified `pytorch_model.bin` in `model/` and keep
the supplied tokenizer, model code and calibration files together. The
softmasked FASTA lowercases only canonical A/C/G/T predictions; ambiguity
symbols remain uppercase and are reported in `ambiguity_qc.bed`.
