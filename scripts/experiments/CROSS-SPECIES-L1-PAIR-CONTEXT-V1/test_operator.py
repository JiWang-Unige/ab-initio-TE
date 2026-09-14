"""Bounded synthetic FP32 native-ESM test; run on a Slurm CPU allocation."""
import argparse
import copy
import json
from pathlib import Path

import torch
from transformers import AutoConfig, AutoModelForTokenClassification

from pair_model import install_pair_adapter, visibility_mask

ATOL, RTOL = 1e-5, 1e-4


def loss(logits, positive, negative):
    logp = logits.float().log_softmax(-1)
    return (-(negative * logp[..., 0] + 3 * positive * logp[..., 1]).sum(1)
            / (3 * positive + negative).sum(1)).mean()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    torch.manual_seed(42)
    config = AutoConfig.from_pretrained(args.base_model, trust_remote_code=True, local_files_only=True)
    config.hidden_size, config.intermediate_size = 32, 64
    config.num_hidden_layers, config.num_attention_heads = 2, 4
    config.num_labels = 2
    native = AutoModelForTokenClassification.from_config(config, trust_remote_code=True).float().eval()
    block = install_pair_adapter(copy.deepcopy(native), "BLOCK4")
    pair = install_pair_adapter(copy.deepcopy(native), "PAIR8")
    ids = torch.randint(4, config.vocab_size, (2, 16))
    mask = torch.ones_like(ids)
    mask[0, -2:], mask[1, -3:] = 0, 0
    ids[mask == 0] = config.pad_token_id
    positive = (torch.arange(32).reshape(2, 16) % 3).float() * mask
    negative = (6 - positive) * mask
    expected = native(input_ids=ids, attention_mask=mask).logits
    actual = block(input_ids=ids, attention_mask=mask).logits
    torch.testing.assert_close(actual[mask.bool()], expected[mask.bool()], atol=ATOL, rtol=RTOL)
    original_loss, packed_loss = loss(expected, positive, negative), loss(actual, positive, negative)
    torch.testing.assert_close(packed_loss, original_loss, atol=ATOL, rtol=RTOL)
    original_loss.backward()
    packed_loss.backward()
    max_gradient_error = 0.0
    for (name, parameter), (other_name, other) in zip(native.named_parameters(), block.named_parameters()):
        assert name == other_name
        if parameter.grad is None:
            assert other.grad is None
            continue
        torch.testing.assert_close(other.grad, parameter.grad, atol=ATOL, rtol=RTOL, msg=name)
        max_gradient_error = max(max_gradient_error, (other.grad - parameter.grad).abs().max().item())
    perturbed = ids.clone()
    perturbed[1, :10] = (perturbed[1, :10] + 1 - 4) % (config.vocab_size - 4) + 4
    with torch.no_grad():
        unchanged = block(input_ids=perturbed, attention_mask=mask).logits
        opened = pair(input_ids=ids, attention_mask=mask, output_attentions=True)
        changed = pair(input_ids=perturbed, attention_mask=mask).logits
    torch.testing.assert_close(unchanged[0], actual[0], atol=ATOL, rtol=RTOL)
    influence = (opened.logits[0][mask[0].bool()] - changed[0][mask[0].bool()]).abs().max().item()
    assert influence > ATOL, "PAIR8 did not show cross-half influence"
    assert not visibility_mask(mask, "BLOCK4")[0, 0, :16, 16:].any()
    assert opened.attentions[0][0, :, :14, 16:29].sum().item() > 0
    assert torch.isfinite(opened.logits).all()
    result = {"status": "PASS", "scope": "synthetic native two-layer ESM only; not real H0 smoke",
              "device": "cpu", "dtype": "float32", "atol": ATOL, "rtol": RTOL,
              "max_valid_logit_error": (actual[mask.bool()] - expected[mask.bool()]).abs().max().item(),
              "loss_error": (packed_loss - original_loss).abs().item(),
              "max_gradient_error": max_gradient_error, "cross_half_logit_change": influence}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
