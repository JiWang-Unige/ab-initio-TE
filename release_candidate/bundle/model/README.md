# D checkpoint slot

The portable release candidate intentionally does not include the approximately
2 GB derived checkpoint. Place the verified seed-42 D file at
`bundle/model/pytorch_model.bin` before running inference. The file must be the
`CROSS-SPECIES-L1-UPSTREAM-20260904` seed-42 arm-D checkpoint described by the
bundle manifest. Do not substitute a different model and calibration pair.
