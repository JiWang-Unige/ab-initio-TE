"""Read-only local QC of the three authorized remote FASTA files."""
import gzip
import json
import subprocess

HOST = 'login1.baobab.hpc.unige.ch'
ROOT = '/srv/beegfs/scratch/shares/ds4dh/common/ab-initio-TE/software_outputs/L1-PANEL-PREP-20260908-kqZrej'
STEMS = ['GCF_004115215.2_mOrnAna1.pri.v4', 'GCF_000002235.5_Spur_5.0', 'GCA_000004555.3_CB4']

for stem in STEMS:
    report = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST,
                                      'cat ' + ROOT + '/' + stem + '_assembly_report.txt'], text=True)
    expected = {}
    for line in report.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        fields = line.split('\t')
        seqid = fields[6] if stem.startswith('GCF') else fields[4]
        # Paired reports also list sequences exclusive to the other database.
        if seqid == 'na':
            continue
        expected[seqid] = (int(fields[8]), fields[7])
    proc = subprocess.Popen(['ssh', '-o', 'BatchMode=yes', HOST,
                             'cat ' + ROOT + '/' + stem + '_genomic.fna.gz'], stdout=subprocess.PIPE)
    observed = {}
    seqid = None
    with gzip.GzipFile(fileobj=proc.stdout) as stream:
        for line in stream:
            if line.startswith(b'>'):
                seqid = line[1:].split()[0].decode('ascii')
                if seqid in observed:
                    raise ValueError('Duplicate FASTA ID: ' + seqid)
                observed[seqid] = [0, 0, 0]
            else:
                sequence = line.strip().upper()
                observed[seqid][0] += len(sequence)
                observed[seqid][1] += sequence.count(b'N')
                observed[seqid][2] += len(sequence) - sum(sequence.count(bytes([b])) for b in b'ACGTN')
    if proc.wait() != 0:
        raise RuntimeError('SSH stream failed')
    if set(expected) != set(observed):
        raise ValueError('Assembly report/FASTA ID mismatch')
    if any(expected[k][0] != observed[k][0] for k in expected):
        raise ValueError('Assembly report/FASTA length mismatch')
    print(json.dumps({'assembly': stem, 'status': 'PASS', 'sequences': len(observed),
                      'total_bp': sum(x[0] for x in observed.values()),
                      'primary_bp': sum(observed[k][0] for k in expected if expected[k][1] == 'Primary Assembly'),
                      'N_bp': sum(x[1] for x in observed.values()),
                      'other_non_ACGTN_bp': sum(x[2] for x in observed.values())}), flush=True)
