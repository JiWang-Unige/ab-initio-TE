# C native-CDS endpoint readiness

Run from project root. Frozen reference eligibility and nine-core geometry are
imported from the original evaluator; its provisional stop-union parser is not used.
Native CDS rows alone determine chains; phase and auxiliary codon rows never move
endpoints. Exact chain metrics on a selected core are descriptive, not scientific PASS.

```
python endpoint.py prepare --config configs/GAP-BRIDGE-C-ENDPOINT-20260906-R1.json
python endpoint.py preflight --config configs/GAP-BRIDGE-C-ENDPOINT-20260906-R1.json
```

Use the script's full repository-relative path. `prepare` creates a new output
directory, copies full core6/core10 plus halo in all three mask modes, and checks
uppercase letters. `preflight` must run in the pinned container: it calls the
installed real `Transcript.to_gtf_rows` for all 330 eligible source transcripts,
requires recovery of the same 243 distinct chains, and checks actual FASTA loader
and six-channel one-hot output for all six prepared FASTAs.

Actual prediction uses only M0. Set `C_ENDPOINT_OBSERVATION` to a fresh JSON path
and invoke `observed_tiberius.py` with normal Tiberius arguments. It wraps the real
`Fasta.one_hot`, validates each returned channel against encoded input (including
padding/reverse-complemented chunks), returns the exact same object, and invokes
the fixed `/opt/Tiberius/tiberius.py` using runpy. The full-FASTA preflight connects
these encoded mask values to source FASTA case. No model or predictor arguments change.

```
python endpoint.py evaluate --config configs/GAP-BRIDGE-C-ENDPOINT-20260906-R1.json \
  --core 6 --gtf output.gtf --gff3 output.gff3 --observation observation.json
```

The evaluator requires GTF/GFF3 equality for all CDS chains, including excluded
halo records and transcript multiplicity, plus verified actual inference calls.
It prints `NONEMPTY_ENDPOINT_READY` or `EMPTY_M0`. The driver may try core10 only
after core6 reports `EMPTY_M0`; neither emptiness nor zero reference matches
authorizes boundary relaxation, extra cores, or three-arm scientific inference.
The actual M0 sequence audit reports start/terminal codons, length modulo three,
and internal in-frame stops on both strands; it never filters chains. Codon counts
are evidence about native CDS terminal-stop semantics, not an accuracy gate.
Full annotation phase progression is not audited in this bounded readiness run.

Tests: `python -m unittest discover -s scripts/experiments/GAP-BRIDGE-C-ENDPOINT-20260906-R1 -p 'test_*.py'`.
Local tests validate parser cases; the allocated container preflight validates
the installed real exporter and FASTA implementation, not a mock.
