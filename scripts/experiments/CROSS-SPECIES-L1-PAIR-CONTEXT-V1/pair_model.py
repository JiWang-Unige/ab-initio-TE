"""Experiment-local connectivity adapter; native tensors and source stay intact.

Inputs and outputs retain [2, half_tokens, ...]. Only encoder connectivity is
changed. Loaders must explicitly call install_pair_adapter after checkpoint load;
the saved config records the arm, but does not install executable custom code.
"""
from types import MethodType

import torch
import torch.utils.checkpoint
from transformers.modeling_outputs import BaseModelOutputWithPoolingAndCrossAttentions

PROTOCOL = "CROSS-SPECIES-L1-PAIR-CONTEXT-V1"


def enable_native_checkpointing(model):
    """Native ESM has the encoder path but disables the HF public enable API."""
    model.esm.encoder.gradient_checkpointing = True
    model.config.use_cache = False


def visibility_mask(attention_mask, arm):
    """Valid keys only; padding queries retain own-half keys to avoid NaNs."""
    if arm not in {"BLOCK4", "PAIR8"}:
        raise ValueError(f"unregistered pair arm: {arm}")
    if attention_mask.ndim != 2 or attention_mask.shape[0] != 2:
        raise ValueError("one original tile, encoded as exactly two halves, required")
    if not attention_mask.bool().any(dim=1).all():
        raise ValueError("each half must contain valid keys")
    width = attention_mask.shape[1]
    valid = attention_mask.reshape(-1).bool()
    visible = valid.unsqueeze(0).expand(2 * width, -1)
    if arm == "BLOCK4":
        halves = torch.arange(2, device=attention_mask.device).repeat_interleave(width)
        visible = visible & halves[:, None].eq(halves[None, :])
    return visible[None, None]


def pair_forward(self, input_ids=None, attention_mask=None, position_ids=None,
                 head_mask=None, inputs_embeds=None, output_attentions=None,
                 output_hidden_states=None, return_dict=None):
    if input_ids is None or inputs_embeds is not None or position_ids is not None:
        raise ValueError("registered pair input is original input_ids, with native positions")
    if attention_mask is None or input_ids.shape != attention_mask.shape:
        raise ValueError("original two-half padding mask required")
    visible = visibility_mask(attention_mask, self.config.pair_context_arm)
    # Crucially embed BEFORE packing: preserves per-half token-dropout scaling,
    # native padding semantics, and original token identities and positions.
    embedding = self.embeddings(input_ids=input_ids, attention_mask=attention_mask)
    width, hidden = embedding.shape[1:]
    packed = embedding.reshape(1, 2 * width, hidden)
    additive = (~visible).to(embedding.dtype) * torch.finfo(embedding.dtype).min
    outputs = self.encoder(
        packed, attention_mask=additive,
        head_mask=self.get_head_mask(head_mask, self.config.num_hidden_layers),
        use_cache=False,
        output_attentions=bool(output_attentions),
        output_hidden_states=bool(output_hidden_states), return_dict=True,
    )
    sequence = outputs.last_hidden_state.reshape(2, width, hidden)
    states = (tuple(state.reshape(2, width, hidden) for state in outputs.hidden_states)
              if outputs.hidden_states is not None else None)
    # Attention maps, when requested for wiring tests, remain packed [1,H,2T,2T].
    result = BaseModelOutputWithPoolingAndCrossAttentions(
        last_hidden_state=sequence, hidden_states=states, attentions=outputs.attentions,
    )
    if return_dict is False:
        return (sequence, None) + tuple(x for x in (states, outputs.attentions) if x is not None)
    return result


def install_pair_adapter(model, arm):
    if arm not in {"BLOCK4", "PAIR8"}:
        raise ValueError(f"unregistered pair arm: {arm}")
    config = model.config
    if config.position_embedding_type != "rotary" or config.is_decoder:
        raise ValueError("registered operator requires the rotary encoder")
    if config.hidden_dropout_prob != 0 or config.attention_probs_dropout_prob != 0:
        raise ValueError("registered matched operator requires native zero dropout")
    saved_arm = getattr(config, "pair_context_arm", arm)
    if saved_arm != arm:
        raise ValueError("checkpoint arm does not match requested adapter")
    config.pair_context_arm = arm
    config.pair_context_protocol = PROTOCOL
    model.esm.forward = MethodType(pair_forward, model.esm)
    return model
