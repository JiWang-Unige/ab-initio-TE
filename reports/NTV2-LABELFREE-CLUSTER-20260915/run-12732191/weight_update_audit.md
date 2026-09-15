# NTv2 last-two update audit

The read-only CPU Slurm audit was job `12733074` (completed in 19 s). It
compared the 30 saved tensors from native encoder layers 27 and 28 in
`last_two_ntv2_ssl_state.pt` with the corresponding tensors in the native
`model.safetensors`; it did not retrain or read family/EVAL labels.

All 30 state tensors matched by exact native key and shape. Of these, 28
weight tensors changed numerically; two rotary-frequency buffers did not.
Across the 33,570,880 matched state elements (including buffers),
33,570,706 changed at exact float comparison, with maximum absolute change
`0.0046758130`, mean absolute change `0.0003856998`, and L2 change `2.8546310`.
Layer 27 had L2 change `1.9814972`; layer 28 had L2 change `2.0548935`.

This establishes that the saved `last_two_ntv2_ssl` arm actually updated the
native layer-27/28 weights. It does not establish that adaptation improves
generalization: the main exploratory clustering comparison remains the
reported six-arm result, where the adapted arm had higher transductive ARI but
lower NMI and lower inductive ARI than the frozen NTv2 arm.

The machine-readable evidence is `weight_update_audit.json`.
