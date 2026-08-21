# Dossier: Dfam 3.9 authoritative curated EMBL alias/accession source

- slug: `dfam39-authoritative-alias` · type: note · added: 2026-08-12
- Links: Dfam 3.9 release `https://www.dfam.org/releases/Dfam_3.9/`; family index `https://www.dfam.org/releases/Dfam_3.9/families/`; release notes `https://www.dfam.org/releases/Dfam_3.9/relnotes.txt`
- PDF: refs/pdfs/dfam39-authoritative-alias.pdf (none)
- Repo: refs/repos/dfam39-authoritative-alias/ (none)
- Supplementary: refs/supp/dfam39-authoritative-alias/ (downloaded(3))
- Why relevant: Freeze Dfam 3.9 AC/ID/PI/SN/DR/SQ evidence for the 279 unresolved RepeatMasker identifiers; no current-release drift.

## Dataset source (verified)
- Release: Dfam `3.9`; the release notes identify `Dfam-curated_only-1.embl.gz` as the curated-DF consensus export and define `AC`, `ID`, `DR`, `PI`, `SN`, and `SQ` fields.
- Frozen payload: `refs/supp/dfam39-authoritative-alias/supp-1.gz`, 25,501,240 bytes, SHA-256 `8bbe1d3dd0c772ca4e55d9f4f84e00faf4101af74ffdcc380bcd35fef9f85050`.
- Official MD5 sidecar: `refs/supp/dfam39-authoritative-alias/supp-2.dat`, SHA-256 `57fbebec45465d930d59d30f57d3328d2e40127130e5707e2cbe56cd319c8f26`; declared/observed MD5 `c1cd35fc6b3a9569f18d06a5f01c935a`.
- Frozen release notes: `refs/supp/dfam39-authoritative-alias/supp-3.txt`, SHA-256 `506783775a32b646ef3bdc239249144da7a86137b867e1a2d4b904d20165083f`.
- License: Dfam Consortium CC0 1.0/public-domain dedication, stated in the Dfam 3.9 release notes. No Repbase payload is redistributed or inferred.

## Metric implementation
- This is an identity/provenance audit, not a biological performance metric. Primary evidence is exact identifier and occurrence coverage under official `ID`/`PI`/`SN`/`DR` relations.
- Unique resolution requires one distinct `(versioned Dfam accession, normalized consensus SHA-256)` identity. One-to-many relations remain `ambiguous`; no prefix, case-fold, substring, taxonomy, label, or genome-copy tie-break is allowed.

## Split scheme
- No split is constructed in this audit. Resolution reads only the frozen identifier denominator and official Dfam source. Species, labels, clades, and future split roles may be joined only after the resolution table is frozen.
- A metamorphic test must show that permuting labels/species/future split roles does not change the resolution payload hash.

## Weights / license
- No model weights. Source license is CC0 1.0 as above.

## Reproducibility notes
- The live Dfam API currently follows the current release and is not accepted as the frozen Dfam 3.9 authority for this route.
- Preliminary target-limited streaming evidence finds partial, not complete, recovery and real one-to-many cases (`L1HS`, `L1PREC2`). The formal audit must therefore be capable of a valid-negative typed block and must not presuppose 279/279 recovery.

## Relevance to our project
- Freeze Dfam 3.9 AC/ID/PI/SN/DR/SQ evidence for the 279 unresolved RepeatMasker identifiers; no current-release drift.
- This source can propose accession-backed homology identities without changing direct-superfamily labels. It cannot by itself authorize homology split, DATA, GPU S0, or hierarchical S1.
