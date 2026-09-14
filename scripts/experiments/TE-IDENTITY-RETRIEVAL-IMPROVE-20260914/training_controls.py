#!/usr/bin/env python3
"""Three fixed training controls, selected on CAL, on the already-seen panel.

L2-normalized 6-mer and NTv2 inputs share the supervised contrastive objective.
A same-projection NTv2 cross-entropy control distinguishes representation and
objective effects. Input dimensions differ, so exact parameter counts are kept.
"""
from pathlib import Path
import argparse
import itertools
import json
import os
import random
import numpy as np
import torch
from torch import nn
import torch.nn.functional as F
import improve_retrieval as core


def train(matrix, labels, train_indices, prototype_ids, id_to_index, indexes, families, identity, objective, output):
    random.seed(42); np.random.seed(42); torch.manual_seed(42)
    torch.set_num_threads(4)
    x = F.normalize(torch.from_numpy(np.asarray(matrix, dtype=np.float32)), dim=1)
    projection = nn.Linear(x.shape[1], 128)
    classifier = nn.Linear(128, len(families)) if objective == 'cross_entropy' else None
    params = list(projection.parameters()) + (list(classifier.parameters()) if classifier else [])
    opt = torch.optim.AdamW(params, lr=0.001, weight_decay=0.0001)
    y = torch.tensor(labels, dtype=torch.long)
    trace, best, best_state, best_accepts = [], None, None, -1
    for epoch in range(1, 51):
        opt.zero_grad(set_to_none=True)
        z = projection(x[train_indices])
        loss = F.cross_entropy(classifier(z), y) if classifier else core.supervised_contrastive_loss(z, y, .1)
        loss.backward(); opt.step()
        with torch.inference_mode():
            all_z = projection(x).numpy()
        cal = core.calibration_for_embedding(all_z, prototype_ids, id_to_index, indexes['cal'], families, True, identity)
        accepts = int(cal['true_accepts'])
        trace.append({'epoch':epoch, 'loss':float(loss.detach()), 'cal_true_accepts':accepts,
                      'cal_false_accepts':cal['false_accepts'], 'cal_pair_far':cal['false_accept_rate']})
        if accepts > best_accepts:
            best_accepts, best = accepts, all_z.copy()
            best_state = {'projection':{k:v.detach().clone() for k,v in projection.state_dict().items()},
                          'classifier':{k:v.detach().clone() for k,v in classifier.state_dict().items()} if classifier else None,
                          'epoch':epoch}
    torch.save(best_state, output / 'state.pt')
    core.write_jsonl(output/'trace.jsonl',trace)
    metric, queries = core.evaluate_embedding(output.name, best, prototype_ids, id_to_index,
                   indexes['cal'], indexes['eval'], families, True, identity)
    metric.update({'selected_epoch':best_state['epoch'], 'training_objective':objective,
                   'input_dim':int(x.shape[1]), 'projection_parameters':sum(p.numel() for p in projection.parameters()),
                   'total_trainable_parameters':sum(p.numel() for p in params),
                   'input_scaling':'per-record L2; no fitted CAL/EVAL statistics',
                   'eval_seen_before':True, 'training_seed':42})
    core.write_queries(output/'queries.tsv', queries)
    core.write_json_atomic(output/'metrics.json',metric)
    return metric


def run(root, output):
    output.mkdir(parents=True, exist_ok=False)
    src = root/'scripts/experiments/TE-IDENTITY-RETRIEVAL-20260914'
    identity, sequence = core.load_support_modules(src)
    data = Path('/srv/beegfs/scratch/users/j/jwang/TE_identity_retrieval_20260914')
    manifest = data/'run_exact/panel/identity_manifest.jsonl'
    rows = [identity.normalize_row(x,i) for i,x in enumerate(identity.load_rows(manifest))]
    audit = identity.audit_manifest(rows)
    if audit['status'] != 'PASS_AUDIT':
        raise ValueError(audit)
    methods, indexes = sequence.select_methods(rows, k=6)
    families = list(indexes['index']['matched_families'])
    ids = [r['record_id'] for r in rows]
    id_to_index = {x:i for i,x in enumerate(ids)}
    embed_root = data/'run_glm_ntv2_native_fixed'
    nt, _ = core.load_embeddings(embed_root/'embeddings.npy',embed_root/'embedding_ids.json',embed_root/'embedding_meta.json',ids)
    vocab = {''.join(k):i for i,k in enumerate(itertools.product('ACGT',repeat=6))}
    km = np.zeros((len(rows),len(vocab)),np.float32)
    for i,r in enumerate(rows):
        if any(c not in 'ACGTN' for c in r['sequence'].upper()):
            raise ValueError('non-ACGTN requires explicit kmer representation choice')
        for k,v in sequence.kmer_vector(r['sequence'],6).items():
            km[i,vocab[k]]=v
    proto = {f:[r['record_id'] for r in methods['basic_train_centroid'][f]] for f in families}
    train_rows = [r for f in families for r in sorted(indexes['train'][f],key=lambda r:r['record_id'])]
    train_indices = [id_to_index[r['record_id']] for r in train_rows]
    label_ids = {f:i for i,f in enumerate(families)}
    labels = [label_ids[r['family_id']] for r in train_rows]
    assert all(r['split']=='train' for r in train_rows)
    config={'arms':['kmer6_l2_supcon','ntv2_l2_supcon','ntv2_l2_cross_entropy'],
            'epochs':50,'lr':.001,'weight_decay':.0001,'temperature':.1,'dimension':128,'seed':42,
            'epoch_selection':'earliest max CAL centroid true pair accepts under pair FAR<=.01',
            'eval':'already-seen EVAL; exploratory, final selected epoch only',
            'note':'CE head optimized only on TRAIN; final retrieval uses projected TRAIN centroid, same as contrastive arms'}
    core.write_json_atomic(output/'config.json',config)
    metrics = {}
    for name,matrix,objective in [('kmer6_l2_supcon',km,'supervised_contrastive'),
                                  ('ntv2_l2_supcon',nt,'supervised_contrastive'),
                                  ('ntv2_l2_cross_entropy',nt,'cross_entropy')]:
        armout=output/name;armout.mkdir()
        metrics[name]=train(matrix,labels,train_indices,proto,id_to_index,indexes,families,identity,objective,armout)
    core.write_json_atomic(output/'metrics.json',metrics)
    core.write_json_atomic(output/'status.json',{'status':'COMPLETED_EXPLORATORY','job_id':os.getenv('SLURM_JOB_ID')})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();run(a.root,a.output)
