"""Matched complete-H0 connectivity arms, reusing the frozen D training loop."""
import argparse
import importlib.util
from pathlib import Path

from pair_model import PROTOCOL, install_pair_adapter, enable_native_checkpointing

LEGACY_PATH = Path(__file__).resolve().parents[1] / "CROSS-SPECIES-L1-20260903" / "cross_species_token_task.py"
spec = importlib.util.spec_from_file_location("pair_context_legacy", LEGACY_PATH)
legacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("BLOCK4", "PAIR8"), required=True)
    parser.add_argument("--seed", type=int, choices=(42, 17), default=42)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--engineering-smoke", action="store_true")
    parser.add_argument("--activation-checkpointing", action="store_true",
                        help="Identical memory strategy for both arms, fixed before science")
    args = parser.parse_args()
    pair_arm = args.arm
    legacy.torch.backends.cuda.matmul.allow_tf32 = False
    legacy.torch.backends.cudnn.allow_tf32 = False

    def loader():
        # Unlike INIT-HISTORY this retains the complete H0 classifier as well.
        model, tokenizer = legacy.load_model_and_tokenizer()
        install_pair_adapter(model, pair_arm)
        if args.activation_checkpointing:
            enable_native_checkpointing(model)
        model.config.pair_activation_checkpointing = args.activation_checkpointing
        return model, tokenizer, {
            "protocol": PROTOCOL, "arm": pair_arm,
            "base_model": str(legacy.BASE_MODEL),
            "encoder_source": str(legacy.H0_CHECKPOINT / "pytorch_model.bin"),
            "head_source": "same complete H0 checkpoint; no reinitialization",
            "activation_checkpointing": args.activation_checkpointing,
            "reload": "load native checkpoint then explicitly install_pair_adapter(model, arm)",
        }

    args.experiment_arm, args.arm, args.species = pair_arm, "B1", None
    args.protocol = PROTOCOL
    args.run_role = "pair_context_engineering_smoke" if args.engineering_smoke else "pair_context_registered_training"
    args.max_steps, args.warmup_steps = (4 if args.engineering_smoke else 4000), 400
    args.collect_exposure = True
    args.species_data = [f"c_elegans={args.upstream_root / 'TRAIN' / 'c_elegans.jsonl.gz'}"]
    legacy.train(args, model_loader=loader)


if __name__ == "__main__":
    main()
