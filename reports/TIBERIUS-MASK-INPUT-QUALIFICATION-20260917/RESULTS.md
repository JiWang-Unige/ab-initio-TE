# Tiberius mask-input qualification

2026-09-17. Direct inspection of upstream model YAMLs changes the proposed nonmammalian masking experiment. These are metadata checks, not new gene prediction results or locally installed weights.

| Configuration | Softmask input | Consequence |
|---|---|---|
| current `vertebrates.yaml` | False | An uppercase/lowercase masking comparison does not test a learned mask channel in this model. No qualifying nonmammalian vertebrate softmask receptor established. |
| current `insecta.yaml` | False | Use as the current unmasked workflow comparator, not as a seven-arm softmask receptor. |
| superseded `insecta_softmasking.yaml` | True | A specifically named historical softmask model can test input-mask utility; do not claim this improves the current insecta model. |
| current `mammalia_softmasking_v2.yaml` | True | Eligible for a D-specific paired-mask experiment, separately from existing P3 results. |

The current and historical insect models list `Apis_mellifera` among training species. Honey bee is outside the six-species D task training set, but not outside these Tiberius task training sets. Those exposure definitions must be separate.

Pro's initial suggestion of two nonmammalian taxa × ten cores × seven mask arms is therefore **not executable as stated with the current vertebrates/insecta configurations**. Merely having a clade checkpoint is insufficient. No 140-call array was submitted under that assumption. Do not override the metadata flag, change softmask to hardmask, or train a new gene model as an undocumented repair.

The finite alternative is to complete D's own utility on an actual mask-consuming mammalian model; optionally add one preselected insect using the historical mask-consuming model and a current unmasked workflow comparator. Nonmammalian TE generalization still proceeds independently. A broader nonmammalian gene-annotation utility claim remains unestablished.

The exact source copies are under `source/`, with retrieval URLs and field readout in [qualification.json](qualification.json). They were downloaded from the official [Tiberius repository](https://github.com/Gaius-Augustus/Tiberius); [model configuration documentation](https://github.com/Gaius-Augustus/Tiberius/blob/main/model_cfg/README.md) states that `softmasking: false` does not use the softmasking track. Current upstream revisions are not assumed identical to every cached Baobab installation.

This finding was sent back to ChatGPT Pro for a correction of its proposed downstream design. It is a receiver/input qualification limitation, not a new negative TE-model result.
