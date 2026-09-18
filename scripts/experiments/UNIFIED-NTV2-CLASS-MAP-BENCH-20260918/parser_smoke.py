#!/usr/bin/env python3
"""Small deterministic fixture for the frozen native class-map parsers.

The fixture is intentionally about parser semantics rather than biological
performance.  It catches the two failures that would change a class score:
source non-TE rows becoming TE, and removal of a complete LTR body because it
has structural LTR children.
"""
from __future__ import annotations

import gzip
import tempfile
from pathlib import Path

import numpy as np

from score_class_maps import LABEL2ID, paint, parse_edta, parse_rm2, parse_source, split_class
from score_class_maps import method_metrics


def write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def write_gz(path: Path, text: str) -> Path:
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(text)
    return path


def main() -> None:
    assert split_class("LINE/CR1") == LABEL2ID["LINE"]
    assert split_class("DNA/TIR") == LABEL2ID["DNA"]
    assert split_class("DNA?") == LABEL2ID["AMBIGUOUS_TE"]
    assert split_class("Unknown") == LABEL2ID["UNCLASSIFIED"]
    assert split_class("Simple_repeat", native=False) == LABEL2ID["BG"]
    assert split_class("Simple_repeat", native=True) is None

    sequences = {"chr1": "A" * 120}
    with tempfile.TemporaryDirectory(prefix="classmap-parser-smoke-") as temp:
        root = Path(temp)
        source_text = "\n".join(
            [
                "0 0 0 0 0 chr1 0 10 0 + rep LINE L1 0 10 0 1",
                "0 0 0 0 0 chr1 20 30 0 + rep Simple_repeat Simple_repeat 0 10 0 2",
                "0 0 0 0 0 chr1 40 50 0 + rep Unknown Unknown 0 10 0 3",
            ]
        ) + "\n"
        source, source_stats = parse_source(write_gz(root / "rmsk.txt.gz", source_text), sequences)
        assert source["chr1"][0] == LABEL2ID["LINE"]
        assert source["chr1"][20] == LABEL2ID["BG"]
        assert source["chr1"][40] == LABEL2ID["UNCLASSIFIED"]
        assert source_stats["source_unknown_bp"] == 10

        rm2_text = "\n".join(
            [
                "0 0.0 0.0 0.0 chr1 1 10 (0) + rep1 LINE/L1 0 10 0",
                "0 0.0 0.0 0.0 chr1 21 30 (0) + rep2 Simple_repeat 0 10 0",
                "0 0.0 0.0 0.0 chr1 41 50 (0) + rep3 Unknown 0 10 0",
            ]
        ) + "\n"
        rm2, rm2_stats = parse_rm2(write(root / "annotation.out", rm2_text), sequences)
        assert rm2_stats["included_rows"] == 2
        assert rm2_stats["skipped_non_te_rows"] == 1
        assert rm2["chr1"][0][2] == LABEL2ID["LINE"]

        edta_text = "\n".join(
            [
                "##gff-version 3",
                "chr1\tEDTA\trepeat_region\t1\t20\t.\t+\t.\tID=container1",
                "chr1\tEDTA\tLTR_retrotransposon\t1\t20\t.\t+\t.\tID=body1;Parent=container1;classification=LTR/Gypsy",
                "chr1\tEDTA\tlong_terminal_repeat\t1\t3\t.\t+\t.\tParent=body1",
                "chr1\tEDTA\tlong_terminal_repeat\t18\t20\t.\t+\t.\tParent=body1",
                "chr1\tEDTA\trepeat_region\t30\t40\t.\t+\t.\tID=container2;classification=LINE/L1",
                "chr1\tEDTA\tmatch_part\t30\t35\t.\t+\t.\tID=part2;Parent=container2;classification=LINE/L1",
                "chr1\tEDTA\tregion\t50\t100\t.\t+\t.\tID=region1;classification=LINE/L1",
                "chr1\tEDTA\trepeat\t60\t70\t.\t+\t.\tclassification=DNA/TIR",
                "chr1\tEDTA\trepeat\t80\t90\t.\t+\t.\tclassification=Simple_repeat",
                "chr1\tEDTA\trepeat\t95\t105\t.\t+\t.\tclassification=Unknown",
            ]
        ) + "\n"
        edta, edta_stats = parse_edta(write(root / "annotation.gff3", edta_text), sequences)
        assert edta_stats["suppressed_parent_rows"] == 1
        assert edta_stats["suppressed_parent_reasons"] == {"container_replaced_by_child": 1}
        assert edta_stats["retained_feature_rows"]["ltr_retrotransposon"] == 1
        edta_array = paint(120, edta["chr1"])
        assert edta_array[0] == LABEL2ID["LTR"] and edta_array[19] == LABEL2ID["LTR"]
        assert edta_array[29] == LABEL2ID["LINE"] and edta_array[35] == LABEL2ID["BG"]
        assert edta_array[59] == LABEL2ID["DNA"] and edta_array[69] == LABEL2ID["DNA"]
        assert edta_array[79] == LABEL2ID["BG"] and edta_array[89] == LABEL2ID["BG"]
        assert edta_array[94] == LABEL2ID["UNCLASSIFIED"] and edta_array[104] == LABEL2ID["UNCLASSIFIED"]
        assert all(interval[2] != LABEL2ID["BG"] for interval in edta["chr1"])

        reference = np.full(120, LABEL2ID["BG"], dtype=np.int8)
        prediction = np.full(120, LABEL2ID["BG"], dtype=np.int8)
        reference[0:10] = LABEL2ID["LINE"]
        prediction[0:10] = LABEL2ID["LINE"]
        reference[20:30] = LABEL2ID["UNCLASSIFIED"]
        prediction[20:30] = LABEL2ID["LINE"]
        metrics = method_metrics({"chr1": reference}, {"chr1": prediction}, sequences)
        assert metrics["source_unknown_unclassified_bp"] == 10
        assert metrics["primary_known"]["per_class"]["LINE"]["tp_bp"] == 10
        assert metrics["full8"]["confusion_rows_true_cols_pred_bp"][LABEL2ID["UNCLASSIFIED"]][LABEL2ID["LINE"]] == 10

    print("parser_smoke: PASS")


if __name__ == "__main__":
    main()
