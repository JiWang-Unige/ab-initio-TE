# TEFM hierarchical ontology mapping contract v0.1

Date: 2026-08-08  
Status: preregistered normalization contract; not a performance result

## Authoritative basis

1. EDTA v2.3.0 commit `a9f7a56d6a1c1a9cdcf2a1d7b8c27a74a38dbfc2`, `bin/TE_Sequence_Ontology.txt`:
   - 14,710 bytes;
   - Git blob `44f1fc38c6abbbb84a56025bfaf608801900ff3a` (local `git hash-object` equals GitHub API);
   - SHA-256 `b7674909edb6672af4ff0efd0c7cbf341394f10981ab8b9c55f2e0969b1668a0`.
2. Wicker et al. (2007), *A unified classification system for eukaryotic transposable elements*, Nature Reviews Genetics 8:973–982, DOI `10.1038/nrg2165`.
3. Raw source labels must be retained; normalization never erases the original label or its source tool/version.

EDTA's official README states that its libraries use Wicker three-letter superfamily codes and directs users to the bundled ontology file. The bundled file explicitly lists aliases such as `LTR/RLG`, `RLG`, `LTR/Gypsy`, `DNA/DTA`, `MITE/DTA`, and `DNAauto/hAT` under the same Sequence Ontology concepts.

## Required normalized fields

Every interval/library record must carry:

- `raw_label`;
- `source_tool` and `source_version`;
- `ontology_version`;
- `biological_status`: `TE`, `TE_LIKE_SENSITIVITY_REQUIRED`, `NON_TE`, or `UNRESOLVED`;
- `class`: `Class_I`, `Class_II`, or `UNRESOLVED`;
- `order`: e.g. `LTR`, `LINE`, `SINE`, `TIR`, `Helitron`, `YR`, `Penelope`, `Maverick`, or `UNRESOLVED`;
- `superfamily`: a named superfamily or `UNRESOLVED`;
- `structural_modifier`: e.g. `MITE`, `TRIM`, `LARD`, `Solo_LTR`, or empty;
- `mapping_source`: exact official alias, Wicker code, tool-native explicit label, or unresolved;
- `mapping_confidence`: `exact`, `parent_only`, or `unresolved`.

Broad-class matching and superfamily matching are separate endpoints. A `parent_only` label may score at class/order level but must not count as a correct superfamily call.

## Frozen exact Wicker/EDTA mappings

| Accepted aliases/codes | Class | Order | Superfamily | Canonical display |
|---|---|---|---|---|
| `RLG`, `LTR/RLG`, `LTR/Gypsy`, `Gypsy` | Class_I | LTR | Gypsy | `LTR/Gypsy` |
| `RLC`, `LTR/RLC`, `LTR/Copia`, `Copia` | Class_I | LTR | Copia | `LTR/Copia` |
| `RLB`, `LTR/RLB`, `LTR/Bel-Pao` | Class_I | LTR | Bel-Pao | `LTR/Bel-Pao` |
| `RLE`, `LTR/RLE`, `LTR/ERV` | Class_I | LTR | Endogenous_Retrovirus | `LTR/ERV` |
| `RLR`, `LTR/RLR`, `LTR/Retrovirus` | Class_I | LTR | Retrovirus | `LTR/Retrovirus` |
| `RLX`, `LTR/unknown`, `LTR/Unknown` | Class_I | LTR | UNRESOLVED | `LTR/UNRESOLVED` |
| `RIR`, `LINE/RIR`, `LINE/R2` | Class_I | LINE | R2 | `LINE/R2` |
| `RIJ`, `LINE/RIJ`, `LINE/Jockey` | Class_I | LINE | Jockey | `LINE/Jockey` |
| `RIL`, `LINE/RIL`, `LINE/L1` | Class_I | LINE | L1 | `LINE/L1` |
| `RII`, `LINE/RII`, `LINE/I` | Class_I | LINE | I | `LINE/I` |
| `RIT`, `LINE/RIT`, `LINE/RTE` | Class_I | LINE | RTE | `LINE/RTE` |
| `RIX`, `LINE/unknown`, `LINE/Unknown` | Class_I | LINE | UNRESOLVED | `LINE/UNRESOLVED` |
| `RST`, `SINE/RST`, `SINE/tRNA` | Class_I | SINE | tRNA | `SINE/tRNA` |
| `RSS`, `SINE/RSS`, `SINE/5S` | Class_I | SINE | 5S | `SINE/5S` |
| `RSL`, `SINE/RSL`, `SINE/7SL` | Class_I | SINE | 7SL | `SINE/7SL` |
| `SIX`, `SINE/unknown`, `SINE/Unknown` | Class_I | SINE | UNRESOLVED | `SINE/UNRESOLVED` |
| `RYN`, `YR/RYN`, `YR/Ngaro` | Class_I | YR | Ngaro | `YR/Ngaro` |
| `RYD`, `YR/RYD`, `YR/DIRS` | Class_I | YR | DIRS | `YR/DIRS` |
| `RYV`, `YR/RYV`, `YR/Viper` | Class_I | YR | Viper | `YR/Viper` |
| `RPP`, `nonLTR/RPP`, `Penelope` | Class_I | Penelope | Penelope | `Penelope/Penelope` |
| `DTA`, `DNA/DTA`, `DNAauto/hAT`, `DNAnona/hAT` | Class_II | TIR | hAT | `TIR/hAT` |
| `DTC`, `DNA/DTC`, `DNAauto/CACTA`, `DNAnona/CACTA`, `DNAauto/CACTG`, `DNAnona/CACTG` | Class_II | TIR | CACTA | `TIR/CACTA` |
| `DTM`, `DNA/DTM`, `DNAauto/MULE`, `DNAnona/MULE`, `DNAnona/MULEtir` | Class_II | TIR | Mutator | `TIR/Mutator` |
| `DTH`, `DNA/DTH`, `DNAnona/Tourist` | Class_II | TIR | PIF-Harbinger | `TIR/PIF-Harbinger` |
| `DTT`, `DNA/DTT`, `DNAauto/MLE`, `DNAnona/MLE`, `MITE/Stow` | Class_II | TIR | Tc1-Mariner | `TIR/Tc1-Mariner` |
| `DTP`, `DNA/DTP` | Class_II | TIR | P | `TIR/P` |
| `DTB`, `DNA/DTB` | Class_II | TIR | PiggyBac | `TIR/PiggyBac` |
| `DTR`, `DNA/DTR` | Class_II | TIR | Transib | `TIR/Transib` |
| `DTE`, `DNA/DTE` | Class_II | TIR | Merlin | `TIR/Merlin` |
| `DTX`, `DNA/DTX`, `TIR/unknown`, `DNAauto/unknown`, `DNAnona/unknown` | Class_II | TIR | UNRESOLVED | `TIR/UNRESOLVED` |
| `DHH`, `DNA/Helitron`, `DNAauto/Helitron`, `DNAnona/Helitron`, `RC/Helitron` | Class_II | Helitron | Helitron | `Helitron/Helitron` |
| `DYC`, `DNA/DYC`, `DNA/Crypton` | Class_II | YR | Crypton | `YR/Crypton` |
| `DXX`, `DNA/unknown`, `DNA/Unknown` | Class_II | UNRESOLVED | UNRESOLVED | `DNA/UNRESOLVED` |

For `MITE/<code>` aliases, the code determines the superfamily and `structural_modifier=MITE`; for example `MITE/DTA` is Class_II/TIR/hAT with modifier MITE. `MITE` alone is parent-only and cannot score as a superfamily call. Likewise `LTR/TRIM`, `LTR/LARD` and `LTR/Solo` preserve their structural modifier but do not invent a Copia/Gypsy superfamily.

## Non-TE and sensitivity-required mappings

- Official aliases for `centromeric_repeat`, including `Centro/tandem`, map to `NON_TE`.
- `Simple_repeat`, `Low_complexity`, satellite, telomeric, subtelomeric, rDNA/RNA and organellar-DNA ontology paths map to `NON_TE` for the TE benchmark.
- `Evirus/ERTBV*` maps to `TE_LIKE_SENSITIVITY_REQUIRED`, order `pararetrovirus`, superfamily `ERTBV`. It is retained in the frozen Rice primary positive set but must also be reported in an exclusion sensitivity analysis.
- Generic `repeat_region`, `repeat_fragment`, `Unknown`, `NA` and empty labels are `UNRESOLVED`, never automatically TE-positive and never a superfamily match.
- Sequence parts such as TSD, PBS, LTR part, RR tract and TIR part are feature parts, not independent TE instances.

## Parser and evaluator gates

1. Input aliases are trimmed and Unicode-normalized, but case-sensitive exact official aliases are attempted before any controlled case-folded fallback.
2. UTF-8 and UTF-8 with BOM are accepted; locale defaults must not change parsing.
3. Duplicate alias definitions resolving to conflicting canonical nodes are fatal at ontology-build time.
4. Unrecognized labels are counted and emitted in an audit table; they are not coerced to a known class.
5. Raw, class, order, superfamily and modifier metrics are all reported separately.
6. Ontology version/hash is included in immutable run identity and result provenance.
7. A benchmark run is not ontology-clean if a known frozen alias such as `RLG`, `RLC` or `DTA` resolves to `Unknown`.

## Required minimum tests

- Exact positive tests for every row in the frozen table above.
- `MITE/DTA` maps to hAT plus modifier MITE; it must not become an unqualified generic DNA label.
- `Centro/tandem`, `Simple_repeat` and `Low_complexity` are non-TE.
- Unknown labels remain unresolved and increment the audit counter.
- Mixed input order produces byte-identical normalized output after canonical sorting.
- Mapping artifacts with duplicate conflicting aliases are rejected.
- `RLG`, `RLC` and `DTA` must never normalize to `Unknown`.

Machine-readable oracle: `evidence/ontology_edta_v230/tefm_ontology_oracle_v0_1.tsv`, 2,642 bytes, SHA-256 `c766485083033c83708c90ffcc812994cf1833d663b752e43a8487265ea590fa`.
