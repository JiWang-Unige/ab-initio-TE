"""Original calibration/metrics, with explicit same-tile paired inference."""
import importlib.util
import json
from pathlib import Path

from pair_model import PROTOCOL, install_pair_adapter

SOURCE = Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-INIT-HISTORY-V1" / "evaluate_init.py"
spec = importlib.util.spec_from_file_location("pair_context_evaluation", SOURCE)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)
legacy = evaluation.legacy
native_loader = legacy.load_final_model


def ordered_pairs(records):
    grouped = {}
    for record in records:
        key, half = str(record["tile_id"]), int(record["half"])
        if half not in (0, 1) or half in grouped.setdefault(key, {}):
            raise ValueError(f"invalid or duplicate half in tile {key}")
        grouped[key][half] = record
    for key in sorted(grouped):
        if set(grouped[key]) != {0, 1}:
            raise ValueError(f"incomplete tile {key}")
        left, right = grouped[key][0], grouped[key][1]
        if any(left[field] != right[field] for field in ("assembly", "split", "chrom")):
            raise ValueError(f"mismatched tile metadata: {key}")
        if int(left["end"]) != int(right["start"]):
            raise ValueError(f"noncontiguous tile: {key}")
        if any(int(r["end"]) - int(r["start"]) != 4096 or len(r["sequence"]) != 4096
               or len(r["labels"]) != 4096 for r in (left, right)):
            raise ValueError(f"incorrect original half length: {key}")
        yield left, right


def infer_inputs(model, tokenizer, device, data_specs, batch_size):
    if batch_size != 2:
        raise ValueError("paired inference requires exactly one two-half tile per batch")
    panels = {}
    for species, path in data_specs:
        tiles = []
        for records in ordered_pairs(legacy.read_jsonl(path)):
            margins = legacy.infer_half_margins(
                model, tokenizer, device, [str(r["sequence"]) for r in records], 2,
            )
            tiles.extend(legacy.assemble_tiles(species, list(records), margins))
        panels[species] = tiles
    return panels


def main():
    evaluation.EXPERIMENT_ID = evaluation.PROTOCOL = PROTOCOL
    evaluation.RUN_ROLE = "pair_context_registered_evaluation"
    evaluation.ARM_CHOICES = ("BLOCK4", "PAIR8")
    parser = evaluation.build_parser()
    parser.set_defaults(batch_size=2)
    args = parser.parse_args()

    def loader(*positional, **kwargs):
        model, tokenizer, device = native_loader(*positional, **kwargs)
        if getattr(model.config, "pair_context_protocol", None) != PROTOCOL:
            raise ValueError("not a saved pair-context checkpoint")
        install_pair_adapter(model, args.arm)
        return model, tokenizer, device

    legacy.load_final_model = loader
    legacy.infer_inputs = infer_inputs
    print(json.dumps(evaluation.evaluate_arm(args), indent=2))


if __name__ == "__main__":
    main()
