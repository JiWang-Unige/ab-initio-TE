"""Real-H0 FP32 operator equivalence and matched 24GB training cost probe.

TRAIN only. No CAL/DEV/SCREEN or scientific selection. All numerical tolerances
are the protocol's predeclared values. A failure is preserved, never relaxed.
"""
import argparse
import gc
import json
import time
from pathlib import Path

import torch

from pair_model import PROTOCOL, install_pair_adapter, enable_native_checkpointing
from train_pair import legacy
from evaluate_pair import ordered_pairs

ATOL, RTOL = 1e-5, 1e-4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--upstream-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    log = (args.output_dir / "events.jsonl").open("x", buffering=1)

    def record(event, **values):
        row = {"event": event, **values}
        log.write(json.dumps(row) + "\n")
        print(json.dumps(row), flush=True)

    torch.set_num_threads(4)
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    record("start", protocol=PROTOCOL, device=torch.cuda.get_device_name(),
           torch=torch.__version__, atol=ATOL, rtol=RTOL, activation_checkpointing=True)
    datasets = {}
    for species in legacy.SPECIES:
        root = args.upstream_root if species == "c_elegans" else args.data_root
        dataset = legacy.SpeciesTileDataset(root / "TRAIN" / f"{species}.jsonl.gz", species)
        expected_count = 3000 if species == "c_elegans" else 1500
        if len(dataset.tile_ids) != expected_count:
            raise ValueError(f"wrong frozen TRAIN count for {species}")
        # Validate all original TRAIN pair metadata, not just the smoke example.
        for tile_id in dataset.tile_ids:
            list(ordered_pairs(dataset.pair(tile_id)))
        datasets[species] = dataset
    record("train_pairing_pass", counts={s: len(d.tile_ids) for s, d in datasets.items()})
    model, tokenizer = legacy.load_model_and_tokenizer()
    native_forward = model.esm.forward
    enable_native_checkpointing(model)
    model.to("cuda").train()
    batches = {}
    for species, dataset in datasets.items():
        records = dataset.pair(dataset.tile_ids[0])
        batch = legacy.encode_pair(tokenizer, records)
        for half, source in enumerate(records):
            assert batch["positive_bp"][half].sum().item() == source["labels"].count("1")
            assert batch["negative_bp"][half].sum().item() == sum(source["labels"].count(x) for x in ("0", "H"))
            assert len(legacy.sequence_tokens(source["sequence"])[-4:]) == 4
        batches[species] = {k: v.to("cuda") for k, v in batch.items()}
    del datasets
    record("encoding_pass", shapes={s: list(b["input_ids"].shape) for s, b in batches.items()})
    numerical = batches["c_elegans"]

    def forward_loss(batch):
        logits = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
        return logits, legacy.bp_weighted_pair_loss(logits, batch["positive_bp"], batch["negative_bp"])

    logits, original_loss = forward_loss(numerical)
    original_loss.backward()
    expected = logits.detach().cpu()
    expected_loss = original_loss.detach().cpu()
    gradients = {name: p.grad.detach().cpu().clone() for name, p in model.named_parameters() if p.grad is not None}
    del logits, original_loss
    model.zero_grad(set_to_none=True)
    record("native_fp32_complete", loss=expected_loss.item())
    install_pair_adapter(model, "BLOCK4")
    logits, actual_loss = forward_loss(numerical)
    actual_loss.backward()
    valid = numerical["attention_mask"].bool().cpu()
    torch.testing.assert_close(logits.detach().cpu()[valid], expected[valid], atol=ATOL, rtol=RTOL)
    torch.testing.assert_close(actual_loss.detach().cpu(), expected_loss, atol=ATOL, rtol=RTOL)
    max_gradient_error = 0.0
    for name, p in model.named_parameters():
        if name not in gradients:
            assert p.grad is None
            continue
        actual_grad = p.grad.detach().cpu()
        torch.testing.assert_close(actual_grad, gradients[name], atol=ATOL, rtol=RTOL, msg=name)
        max_gradient_error = max(max_gradient_error, (actual_grad - gradients[name]).abs().max().item())
    record("real_h0_fp32_equivalence_pass",
           max_valid_logit_error=(logits.detach().cpu()[valid] - expected[valid]).abs().max().item(),
           loss_error=abs(actual_loss.item() - expected_loss.item()),
           max_gradient_error=max_gradient_error)
    del gradients, actual_grad, logits, actual_loss
    model.zero_grad(set_to_none=True)
    gc.collect()
    torch.cuda.empty_cache()

    perturbed = {k: v.clone() for k, v in numerical.items()}
    right_valid = perturbed["attention_mask"][1].bool()
    perturbed["input_ids"][1, right_valid] = perturbed["input_ids"][1, right_valid].flip(0)
    with torch.no_grad():
        blocked, _ = forward_loss(perturbed)
        torch.testing.assert_close(blocked[0].cpu()[valid[0]], expected[0][valid[0]], atol=ATOL, rtol=RTOL)
        model.config.pair_context_arm = "PAIR8"
        opened, _ = forward_loss(numerical)
        changed, _ = forward_loss(perturbed)
        influence = (opened[0][valid[0].to("cuda")] - changed[0][valid[0].to("cuda")]).abs().max().item()
        if influence <= ATOL:
            raise ValueError("no resolved real-H0 cross-half influence")
        model.config.pair_context_arm = "BLOCK4"
    del blocked, opened, changed, perturbed
    record("real_h0_cross_half_influence_pass", max_left_logit_change=influence)

    # Exercise on-disk state/config restoration and explicit adapter reinstall.
    checkpoint = args.output_dir / "reload_checkpoint"
    model.save_pretrained(checkpoint, safe_serialization=False)
    from transformers import AutoConfig
    restored_config = AutoConfig.from_pretrained(checkpoint, trust_remote_code=True, local_files_only=True)
    assert restored_config.pair_context_arm == "BLOCK4"
    assert restored_config.pair_context_protocol == PROTOCOL
    state = torch.load(checkpoint / "pytorch_model.bin", map_location="cpu")
    model.load_state_dict(state, strict=True)
    del state
    model.esm.forward = native_forward
    install_pair_adapter(model, restored_config.pair_context_arm)
    with torch.no_grad():
        restored, _ = forward_loss(numerical)
    torch.testing.assert_close(restored.cpu()[valid], expected[valid], atol=ATOL, rtol=RTOL)
    del restored
    record("checkpoint_state_and_adapter_reload_pass")

    # Same full six-species update path in both arms, including AdamW state.
    # Restoring H0 before each arm keeps this an engineering comparison only.
    for arm in ("BLOCK4", "PAIR8"):
        state = torch.load(legacy.H0_CHECKPOINT / "pytorch_model.bin", map_location="cpu")
        model.load_state_dict(state, strict=True)
        del state
        # Explicit switch is restricted to this two-arm smoke, never a checkpoint loader.
        model.config.pair_context_arm = arm
        install_pair_adapter(model, arm)
        optimizer = legacy.build_optimizer(model)
        elapsed = []
        torch.cuda.reset_peak_memory_stats()
        for step in range(5):
            torch.cuda.synchronize()
            started = time.perf_counter()
            optimizer.zero_grad(set_to_none=True)
            losses = []
            for species in legacy.SPECIES:
                with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
                    logits, value = forward_loss(batches[species])
                if not torch.isfinite(value):
                    raise ValueError(f"nonfinite {arm} loss")
                (value / len(legacy.SPECIES)).backward()
                losses.append(value.item())
                del logits, value
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), legacy.MAX_GRAD_NORM)
            if not torch.isfinite(norm):
                raise ValueError(f"nonfinite {arm} gradient")
            optimizer.step()
            torch.cuda.synchronize()
            duration = time.perf_counter() - started
            elapsed.append(duration)
            record("timing_step", arm=arm, step=step + 1, seconds=duration, losses=losses)
        record("timing_arm_complete", arm=arm, warmed_step_seconds=max(elapsed[2:]),
               peak_allocated_bytes=torch.cuda.max_memory_allocated(),
               peak_reserved_bytes=torch.cuda.max_memory_reserved(),
               projected_4000_step_seconds=4000 * max(elapsed[2:]))
        optimizer.zero_grad(set_to_none=True)
        del optimizer
        gc.collect()
        torch.cuda.empty_cache()
        # Original evaluator is FP32/no-autocast. Time this exact model path on
        # TRAIN only; it predicts evaluation cost without opening any eval panel.
        model.eval()
        durations = []
        with torch.no_grad():
            for step in range(5):
                torch.cuda.synchronize()
                started = time.perf_counter()
                predicted = model(input_ids=numerical["input_ids"],
                                  attention_mask=numerical["attention_mask"]).logits
                margins = (predicted[..., 1] - predicted[..., 0]).cpu().numpy()
                torch.cuda.synchronize()
                durations.append(time.perf_counter() - started)
        record("inference_timing", arm=arm, fp32_pair_seconds=max(durations[2:]))
        del predicted, margins
        model.train()
    record("PASS", scope="real-H0 numerical and matched training-cost smoke only",
           scientific_evidence=False)


if __name__ == "__main__":
    main()
