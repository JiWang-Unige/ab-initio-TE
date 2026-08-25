# ChatGPT Pro review: TE-specific post-training

Date: 2026-08-25
Conversation: `6a8d7c50-0ca0-83eb-b7a7-38c95f3fb1d6`

## Converged points

- Generic Human MLM-DAPT tested only additional ordinary Human-sequence
  exposure. It did not test TE-aware masking or a segmentation-aligned task.
- Human bp F1 near 0.934 alongside segment F1 near 0.34-0.38 and boundary F1
  near 0.20-0.22 is consistent with strong local signal and weak instance
  representation, but does not prove that architecture is the only bottleneck.
- SegmentNT supports transferring multiscale down/up sampling, skip connections
  and joint encoder/head training. Its biological label ontology and context
  recipe cannot be copied without validation.
- Tiberius supports end-to-end structural bias, not direct reuse of a gene HMM.
  TE classes do not share a universal exon/intron-like grammar.
- HiTE's FlyBase advantage may arise from target-genome repeat redundancy,
  clustering, consensus construction and copy recovery. Tool ablations are
  required to separate those effects from structural rules or a known library.
- TE-aware span MLM can still solve masked nucleotides through GC, k-mer or
  family composition. It cannot be said to learn boundaries without boundary
  perturbation/composition controls and downstream held-out-species evidence.

## Terminology

- A only: **annotation-conditioned TE-aware self-supervised continued
  pretraining**.
- B only: **task-specific supervised adaptation/fine-tuning of a pretrained
  genome language model**.
- The short name **TE-specific post-trained genome language model** is justified
  only if P2 shows an independent increment over P1 and P4 shows that the P2
  initialization adds to P3.

## Decisive unresolved asset question

The Pro review identified one route-changing fact: whether the project has
copy-level biological TE start/end and trustworthy interior/boundary/flank
annotations outside Drosophila. The repository audit found no such frozen
asset. Existing JSONL contains sequence, binary/unknown labels and coordinates;
RepeatMasker row provenance is not biological copy identity. P2 therefore stays
blocked at the mechanism-smoke stage until the remote asset audit proves more.

The complete operational decision and gates are frozen in
`TE-STRUCTURE-PILOT-20260825-R1-MATRIX.md`.

## Primary-paper check

- [SegmentNT](https://pmc.ncbi.nlm.nih.gov/articles/PMC12615259/) replaces the
  original language-model head with a two-down/two-up 1D U-Net, uses skip
  connections and trains encoder and segmentation head end to end. P3 borrows
  only that multiscale geometry; its 128-channel pilot is not a reproduction of
  SegmentNT's much larger head or its 14-class label ontology.
- [Tiberius](https://pmc.ncbi.nlm.nih.gov/articles/PMC11645249/) integrates a
  differentiable HMM into training and inference, but its 15 states encode
  gene-specific exon, intron, frame, splice and start/stop constraints. The
  transferable principle is end-to-end structural bias, not the gene grammar.
- [HiTE](https://pmc.ncbi.nlm.nih.gov/articles/PMC11219922/) explicitly uses
  target-genome all-vs-all alignments, clustering, MAFFT consensus construction
  and TE-type-specific structure/homology modules. The FlyBase advantage cannot
  be attributed to a single factor without ablating multi-copy, structure and
  classification/library components.
