import gzip
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

try:
    import numpy as np
    import torch
except ModuleNotFoundError:
    np = None
    torch = None

TorchModule = torch.nn.Module if torch is not None else object


SCRIPT = Path(__file__).with_name("h0_loader_identity.py")
SPEC = importlib.util.spec_from_file_location("h0_loader_identity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def records():
    return [
        {"species_code": "human", "split": "CAL", "sequence": "A" * 4096}
        for _ in range(MODULE.N_RECORDS)
    ]


class RecordTest(unittest.TestCase):
    def test_reads_first_16_human_cal_records(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl.gz") as handle:
            with gzip.open(handle.name, "wt") as output:
                for index in range(MODULE.N_RECORDS + 1):
                    output.write(
                        json.dumps(
                            {
                                "species_code": "human",
                                "split": "CAL",
                                "sequence": "A" * 4096,
                                "index": index,
                            }
                        )
                        + "\n"
                    )
            observed = MODULE.read_records(Path(handle.name))
        self.assertEqual([row["index"] for row in observed], list(range(16)))


@unittest.skipUnless(torch is not None and np is not None, "torch and numpy required")
class NumericGateTest(unittest.TestCase):
    class Tokenizer:
        def __call__(self, sequences, **kwargs):
            batch = len(sequences)
            ids = torch.arange(688).repeat(batch, 1)
            attention = torch.ones_like(ids)
            special = torch.zeros((batch, 689), dtype=ids.dtype)
            special[:, (0, 687)] = 1
            return {
                "input_ids": ids,
                "attention_mask": attention,
                "special_tokens_mask": special,
            }

    class Model(TorchModule):
        def __init__(self, delta=0.0):
            super().__init__()
            self.delta = delta

        def forward(self, input_ids, attention_mask):
            margin = torch.ones_like(input_ids, dtype=torch.float32) + self.delta
            return SimpleNamespace(
                logits=torch.stack((torch.zeros_like(margin), margin), dim=-1)
            )

    @staticmethod
    def project(margins, positions, bp_length):
        output = np.empty(bp_length, dtype=np.float32)
        for chunk, position in enumerate(positions[:682]):
            output[chunk * 6 : (chunk + 1) * 6] = margins[position]
        for offset, position in enumerate(positions[682:]):
            output[4092 + offset] = margins[position]
        return output

    def test_passes_identical_and_fails_changed_logits(self):
        same = MODULE.compare(
            self.Model(), self.Tokenizer(), self.Model(), self.Tokenizer(), records(), self.project
        )
        changed = MODULE.compare(
            self.Model(),
            self.Tokenizer(),
            self.Model(delta=2e-5),
            self.Tokenizer(),
            records(),
            self.project,
        )
        self.assertEqual(same["status"], "PASS")
        self.assertEqual(changed["status"], "FAIL")
        self.assertEqual(changed["next_action"], "repair loader")


if __name__ == "__main__":
    unittest.main()
