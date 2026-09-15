#!/usr/bin/env python3
"""Prepare fixed external cores, NCBI CDS loci, and one native RM mask per species."""
import argparse
from collections import Counter, defaultdict
import csv
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / 'outputs/P3-TIBERIUS-EXTERNAL-20260915'
SOURCES = ROOT / 'software_outputs/P3-TIBERIUS-EXTERNAL-20260915/source'
OLD = ROOT / 'software_outputs/L1-PANEL-PREP-20260908-kqZrej'
META = {
    'cow': {'assembly': 'GCF_002263795.3_ARS-UCD2.0', 'taxid': 9913,
            'fasta': SOURCES/'cow/GCF_002263795.3_ARS-UCD2.0_genomic.fna.gz',
            'gff': SOURCES/'cow/GCF_002263795.3_ARS-UCD2.0_genomic.gff.gz',
            'report': SOURCES/'cow/GCF_002263795.3_ARS-UCD2.0_assembly_report.txt'},
    'platypus': {'assembly': 'GCF_004115215.2_mOrnAna1.pri.v4', 'taxid': 9258,
                 'fasta': OLD/'GCF_004115215.2_mOrnAna1.pri.v4_genomic.fna.gz',
                 'gff': SOURCES/'platypus/GCF_004115215.2_mOrnAna1.pri.v4_genomic.gff.gz',
                 'report': OLD/'GCF_004115215.2_mOrnAna1.pri.v4_assembly_report.txt'},
}


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, allow_nan=False) + '\n')


def attrs(text):
    return {k: unquote(v) for k, v in (piece.split('=', 1) for piece in text.split(';') if '=' in piece)}


def geometry(report):
    rows = []
    for line in report.read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        f = line.split('\t')
        if f[1] == 'assembled-molecule' and f[2].isdigit() and f[3] == 'Chromosome':
            rows.append((int(f[8]), f[6], f[2]))
    rows = sorted(rows, reverse=True)[:10]
    if len(rows) != 10:
        raise ValueError('ten qualified autosomes required by fixed geometry')
    cores = []
    for length, chrom, chromosome in rows:
        for j in (1, 2):
            start = length*j//3 - 2500000
            end = start + 5000000
            hs, he = start-100000, end+100000
            if not 0 <= hs < start < end < he <= length:
                raise ValueError('fixed core/halo does not fit selected autosome')
            cores.append({'id': f'c{len(cores):02d}', 'chrom': chrom, 'chromosome': chromosome,
                          'index': j-1, 'start': start, 'end': end, 'halo_start': hs, 'halo_end': he})
    return cores


def extract(fasta_path, cores):
    selected = defaultdict(list)
    for core in cores:
        selected[core['chrom']].append(core)
    pieces = {c['id']: [] for c in cores}
    name, position = None, 0
    with gzip.open(fasta_path, 'rt') as handle:
        for line in handle:
            if line.startswith('>'):
                name, position = line[1:].split()[0], 0
                continue
            seq = line.strip().upper()
            for core in selected.get(name, []):
                left, right = max(position, core['halo_start']), min(position+len(seq), core['halo_end'])
                if left < right:
                    pieces[core['id']].append(seq[left-position:right-position])
            position += len(seq)
    sequences = {key: ''.join(parts) for key, parts in pieces.items()}
    for core in cores:
        seq = sequences[core['id']]
        if len(seq) != core['halo_end']-core['halo_start'] or set(seq)-set('ACGTN'):
            raise ValueError('core extraction length/alphabet mismatch')
    return sequences


def reference(path, cores, sequences):
    chromosomes = {c['chrom'] for c in cores}
    genes, transcripts, cds = {}, {}, defaultdict(list)
    rejected = Counter()
    with gzip.open(path, 'rt') as handle:
        for line in handle:
            if line.startswith('#'):
                continue
            f = line.rstrip().split('\t')
            if len(f) != 9 or f[0] not in chromosomes:
                continue
            a = attrs(f[8])
            entry = {'chrom': f[0], 'strand': f[6], 'start': int(f[3])-1, 'end': int(f[4]), 'attrs': a}
            if f[2] in ('gene', 'pseudogene'):
                entry['feature'] = f[2]
                genes[a['ID']] = entry
            elif f[2] == 'mRNA':
                transcripts[a['ID']] = entry
            elif f[2] == 'CDS':
                entry['phase'] = f[7]
                for parent in a.get('Parent', '').split(','):
                    cds[parent].append(entry)
    by_gene = defaultdict(list)
    for tid, tx in transcripts.items():
        parts = sorted(cds.get(tid, []), key=lambda c: (c['start'], c['end']))
        if not parts:
            continue
        gene_id = tx['attrs'].get('Parent')
        gene = genes.get(gene_id)
        if gene is None:
            raise ValueError('coding mRNA has no reference gene')
        flags = [gene['attrs'], tx['attrs']] + [c['attrs'] for c in parts]
        if gene['feature'] == 'pseudogene' or any(a.get('pseudo') == 'true' for a in flags):
            rejected['pseudogene'] += 1
            continue
        if any(a.get('partial') == 'true' or 'start_range' in a or 'end_range' in a or 'exception' in a for a in flags):
            rejected['partial_or_exception'] += 1
            continue
        intervals = sorted(set((c['start'], c['end']) for c in parts))
        if any(b[0] < a[1] for a, b in zip(intervals, intervals[1:])):
            rejected['overlapping_CDS'] += 1
            continue
        core = next((c for c in cores if c['chrom'] == tx['chrom'] and c['start'] <= intervals[0][0] < c['end']), None)
        if core is None:
            rejected['outside_fixed_core'] += 1
            continue
        if intervals[-1][1] > core['halo_end']:
            rejected['boundary_incomplete'] += 1
            continue
        if any(c['chrom'] != tx['chrom'] or c['strand'] != tx['strand'] for c in parts):
            raise ValueError('CDS/transcript sequence or strand mismatch')
        seq = ''.join(sequences[core['id']][a-core['halo_start']:b-core['halo_start']] for a,b in intervals)
        if tx['strand'] == '-':
            seq = seq.translate(str.maketrans('ACGTN','TGCAN'))[::-1]
        if len(seq)%3 or not seq.startswith('ATG') or seq[-3:] not in ('TAA','TAG','TGA') or 'N' in seq:
            rejected['nonstandard_or_incomplete_coding_sequence'] += 1
            continue
        accession = tx['attrs'].get('transcript_id', tx['attrs'].get('Name', tid))
        by_gene[gene_id].append({'tid': tid, 'accession': accession, 'intervals': intervals,
                                 'core_id': core['id'], 'chrom': tx['chrom'], 'strand': tx['strand']})
    units, chain_owners = [], defaultdict(set)
    for gid, isoforms in sorted(by_gene.items()):
        core_ids = {i['core_id'] for i in isoforms}
        if len(core_ids) != 1:
            rejected['gene_crosses_core_ownership'] += 1
            continue
        unit = {'unit_id': gid, 'core_id': isoforms[0]['core_id'], 'chrom': isoforms[0]['chrom'],
                'strand': isoforms[0]['strand'], 'gene': genes[gid]['attrs'].get('Name', gid),
                'curated_transcript_present': any(i['accession'].startswith('NM_') for i in isoforms),
                'isoforms': isoforms}
        units.append(unit)
        for iso in isoforms:
            chain_owners[(unit['chrom'],unit['strand'],tuple(map(tuple,iso['intervals'])))].add(gid)
    ambiguous = set().union(*(v for v in chain_owners.values() if len(v)>1)) if chain_owners else set()
    units = [u for u in units if u['unit_id'] not in ambiguous]
    rejected['ambiguous_identical_chain_loci'] = len(ambiguous)
    return {'units': units, 'unit_count': len(units), 'excluded': dict(rejected),
            'per_core_units': {c['id']: sum(u['core_id']==c['id'] for u in units) for c in cores},
            'curated_loci': sum(u['curated_transcript_present'] for u in units),
            'reference_scope': 'NCBI assembly-matched complete standard CDS chains; annotation-relative'}


def prepare(species):
    meta = META[species]
    out = BASE / 'prepared' / species
    out.mkdir(parents=True, exist_ok=False)
    cores = geometry(meta['report'])
    seqs = extract(meta['fasta'], cores)
    for c in cores:
        c['record_id'] = f"{c['chrom']}|base_mask_core={c['index']}|core={c['start']}-{c['end']}|halo={c['halo_start']}-{c['halo_end']}"
    write(out/'geometry.json', cores)
    refs = reference(meta['gff'], cores, seqs)
    write(out/'reference.json', refs)
    with (out/'panel.fa').open('w') as panel:
        for core in cores:
            seq = seqs[core['id']]
            cell = out/core['id']
            cell.mkdir()
            (cell/'sequence.txt').write_text(seq+'\n')
            panel.write('>'+core['id']+'\n')
            for i in range(0,len(seq),80):
                panel.write(seq[i:i+80]+'\n')
            with gzip.open(cell/'region.jsonl.gz','wt') as handle:
                for offset in range(0,len(seq),8192):
                    part=seq[offset:offset+8192]
                    handle.write(json.dumps({'chr':core['chrom'],'start':core['halo_start']+offset,
                        'end':core['halo_start']+offset+len(part),'sequence':part,'labels':[0]*len(part)},separators=(',',':'))+'\n')
    manifest = {'species':species,'assembly':meta['assembly'],'sources':{k:str(v) for k,v in meta.items()},
                'core_count':len(cores),'core_bp':100000000,'halo_input_bp':sum(map(len,seqs.values())),
                'reference_loci':refs['unit_count'],'curated_loci':refs['curated_loci'],
                'new_D_evaluation':False,'scope':'new fixed P3/Tiberius downstream experiment; D cattle remains sealed'}
    write(out/'preparation.json',manifest)
    cfg=json.loads((ROOT/'configs/TE-LONG-BENCH-20260915.json').read_text())
    runtime={k:ROOT/v for k,v in cfg['runtimes'].items()}
    cmd=['apptainer','exec','--cleanenv','--bind',f'{out}:/work','--bind',
         f'{runtime["famdb4"]}:/usr/local/share/famdb-3.0.0/Libraries/famdb:ro',str(runtime['rm'])]
    with (out/'library.fa').open('w') as h:
        subprocess.run(cmd+['/usr/local/share/famdb-3.0.0/famdb.py','-i','/usr/local/share/famdb-3.0.0/Libraries/famdb',
            'families','-f','fasta_acc','--include-class-in-name','-ad',str(meta['taxid'])],stdout=h,check=True)
    if not (out/'library.fa').read_text().startswith('>'):
        raise ValueError('reference library export failed')
    (out/'mask').mkdir()
    started=time.monotonic()
    with (out/'repeatmasker.stdout').open('w') as stdout, (out/'repeatmasker.stderr').open('w') as stderr:
        subprocess.run(cmd+['RepeatMasker','-pa','4','-gff','-xsmall','-lib','/work/library.fa',
                      '-dir','/work/mask','/work/panel.fa'],stdout=stdout,stderr=stderr,check=True)
    spec=importlib.util.spec_from_file_location('tib_external_adapter',ROOT/'scripts/experiments/LEMMI-TE-BENCH-20260824-R1/adapter.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    counts=adapter.convert(out/'mask/panel.fa.out',out/'R.canonical.tsv','repeatmasker_out')
    manifest.update(status='PREPARED_WITH_NATIVE_RM',repeatmasker_version='4.2.4',library='Dfam4.0 taxon ancestors+descendants',
                    repeatmasker_seconds=time.monotonic()-started,repeat_rows=counts)
    write(out/'preparation.json',manifest)
    print(json.dumps(manifest))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('species',choices=sorted(META))
    prepare(parser.parse_args().species)
