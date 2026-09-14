#!/usr/bin/env python3
"""Calibrate on old hg19 chr11 only; retain scores for fixed chromosome evaluation."""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare import role_map


def check_records(records, chrom, split, expected_tiles, tile_bp=8192):
    pairs = {}
    for row in records:
        if (row['chrom'], row['split'], row['assembly'], row['species_code']) != (
                chrom, split, 'hg19', 'human'):
            raise ValueError('record is outside the fixed chromosome/split contract')
        half = row['half']
        pair = pairs.setdefault(row['tile_id'], {})
        if half not in (0, 1) or half in pair:
            raise ValueError('duplicate or invalid tile half')
        if row['end'] - row['start'] != tile_bp // 2 or len(row['sequence']) != tile_bp // 2 or len(row['labels']) != tile_bp // 2:
            raise ValueError('half coordinate/sequence/label length mismatch')
        pair[half] = row
    if len(pairs) != expected_tiles:
        raise ValueError('fixed tile count mismatch')
    intervals = []
    for pair in pairs.values():
        if set(pair) != {0, 1} or pair[0]['end'] != pair[1]['start']:
            raise ValueError('missing or nonadjacent tile halves')
        intervals.append((pair[0]['start'], pair[1]['end']))
    intervals.sort()
    if any(a[1] > b[0] for a, b in zip(intervals, intervals[1:])):
        raise ValueError('overlapping evaluation tiles')


def old_state_intervals(tile, probability, threshold):
    """Partition all old-callable bp before inspecting any later annotation."""
    from itertools import groupby
    states = []
    for truth, valid, score in zip(tile['truth'], tile['callable'], probability):
        states.append('IGNORE' if not valid else
                      'TP' if truth and score >= threshold else
                      'FN' if truth else 'FP' if score >= threshold else 'TN')
    start = int(tile['start'])
    rows = []
    for state, values in groupby(states):
        length = sum(1 for _ in values)
        if state != 'IGNORE':
            rows.append((tile['chrom'], start, start + length, state, 0, '.', tile['tile_id']))
        start += length
    if start != tile['end']:
        raise ValueError('old-state partition does not cover the full tile')
    return rows


def run(args):
    import numpy as np
    cfg = json.loads(args.config.read_text())
    role_map(cfg)
    prep = json.loads((args.data / 'preparation.json').read_text())
    meta = json.loads((args.training / 'training_meta.json').read_text())
    done = json.loads((args.training / 'completion.json').read_text())
    expected_status = 'ENGINEERING_SMOKE_PASS' if args.engineering_smoke else 'TRAINING_COMPLETED_NOT_EVALUATED'
    if prep['protocol'] != cfg or meta['protocol'] != HERE.name or meta['species'] != ['human']:
        raise ValueError('prepared data/training protocol mismatch')
    if Path(meta['data_root']).resolve() != args.data.resolve():
        raise ValueError('evaluation data differ from training preparation')
    if done['status'] != expected_status or done['steps'] != (2 if args.engineering_smoke else cfg['train_steps']):
        raise ValueError('prescribed final training step has not completed')
    spec = importlib.util.spec_from_file_location('hg19_eval_core', HERE.parent / 'CROSS-SPECIES-L1-20260903/calibrate_evaluate_x0.py')
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    args.output.mkdir(parents=True, exist_ok=False)
    native = args.root / cfg['native_model']
    model, tokenizer, device = core.load_final_model(args.training / 'final_model', native, False, native)
    if device.type != 'cuda':
        raise RuntimeError('GPU evaluation job did not receive a CUDA device')
    status = 'ENGINEERING_INTERFACE_ONLY' if args.engineering_smoke else 'OLD_ANNOTATION_CHROMOSOME_EVALUATION'
    common = dict(experiment=HERE.name, status=status, seed=42,
                  training_dir=str(args.training.resolve()), data_dir=str(args.data.resolve()),
                  label_source='fixed old hg19 UCSC comparator', biological_ground_truth=False,
                  checkpoint_selection='final step only', new_annotations_used=False,
                  segment_interpretation='tile-clipped material topology, not insertion identity')

    def infer(split):
        by_chrom = {}
        for chrom, n in cfg['tiles_by_split'][split].items():
            records = core.read_jsonl(args.data / split / f'{chrom}.jsonl.gz')
            check_records(records, chrom, split, n, cfg['tile_bp'])
            if args.engineering_smoke:
                records = records[:4]  # Two preselected tiles, engineering only.
            margins = core.infer_half_margins(model, tokenizer, device,
                                            [r['sequence'] for r in records], args.batch_size)
            if len(margins) != len(records) or any(not np.isfinite(m).all() for m in margins):
                raise ValueError('missing or nonfinite inference margins')
            tiles = core.assemble_tiles('human', records, margins)
            folder = args.output / 'margins' / split
            folder.mkdir(parents=True, exist_ok=True)
            values = {key: np.stack([t[key] for t in tiles]) for key in ('margin', 'truth', 'callable')}
            values.update({key: np.asarray([t[key] for t in tiles]) for key in ('tile_id', 'chrom', 'start', 'end')})
            np.savez_compressed(folder / f'{chrom}.npz', **values)
            by_chrom[chrom] = tiles
        return by_chrom

    cal_chrom = infer('CAL')
    cal = {'human': [t for v in cal_chrom.values() for t in v]}
    core.require_cal_split(cal)
    raw = core.callable_arrays(cal)
    slope, intercept, loss = core.fit_platt(raw)
    selection = core.select_global_threshold({
        k: (core.sigmoid(slope * margin + intercept), truth)
        for k, (margin, truth) in raw.items()})
    calibration = dict(common, fit_split='CAL', fit_chromosomes=['chr11'],
                       platt_slope=slope, platt_intercept=intercept, calibration_loss=loss,
                       threshold=selection['threshold'], selection=selection,
                       threshold_rule='maximum chr11 CAL bp F1; ties closest to 0.5 then higher threshold')
    core.write_json(args.output / 'calibration.json', calibration)
    del cal, raw, cal_chrom
    for split in ('DEV', 'EVAL'):
        by_chrom = infer(split)
        per_chrom = {chrom: core.evaluate_species_tiles(tiles, slope, intercept, selection['threshold'])
                     for chrom, tiles in by_chrom.items()}
        pooled = core.evaluate_species_tiles([t for v in by_chrom.values() for t in v],
                                             slope, intercept, selection['threshold'])
        core.write_json(args.output / f'{split.lower()}_metrics.json',
                        dict(common, split=split, per_chromosome=per_chrom, pooled=pooled,
                             calibration_json=str((args.output / 'calibration.json').resolve())))
        if split == 'EVAL':
            counts = dict.fromkeys(('TP', 'FP', 'FN', 'TN'), 0)
            with (args.output / 'old_confusion_intervals.bed').open('w') as handle:
                for tiles in by_chrom.values():
                    for tile in tiles:
                        probability = core.sigmoid(slope * tile['margin'] + intercept)
                        for row in old_state_intervals(tile, probability, selection['threshold']):
                            handle.write('\t'.join(map(str, row)) + '\n')
                            counts[row[3]] += row[2] - row[1]
            if any(counts[key] != pooled['bp_' + key.lower()] for key in ('TP', 'FP', 'FN')):
                raise ValueError('frozen interval counts differ from evaluation counts')
            if sum(counts.values()) != pooled['callable_bp']:
                raise ValueError('old-state partition lost callable bases')
            core.write_json(args.output / 'old_prediction_manifest.json',
                            dict(common, split='EVAL', interval_bp=counts,
                                 intervals='old_confusion_intervals.bed',
                                 interval_columns=['chrom', 'start0', 'end', 'old_state', 'score', 'strand', 'tile_id'],
                                 interval_unit='tile-clipped old-confusion-state run; not insertion',
                                 matching_controls='TN pool retained in full; matched controls not yet selected',
                                 later_annotation_accessed=False))
    core.write_json(args.output / 'completion.json',
                    dict(common, completed_splits=['CAL', 'DEV', 'EVAL'],
                         cross_assembly_rescue='NOT_YET_EVALUATED'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for field in ('config', 'data', 'training', 'output'):
        parser.add_argument('--' + field, type=Path, required=True)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--batch-size', type=int, default=8)
    parser.add_argument('--engineering-smoke', action='store_true')
    run(parser.parse_args())
