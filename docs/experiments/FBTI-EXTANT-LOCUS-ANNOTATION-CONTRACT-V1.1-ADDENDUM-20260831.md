# FBTI extant-locus annotation contract V1.1 addendum

Date: 2026-08-31

Status: **implementation-blocking correction after job 12121043**

This addendum changes only the canonical-P3 atom ownership sentence in Section
4 of `FBTI-EXTANT-LOCUS-ANNOTATION-CONTRACT-V1-ADDENDUM-20260831.md`.

Job `12121043` correctly froze 172 pairwise non-overlapping packages, then
stopped while building atom manifests because atom `P3:2R:4923598:4924703`
overlapped more than one selected package. The failed job has no Gate L result
and remains outside every scientific denominator.

Pairwise non-overlap of package intervals does not imply unique package overlap
for an interval-valued atom: one long atom can span the gap between two
packages. Therefore:

1. `package_atoms.tsv` contains one row per `(package_id, atom_id)` with
   positive-length overlap.
2. A canonical atom that overlaps multiple packages is retained once in each
   such package and is `package_censored=1` in every one of those rows.
3. Package-censored atom rows remain excluded from L-D, Gate O and Gate E.
4. Sampling remains independent of P3 geometry. Do not add an atom-ownership
   constraint, change the seed, alter a quota or swap a selected package.

The retry must use a new output directory and the unchanged frozen population,
seed, priority vector, MILP quotas and package non-overlap constraints.
