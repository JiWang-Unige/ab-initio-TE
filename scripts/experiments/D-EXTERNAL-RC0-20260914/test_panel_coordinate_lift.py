#!/usr/bin/env python3
"""Small non-zero-start regression for panel ID and coordinate lifting."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from panel_coordinate_lift import lift_repeatmasker_out  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="d-panel-lift-") as root:
        base = Path(root)
        raw = base / "raw.out"
        mapping = base / "id_map.tsv"
        lifted = base / "lifted.out"
        mapping.write_text(
            "short_id\tfrozen_region_id\tfrozen_start_bp\tfrozen_end_bp\n"
            "sea_r01\tsea__r01__contig__1000_1100\t1000\t1100\n"
            "sea_r02\tsea__r02__contig__2000_2100\t2000\t2100\n"
            "sea_r03\tsea__r03__contig__3000_3100\t3000\t3100\n"
            "sea_r04\tsea__r04__contig__4000_4100\t4000\t4100\n",
            encoding="utf-8",
        )
        raw.write_text(
            "   1  0.0  0.0  0.0 sea_r01 2 20 (80) + name LINE/L1\n",
            encoding="utf-8",
        )
        result = lift_repeatmasker_out(raw, mapping, lifted)
        fields = lifted.read_text(encoding="utf-8").split()
        assert result == {"rows": 1, "mapped_region_ids": ["sea__r01__contig__1000_1100"]}
        assert fields[4] == "sea__r01__contig__1000_1100"
        assert fields[5:7] == ["1002", "1020"]
        bad = base / "bad.out"
        bad.write_text(
            "   1  0.0  0.0  0.0 unknown 2 20 (80) + name LINE/L1\n",
            encoding="utf-8",
        )
        try:
            lift_repeatmasker_out(bad, mapping, base / "bad.lifted.out")
        except ValueError as exc:
            assert "unmapped query ID" in str(exc)
        else:
            raise AssertionError("unknown query ID was silently accepted")
    print("{\"status\":\"PASS\",\"nonzero_start\":1000,\"lifted_begin\":1002,\"lifted_end\":1020}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
