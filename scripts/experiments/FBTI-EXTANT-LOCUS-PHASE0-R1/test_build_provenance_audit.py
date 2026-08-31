#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "build_provenance_audit", HERE / "build_provenance_audit.py"
)
assert SPEC is not None and SPEC.loader is not None
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class BuildProvenanceAuditTest(unittest.TestCase):
    def test_builds_prefilled_integrity_and_blank_deep_judgement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle"
            packet = bundle / "packets" / "MAIN-001"
            packet.mkdir(parents=True)
            packages = root / "packages.tsv"
            packet_manifest = bundle / "packet_manifest.tsv"
            output = root / "provenance.tsv"

            packages.write_text(
                "package_id\tassembly_id\tfeature_ids\tdeep_audit_feature_id\n"
                "S0-1\tdmel_r6.68\tFBti1\tFBti1\n",
                encoding="utf-8",
            )
            packet_manifest.write_text(
                "packet_id\tpackage_id\nMAIN-001\tS0-1\n", encoding="utf-8"
            )
            (packet / "context_features.tsv").write_text(
                "packet_id\tfeature_id\tseqid\tstart0\tend0\n"
                "MAIN-001\tFBti1\t2L\t100\t150\n",
                encoding="utf-8",
            )
            (packet / "raw_flybase_features.gff3").write_text(
                "2L\tFlyBase\ttransposable_element\t101\t150\t.\t+\t.\tID=FBti1\n",
                encoding="utf-8",
            )

            audit.build_provenance_audit(
                packages, packet_manifest, bundle, "dmel_r6.68", output
            )
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["manifest_start"], "100")
            self.assertEqual(rows[0]["source_start"], "100")
            self.assertEqual(rows[0]["evidence_codes"], "FLYBASE_FEATURE_RECORD")
            self.assertEqual(rows[0]["deep_audit"], "1")
            self.assertEqual(rows[0]["anchor_interpretability"], "")


if __name__ == "__main__":
    unittest.main()
