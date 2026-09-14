#!/usr/bin/env python3
"""Create fixed hg19 chr1-only task training and chromosome-held-out records."""
import argparse
import collections
import gzip
import json
import random
from pathlib import Path

TE = {'SINE','LINE','LTR','DNA','RC','RETROPOSON'}


def role_map(cfg):
    result={}
    for split, chroms in cfg['tiles_by_split'].items():
        for chrom, n in chroms.items():
            if chrom in result or chrom in cfg['forbidden']:
                raise ValueError('overlapping or forbidden chromosome role')
            result[chrom]=(split,n)
    if set(cfg['tiles_by_split']['TRAIN'])!={'chr1'}:
        raise ValueError('task training must use only hg19 chr1')
    return result


def fasta_records(path, wanted):
    chrom=None; pieces=[]
    with gzip.open(path,'rt') as f:
        for line in f:
            if line.startswith('>'):
                if chrom in wanted:yield chrom,''.join(pieces).upper()
                chrom=line[1:].split()[0];pieces=[]
            elif chrom in wanted:pieces.append(line.strip())
    if chrom in wanted:yield chrom,''.join(pieces).upper()


def selected_starts(seq,n,tile,seed,max_nonacgt):
    # Eligibility uses only the old assembly sequence. Labels and model scores
    # play no role in selection; sampling is across the whole chromosome.
    candidates=[s for s in range(0,len(seq)-tile+1,tile)
                if sum(seq[s:s+tile].count(b) for b in 'ACGT') >= tile*(1-max_nonacgt)]
    if len(candidates)<n:raise ValueError('insufficient sequence-qualified tiles')
    return sorted(random.Random(seed).sample(candidates,n)),len(candidates)


def label_records(path,wanted):
    out={chrom:[] for chrom in wanted}
    with gzip.open(path,'rt') as f:
        for line in f:
            r=line.rstrip('\n').split('\t')
            if len(r)!=17:raise ValueError('expected 17-column UCSC rmsk')
            chrom=r[5]
            if chrom not in wanted:continue
            s,e=int(r[6]),int(r[7]);c=r[11].upper()
            if not 0<=s<e:raise ValueError('invalid annotation coordinate')
            label=('?' if '?' in c or c=='UNKNOWN' else
                   '1' if c.split('/')[0] in TE else '0')
            out[chrom].append((s,e,label))
    return {c:sorted(v) for c,v in out.items()}


def materialize(cfg,root,out):
    roles=role_map(cfg);tile=cfg['tile_bp']
    if tile!=8192:raise ValueError('reuse requires 8192 bp paired tiles')
    out.mkdir(parents=True,exist_ok=False)
    ann=label_records(root/cfg['comparator'],roles)
    manifest=[];counts={};observed=set()
    for chrom,seq in fasta_records(root/cfg['fasta'],roles):
        observed.add(chrom);split,n=roles[chrom]
        starts,pool=selected_starts(seq,n,tile,cfg['seed'],cfg['max_non_acgt_fraction'])
        records=ann[chrom];pointer=0;active=[];label_counts=collections.Counter()
        folder=out/split;folder.mkdir(exist_ok=True)
        with gzip.open(folder/f'{chrom}.jsonl.gz','wt') as f:
            for s in starts:
                e=s+tile;active=[r for r in active if r[1]>s]
                while pointer<len(records) and records[pointer][0]<e:
                    if records[pointer][1]>s:active.append(records[pointer])
                    pointer+=1
                labels=bytearray(b'0'*tile)
                # Positive first, then ignore. Non-ACGT always remains ignored.
                for mark in ('1','?'):
                    for a,b,value in active:
                        if value==mark:
                            lo,hi=max(a,s)-s,min(b,e)-s
                            if lo<hi:labels[lo:hi]=mark.encode()*(hi-lo)
                piece=seq[s:e]
                for j,b in enumerate(piece):
                    if b not in 'ACGT':labels[j]=ord('?')
                text=labels.decode()
                if split=='TRAIN' and any(set(text[h:h+4096])=={'?'} for h in (0,4096)):
                    raise ValueError(f'preselected TRAIN half has no callable label: {chrom}:{s}')
                label_counts.update(text)
                tid=f'human|hg19|{chrom}|{s}|{e}'
                manifest.append(dict(split=split,chrom=chrom,start=s,end=e,tile_id=tid))
                for half in (0,1):
                    h=half*4096
                    record=dict(species_code='human',assembly='hg19',split=split,tile_id=tid,
                                half=half,chrom=chrom,start=s+h,end=s+h+4096,
                                sequence=piece[h:h+4096],labels=text[h:h+4096])
                    f.write(json.dumps(record,separators=(',',':'))+'\n')
        counts[chrom]=dict(split=split,tiles=n,sequence_eligible_pool=pool,label_bp=dict(label_counts))
    if observed!=set(roles):raise ValueError('missing required hg19 chromosomes')
    # The legacy single-species trainer consumes exactly this TRAIN filename.
    (out/'TRAIN'/'chr1.jsonl.gz').rename(out/'TRAIN'/'human.jsonl.gz')
    (out/'tiles.json').write_text(json.dumps(manifest,indent=2)+'\n')
    result=dict(status='DATA_PREPARED_NO_MODEL_RESULT',protocol=cfg,counts=counts,
                selection='sequence-only sampled nonoverlapping 8192 grid tiles, seed42',
                source_assembly='hg19',new_annotation_used=False,
                pretrained_sequence_exposure='unresolved',sequence_homology_holdout=False)
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='protocol'},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,required=True);ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();materialize(json.loads(a.config.read_text()),a.root,a.output)
