# Local evidence cache for FUNCTIONAL-MASK-EVIDENCE-20260925

This directory contains a local, reproducible cache for the structural-panel
audit. The downloaded XML, DOCX/ZIP supplement and NCBI assembly reports are
ignored by Git and should not be included in the public repository. The public
release needs only the compact derived tables under `structural_panels/`, this
README, the parent `evidence_manifest.tsv`, and the extraction script.

## Re-download URLs

| input | URL |
|---|---|
| chicken article XML | https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7597685/fullTextXML |
| zebrafish article XML | https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7913693/fullTextXML |
| zebrafish supplementary archive | https://www.ebi.ac.uk/europepmc/webservices/rest/PMC7913693/supplementaryFiles |
| chicken GRCg6a assembly report | https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/002/315/GCA_000002315.5_GRCg6a/GCA_000002315.5_GRCg6a_assembly_report.txt |
| zebrafish GRCz11 assembly report | https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/000/002/035/GCA_000002035.4_GRCz11/GCA_000002035.4_GRCz11_assembly_report.txt |

The Europe PMC supplementary archive contains the nested NAR file
`gkab045_supplemental_files.zip`; its DOCX contains Supplementary Table S4.
The extractor expects the expanded DOCX at the path documented in its default
arguments. If the local cache is absent, download and expand the archive
outside the repository or into this ignored directory, then rerun:

```text
python3 scripts/experiments/FUNCTIONAL-MASK-EVIDENCE-20260925/extract_structural_panels.py
```

The script reads only the independent source files, assembly reports and fixed
core geometry JSON; it does not read D/U/R model outputs.
