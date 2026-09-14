# Sea-urchin library sensitivity on the fixed D panel

The separate Dfam 3.9 uncurated lineage comparator is complete. The model,
four regions, cached probabilities, six-species CAL and threshold are unchanged.
Original Label-A remains unchanged and has no qualifying TE-positive bases in
these four regions. The alternative library is not independent biological truth.
Original Label-A was generated from the assembly, whereas the alternative
RepeatMasker input contains the four extracted regions. Annotation context at
region edges therefore differs; this is a bounded comparator-sensitivity
diagnostic, not a complete identical-input library-only causal benchmark.

## Library and coordinate qualification

Taxon 7668 export `12705673` completed with 3,324 consensus sequences. The
initial length audit incorrectly counted only the first wrapped sequence line;
the FASTA supplied to RepeatMasker was complete. Slurm re-audit `12706320`
retained `library_manifest.first_pass.json` and corrected the length metadata.
The complete sequences total **5,216,115 bp**, range **33–20,961 bp**.
The source summary classified 1,154 entries as TE-like, 2,145 as
unknown/unclassified and 25 as other/unparsed; this is only a source-summary
audit. Primary scoring uses strict class assignment on actual annotation rows.

The initial annotation `12705698` failed on long query identifiers. The
short-ID run `12705750` completed, but the subsequent `12705857` rescore did
not restore panel-relative coordinates and is superseded. Corrected annotation
`12705928` completed in 4:45. Final validation and cache-only rescore
**12706353 completed in 1:08** with 4 CPUs and 16 GB.

The final validation requires every annotation query to have an explicit
mapping, checks its local and lifted bounds, and confirms the short-query
sequences equal the original frozen D panel. A nonzero-start fixture checks
RepeatMasker 1-based coordinates and rejection of an unknown query. All
10,021 annotation rows mapped to the four frozen region IDs. Recomputed
lifted output exactly matched the corrected annotation output. No inference
or annotation was rerun during final validation. Raw assets remain on Baobab.

## Actual results

The alternative annotation contains 3,371 strict TE-class rows spanning
**844,932 union bp**, 4,599 unknown/ambiguous rows (1,239,687 union bp;
including PLE under the unchanged class contract), and 2,051 known non-TE rows
(133,506 union bp). These bucket unions can overlap and are not additive.
The callable panel remains 4,192,804 bp.

| Frozen arm | Positive-only TE bp recall | T0 comparator bp F1 |
|---|---:|---:|
| F | 0.428937 | 0.491968 |
| RC mapped back | 0.418908 | 0.487093 |
| F/RC mean | 0.424200 | 0.491484 |
| F/3-bp-phase mean | 0.424027 | 0.488283 |

T1 precision and F1 remain null. T0 assumes the complement as comparator
negative and is not independent accuracy. In particular, the many unknown
annotations are not established true negatives.

This result changes the interpretation of the original empty denominator:
curated-only library selection omitted substantial alternative TE-class
coverage. It also reveals low recovery by the frozen D model on that
alternative coverage, which simple RC/phase averaging does not improve.
Thus external stability is not established. The four selected regions and
uncurated labels do not estimate whole-genome biological accuracy or isolate
the cause of the domain shift.

Next, qualify additional labels and stratify the observed errors by class,
divergence, length and genomic context before choosing an adaptation model.
Any panel used to select such changes becomes development evidence. An adapter
versus dense baseline can precede a bounded MoE experiment; the present result
does not itself demonstrate useful expert complementarity.

Compact provenance and scores are in `results/sea_urchin_uncurated/`.
The remote final output is
`outputs/D-EXTERNAL-RC0-20260914/sea_urchin_uncurated_dfam/finalize-12706353/`.
Original failed or superseded outputs remain in sibling directories.
