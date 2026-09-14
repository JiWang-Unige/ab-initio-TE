#!/usr/bin/env python3
"""
Real Genome TE Data Source

Extracts TE sequences from real genome using RepeatMasker annotations.
Supports hg38 and other genomes with RepeatMasker BED files.

Uses pyfaidx for efficient indexed FASTA access.
"""

import gzip
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict

# Try pyfaidx first (fast indexed access), fallback to BioPython
try:
    from pyfaidx import Fasta
    PYFAIDX_AVAILABLE = True
except ImportError:
    PYFAIDX_AVAILABLE = False
    from Bio import SeqIO

from .base import TEDataSource, TESequence


class RealGenomeDataSource(TEDataSource):
    """
    Data source for real genome TE fragments

    Extracts TE sequences from genome FASTA using RepeatMasker BED annotations.
    Supports filtering by chromosome, length, and N-base ratio.

    Features:
    - Indexed FASTA access via pyfaidx (falls back to BioPython)
    - Strand-aware extraction (reverse complement for minus strand)
    - Sequence-level train/val/test splitting
    """

    def __init__(
        self,
        config: Dict,
        genome_fasta: str,
        annotation_bed: str,
        chromosomes: List[str] = None,
        seed: int = 42
    ):
        """
        Initialize real genome data source

        Args:
            config: Configuration dictionary
            genome_fasta: Path to genome FASTA file
            annotation_bed: Path to RepeatMasker BED file
            chromosomes: List of chromosomes to process (None = all)
            seed: Random seed
        """
        super().__init__(config, seed)

        self.genome_fasta = genome_fasta
        self.annotation_bed = annotation_bed
        self.chromosomes = chromosomes or ["chr1"]

        # Indexed FASTA reader (lazy initialization)
        self._fasta = None
        self._use_pyfaidx = PYFAIDX_AVAILABLE

        # Cache for BioPython fallback
        self._chromosome_cache = {}

        # Statistics
        self._stats = {
            "total_annotations": 0,
            "filtered_too_short": 0,
            "filtered_too_long": 0,
            "filtered_high_n": 0,
            "plus_strand": 0,
            "minus_strand": 0,
            "extracted": 0
        }

    def get_source_name(self) -> str:
        return "real_genome"

    def get_te_sequences(self) -> List[TESequence]:
        """
        Extract TE sequences from genome

        Returns:
            List of TESequence objects
        """
        print(f"\n{'='*60}")
        print("Real Genome TE Extraction")
        print(f"{'='*60}")
        print(f"  Genome: {self.genome_fasta}")
        print(f"  Annotation: {self.annotation_bed}")
        print(f"  Chromosomes: {self.chromosomes}")
        print(f"  TE classes: {self.te_classes}")
        print(f"  Length range: [{self.min_length}, {self.max_length}]")

        # Parse annotations
        annotations = self._parse_annotations()

        if not annotations:
            print("  No annotations found!")
            return []

        # Extract sequences
        sequences = self._extract_sequences(annotations)

        # Print statistics
        self._print_statistics(sequences)

        return sequences

    def _parse_annotations(self) -> List[Dict]:
        """Parse RepeatMasker BED annotations"""
        print(f"\n  Parsing annotations...")

        annotations = []
        open_func = gzip.open if self.annotation_bed.endswith('.gz') else open

        with open_func(self.annotation_bed, 'rt') as f:
            for line in f:
                if line.startswith('#') or line.startswith('track'):
                    continue

                parts = line.strip().split('\t')
                if len(parts) < 7:
                    continue

                chrom = parts[0]

                # Filter by chromosome
                if self.chromosomes and chrom not in self.chromosomes:
                    continue

                start = int(parts[1])
                end = int(parts[2])
                repeat_name = parts[3]
                strand = parts[5] if len(parts) > 5 else '+'
                repeat_class = parts[6] if len(parts) > 6 else 'Unknown'
                repeat_family = parts[7] if len(parts) > 7 else 'Unknown'

                # Extract main class (e.g., 'LINE/L1' -> 'LINE')
                main_class = repeat_class.split('/')[0] if '/' in repeat_class else repeat_class

                # Filter by TE class
                if main_class not in self.te_classes:
                    continue

                self._stats["total_annotations"] += 1

                annotations.append({
                    'chr': chrom,
                    'start': start,
                    'end': end,
                    'repeat_name': repeat_name,
                    'repeat_class': main_class,
                    'repeat_family': repeat_family,
                    'strand': strand,
                    'length': end - start
                })

        print(f"    Found {len(annotations):,} annotations")

        return annotations

    def _init_fasta_reader(self):
        """Initialize FASTA reader (lazy loading)"""
        if self._fasta is not None:
            return

        if self._use_pyfaidx:
            print(f"    Using pyfaidx for indexed FASTA access...")
            try:
                self._fasta = Fasta(self.genome_fasta)
                print(f"      Indexed FASTA loaded successfully")
            except Exception as e:
                print(f"      pyfaidx failed: {e}, falling back to BioPython")
                self._use_pyfaidx = False
        else:
            print(f"    Using BioPython for FASTA access (slower)...")

    def _get_sequence(self, chrom: str, start: int, end: int) -> str:
        """
        Get sequence from genome (pyfaidx or BioPython)

        Args:
            chrom: Chromosome name
            start: Start position (0-based)
            end: End position (exclusive)

        Returns:
            DNA sequence string
        """
        self._init_fasta_reader()

        if self._use_pyfaidx:
            # pyfaidx: fast indexed access
            try:
                seq = str(self._fasta[chrom][start:end]).upper()
                return seq
            except Exception as e:
                raise ValueError(f"Failed to extract {chrom}:{start}-{end}: {e}")
        else:
            # BioPython fallback: cache entire chromosome
            if chrom not in self._chromosome_cache:
                print(f"      Loading {chrom} sequence (BioPython)...")
                for record in SeqIO.parse(self.genome_fasta, 'fasta'):
                    if record.id == chrom:
                        self._chromosome_cache[chrom] = str(record.seq).upper()
                        print(f"        Loaded {chrom}: {len(self._chromosome_cache[chrom]):,} bp")
                        break
                else:
                    raise ValueError(f"Chromosome {chrom} not found")

            return self._chromosome_cache[chrom][start:end]

    def _extract_sequences(self, annotations: List[Dict]) -> List[TESequence]:
        """Extract sequences from annotations"""
        print(f"\n  Extracting sequences...")

        sequences = []

        for annot in annotations:
            length = annot['length']

            # Length filtering
            if length < self.min_length:
                self._stats["filtered_too_short"] += 1
                continue
            if length > self.max_length:
                self._stats["filtered_too_long"] += 1
                continue

            # Extract sequence using indexed/cached reader
            seq = self._get_sequence(annot['chr'], annot['start'], annot['end'])

            # Handle strand: reverse complement for minus strand
            # This is CRITICAL for consistent TE orientation
            if annot['strand'] == '-':
                seq = self._reverse_complement(seq)
                self._stats["minus_strand"] += 1
            else:
                self._stats["plus_strand"] += 1

            # N-base filtering
            n_count = seq.count('N')
            n_ratio = n_count / len(seq) if len(seq) > 0 else 0

            if n_ratio > self.max_n_ratio:
                self._stats["filtered_high_n"] += 1
                continue

            # Create TESequence object
            te_seq = TESequence(
                id=f"{annot['chr']}:{annot['start']}-{annot['end']}|{annot['repeat_class']}|{annot['repeat_family']}|{annot['strand']}",
                sequence=seq,
                te_class=annot['repeat_class'],
                te_family=annot['repeat_family'],
                length=len(seq),
                source="real_genome",
                location=f"{annot['chr']}:{annot['start']}-{annot['end']}",
                metadata={
                    'strand': annot['strand'],
                    'repeat_name': annot['repeat_name'],
                    'n_ratio': n_ratio,
                    'original_orientation': 'reverse_complemented' if annot['strand'] == '-' else 'forward'
                }
            )

            sequences.append(te_seq)
            self._stats["extracted"] += 1

        return sequences

    def _print_statistics(self, sequences: List[TESequence]):
        """Print extraction statistics"""
        print(f"\n  Extraction Statistics:")
        print(f"    Total annotations: {self._stats['total_annotations']:,}")
        print(f"    Too short (<{self.min_length}bp): {self._stats['filtered_too_short']:,}")
        print(f"    Too long (>{self.max_length}bp): {self._stats['filtered_too_long']:,}")
        print(f"    High N (>{self.max_n_ratio:.1%}): {self._stats['filtered_high_n']:,}")
        print(f"    Extracted: {self._stats['extracted']:,}")
        print(f"    Strand distribution: + {self._stats['plus_strand']:,}, - {self._stats['minus_strand']:,}")

        # Class distribution
        class_counts = Counter([seq.te_class for seq in sequences])
        print(f"\n  Class Distribution:")
        for te_class, count in sorted(class_counts.items()):
            pct = count / len(sequences) * 100 if sequences else 0
            print(f"    {te_class}: {count:,} ({pct:.1f}%)")

    def split_sequences(
        self,
        sequences: List[TESequence],
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        stratify: bool = True
    ) -> Tuple[List[TESequence], List[TESequence], List[TESequence]]:
        """
        Split sequences into train/val/test sets (sequence-level holdout)

        IMPORTANT: This ensures no sequence appears in multiple splits,
        preventing data leakage.

        Args:
            sequences: List of TESequence objects
            train_ratio: Fraction for training
            val_ratio: Fraction for validation
            test_ratio: Fraction for testing
            stratify: Whether to maintain class distribution

        Returns:
            (train_sequences, val_sequences, test_sequences)
        """
        assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 0.01, \
            "Ratios must sum to 1.0"

        random.seed(self.seed)

        if stratify:
            # Stratified split: maintain class distribution
            by_class = defaultdict(list)
            for seq in sequences:
                by_class[seq.te_class].append(seq)

            train_seqs, val_seqs, test_seqs = [], [], []

            for te_class, class_seqs in by_class.items():
                random.shuffle(class_seqs)
                n = len(class_seqs)
                n_train = int(n * train_ratio)
                n_val = int(n * val_ratio)

                train_seqs.extend(class_seqs[:n_train])
                val_seqs.extend(class_seqs[n_train:n_train + n_val])
                test_seqs.extend(class_seqs[n_train + n_val:])
        else:
            # Random split
            shuffled = sequences.copy()
            random.shuffle(shuffled)
            n = len(shuffled)
            n_train = int(n * train_ratio)
            n_val = int(n * val_ratio)

            train_seqs = shuffled[:n_train]
            val_seqs = shuffled[n_train:n_train + n_val]
            test_seqs = shuffled[n_train + n_val:]

        # Shuffle within each set
        random.shuffle(train_seqs)
        random.shuffle(val_seqs)
        random.shuffle(test_seqs)

        print(f"\n  Sequence-level split (seed={self.seed}):")
        print(f"    Train: {len(train_seqs):,} ({len(train_seqs)/len(sequences)*100:.1f}%)")
        print(f"    Val:   {len(val_seqs):,} ({len(val_seqs)/len(sequences)*100:.1f}%)")
        print(f"    Test:  {len(test_seqs):,} ({len(test_seqs)/len(sequences)*100:.1f}%)")

        return train_seqs, val_seqs, test_seqs

    def get_metadata(self) -> Dict:
        """Return metadata about extracted data"""
        return {
            "source": "real_genome",
            "genome_fasta": str(self.genome_fasta),
            "annotation_bed": str(self.annotation_bed),
            "chromosomes": self.chromosomes,
            "te_classes": self.te_classes,
            "filters": {
                "min_length": self.min_length,
                "max_length": self.max_length,
                "max_n_ratio": self.max_n_ratio
            },
            "statistics": self._stats,
            "seed": self.seed
        }

    def analyze_length_distribution(
        self,
        sequences: List[TESequence],
        output_file: Optional[str] = None
    ) -> Dict:
        """
        Analyze length distribution by class

        Args:
            sequences: List of TESequence objects
            output_file: Optional path to save JSON results

        Returns:
            Dictionary with length distribution statistics
        """
        length_bins = [
            (50, 100),
            (100, 150),
            (150, 300),
            (300, 1000),
            (1000, 10000)
        ]

        class_length_dist = defaultdict(lambda: defaultdict(int))
        class_total = defaultdict(int)

        for seq in sequences:
            te_class = seq.te_class
            length = seq.length

            class_total[te_class] += 1

            for min_len, max_len in length_bins:
                if min_len <= length < max_len:
                    class_length_dist[te_class][f"{min_len}-{max_len}bp"] += 1
                    break

        # Build distribution table
        distribution = {}
        for te_class in sorted(class_total.keys()):
            distribution[te_class] = {
                "total": class_total[te_class],
                "bins": {}
            }
            for min_len, max_len in length_bins:
                bin_name = f"{min_len}-{max_len}bp"
                count = class_length_dist[te_class][bin_name]
                ratio = count / class_total[te_class] if class_total[te_class] > 0 else 0
                distribution[te_class]["bins"][bin_name] = {
                    "count": count,
                    "ratio": round(ratio, 4)
                }

        if output_file:
            import json
            with open(output_file, 'w') as f:
                json.dump(distribution, f, indent=2)
            print(f"  Saved length distribution to {output_file}")

        return distribution

    def _reverse_complement(self, sequence: str) -> str:
        """Generate reverse complement of DNA sequence"""
        complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C', 'N': 'N'}
        return ''.join([complement.get(base, 'N') for base in reversed(sequence)])
