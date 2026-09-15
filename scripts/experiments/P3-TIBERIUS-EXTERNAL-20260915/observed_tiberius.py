#!/usr/bin/env python3
"""Observe actual FASTA encoding and LSTM input in both official model modes."""
import json
import os
from pathlib import Path
import runpy
import sys
import numpy as np
from bricks2marble.struct.fasta import Fasta

sys.path.insert(0, '/opt/Tiberius')
from tiberius.eval_model_class import PredictionGTF

target = Path(os.environ['TIB_OBSERVATION'])
channels = int(os.environ['TIB_EXPECTED_CHANNELS'])
original = Fasta.one_hot
original_predict = PredictionGTF.lstm_prediction
audit = {'passed': True, 'encoding_calls': 0, 'model_calls': 0,
         'expected_channels': channels, 'masked_positions': 0, 'positions': 0}


def observed(self, *args, **kwargs):
    result = original(self, *args, **kwargs)
    if result.shape != (*self.nuc.shape, channels):
        raise ValueError('actual encoding differs from specified checkpoint channel count')
    mask = self.nuc > 4
    base = np.where(mask, self.nuc-5, np.where(self.nuc == -1, 4, self.nuc))
    for index in range(5):
        if not np.array_equal(result[..., index], base == index):
            raise ValueError('actual encoding base track differs from FASTA')
    if channels == 6 and not np.array_equal(result[..., 5], mask):
        raise ValueError('actual softmask track differs from sequence case')
    audit['encoding_calls'] += 1
    return result


def observed_predict(self, inp_chunks, *args, **kwargs):
    if inp_chunks.shape[-1] != channels or self.lstm_model.input_shape[-1] != channels:
        raise ValueError('LSTM received incompatible input/checkpoint channels')
    audit['model_calls'] += 1
    audit['positions'] += int(np.prod(inp_chunks.shape[:-1]))
    if channels == 6:
        audit['masked_positions'] += int(inp_chunks[..., 5].sum())
    return original_predict(self, inp_chunks, *args, **kwargs)


Fasta.one_hot = observed
PredictionGTF.lstm_prediction = observed_predict
sys.argv[0] = '/opt/Tiberius/tiberius.py'
try:
    runpy.run_path('/opt/Tiberius/tiberius.py', run_name='__main__')
except BaseException as error:
    if not isinstance(error, SystemExit) or error.code not in (0, None):
        audit.update(passed=False, error=repr(error))
    raise
finally:
    if not audit['encoding_calls'] or not audit['model_calls']:
        audit['passed'] = False
    target.write_text(json.dumps(audit, indent=2)+'\n')
    Fasta.one_hot = original
    PredictionGTF.lstm_prediction = original_predict
