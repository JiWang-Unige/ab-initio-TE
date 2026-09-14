#!/usr/bin/env python3
"""
Consensus TE Data Source

Generates TE fragments from Dfam consensus sequences.
Supports RepBase format FASTA files with TE class annotations.
"""

import random
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter, defaultdict
from Bio import SeqIO

from .base import TEDataSource, TESequence


class ConsensusDataSource(TEDataSource):
    """
    Data source for consensus TE fragments

    Parses Dfam/RepBase format FASTA files and generates
    random fragments from consensus sequences.
    """

    def __init__(
        self,
        config: Dict,
        consensus_fasta: str,
        balance_classes: bool = True,
        max_sequences_per_class: Optional[int] = None,
        seed: int = 42
    ):
        """
        Initialize consensus data source

        Args:
            config: Configuration dictionary
            consensus_fasta: Path to consensus FASTA file (RepBase format)
            balance_classes: Whether to balance class distribution
            max_sequences_per_class: Maximum sequences per class (for balancing)
            seed: Random seed
        """
        super().__init__(config, seed)

        self.consensus_fasta = consensus_fasta
        self.balance_classes = balance_classes
        self.max_sequences_per_class = max_sequences_per_class

        # Statistics
        self._stats = {
            "total_sequences": 0,
            "filtered_too_short": 0,
            "filtered_too_long": 0,
            "filtered_unknown_class": 0,
            "extracted": 0
        }

    def get_source_name(self) -> str:
        return "consensus"

    def get_te_sequences(self) -> List[TESequence]:
        """
        Parse consensus sequences and generate fragments

        Returns:
            List of TESequence objects
        """
        print(f"\n{'='*60}")
        print("Consensus TE Extraction")
        print(f"{'='*60}")
        print(f"  Consensus file: {self.consensus_fasta}")
        print(f"  TE classes: {self.te_classes}")
        print(f"  Length range: [{self.min_length}, {self.max_length}]")
        print(f"  Balance classes: {self.balance_classes}")

        # Parse consensus sequences
        sequences = self._parse_consensus()

        if not sequences:
            print("  No sequences found!")
            return []

        # Balance classes if requested
        if self.balance_classes:
            sequences = self._balance_classes(sequences)

        # Print statistics
        self._print_statistics(sequences)

        return sequences

    def _parse_consensus(self) -> List[TESequence]:
        """
        Parse RepBase format FASTA file

        RepBase format header example:
        >MER1_type1#DNA/TcMar-Tigger @Mammalia [S:36]

        Format: >name#class/family @taxonomy [score]
        """
        print(f"\n  Parsing consensus sequences...")

        sequences = []

        for record in SeqIO.parse(self.consensus_fasta, 'fasta'):
            self._stats["total_sequences"] += 1

            # Parse header
            header = record.description
            te_class, te_family = self._parse_repbase_header(header)

            if te_class is None:
                self._stats["filtered_unknown_class"] += 1
                continue

            # Filter by TE class
            if te_class not in self.te_classes:
                continue

            seq = str(record.seq).upper()
            length = len(seq)

            # Length filtering
            if length < self.min_length:
                self._stats["filtered_too_short"] += 1
                continue
            if length > self.max_length:
                self._stats["filtered_too_long"] += 1
                continue

            # Create TESequence object
            te_seq = TESequence(
                id=f"consensus|{record.id}|{te_class}|{te_family}",
                sequence=seq,
                te_class=te_class,
                te_family=te_family,
                length=length,
                source="consensus",
                location=None,
                metadata={
                    'original_id': record.id,
                    'description': header
                }
            )

            sequences.append(te_seq)
            self._stats["extracted"] += 1

        print(f"    Parsed {len(sequences):,} consensus sequences")

        return sequences

    def _parse_repbase_header(self, header: str) -> tuple:
        """
        Parse RepBase format header to extract class and family

        Examples:
        - "MER1_type1#DNA/TcMar-Tigger @Mammalia [S:36]" -> ("DNA", "TcMar-Tigger")
        - "L1_Mus#LINE/L1 @Rodentia" -> ("LINE", "L1")
        - "AluSx#SINE/Alu @Primates" -> ("SINE", "Alu")
        - "ERVL-B4#LTR/ERVL @Mammalia" -> ("LTR", "ERVL")

        Returns:
            (te_class, te_family) or (None, None) if parsing fails
        """
        try:
            # Find the class/family part after #
            if '#' not in header:
                return None, None

            # Split by # and take the part after it
            parts = header.split('#')
            if len(parts) < 2:
                return None, None

            class_part = parts[1].split()[0]  # Remove anything after space

            # Split class and family
            if '/' in class_part:
                te_class, te_family = class_part.split('/', 1)
            else:
                te_class = class_part
                te_family = class_part

            # Normalize class names
            te_class = self._normalize_class(te_class)

            return te_class, te_family

        except Exception:
            return None, None

    def _normalize_class(self, te_class: str) -> str:
        """Normalize TE class name to standard format"""
        # Mapping of various names to standard classes
        class_mapping = {
            'DNA': 'DNA',
            'LINE': 'LINE',
            'SINE': 'SINE',
            'LTR': 'LTR',
            'Retroposon': 'Retroposon',
            'RC': 'RC',
            'PLE': 'PLE',
            # Add more mappings as needed
        }

        return class_mapping.get(te_class, te_class)

    def _balance_classes(self, sequences: List[TESequence]) -> List[TESequence]:
        """Balance class distribution by downsampling"""
        print(f"\n  Balancing classes...")

        # Group by class
        by_class = defaultdict(list)
        for seq in sequences:
            by_class[seq.te_class].append(seq)

        # Find minimum count or use max_sequences_per_class
        if self.max_sequences_per_class:
            target_count = self.max_sequences_per_class
        else:
            target_count = min(len(seqs) for seqs in by_class.values())

        print(f"    Target count per class: {target_count:,}")

        # Downsample each class
        balanced = []
        for te_class, class_seqs in by_class.items():
            if len(class_seqs) > target_count:
                sampled = random.sample(class_seqs, target_count)
            else:
                sampled = class_seqs
            balanced.extend(sampled)
            print(f"    {te_class}: {len(class_seqs):,} -> {len(sampled):,}")

        random.shuffle(balanced)

        return balanced

    def _print_statistics(self, sequences: List[TESequence]):
        """Print extraction statistics"""
        print(f"\n  Extraction Statistics:")
        print(f"    Total in file: {self._stats['total_sequences']:,}")
        print(f"    Unknown class: {self._stats['filtered_unknown_class']:,}")
        print(f"    Too short (<{self.min_length}bp): {self._stats['filtered_too_short']:,}")
        print(f"    Too long (>{self.max_length}bp): {self._stats['filtered_too_long']:,}")
        print(f"    Extracted: {len(sequences):,}")

        # Class distribution
        class_counts = Counter([seq.te_class for seq in sequences])
        print(f"\n  Class Distribution:")
        for te_class, count in sorted(class_counts.items()):
            pct = count / len(sequences) * 100 if sequences else 0
            print(f"    {te_class}: {count:,} ({pct:.1f}%)")

    def get_metadata(self) -> Dict:
        """Return metadata about extracted data"""
        return {
            "source": "consensus",
            "consensus_fasta": str(self.consensus_fasta),
            "te_classes": self.te_classes,
            "balance_classes": self.balance_classes,
            "max_sequences_per_class": self.max_sequences_per_class,
            "filters": {
                "min_length": self.min_length,
                "max_length": self.max_length
            },
            "statistics": self._stats,
            "seed": self.seed
        }

    def generate_fragments_from_consensus(
        self,
        sequences: List[TESequence],
        num_fragments_per_sequence: int = 10,
        fragment_size_range: tuple = (100, 300)
    ) -> List[TESequence]:
        """
        Generate multiple fragments from each consensus sequence

        This is useful for data augmentation when consensus sequences
        are longer than the desired fragment size.

        Args:
            sequences: List of consensus TESequence objects
            num_fragments_per_sequence: Number of fragments to generate per sequence
            fragment_size_range: (min_size, max_size) for fragments

        Returns:
            List of fragment TESequence objects
        """
        print(f"\n  Generating fragments from consensus sequences...")

        fragments = []
        min_size, max_size = fragment_size_range

        for seq in sequences:
            if seq.length < min_size:
                # Sequence too short, use as-is
                fragments.append(seq)
                continue

            # Generate multiple fragments
            for i in range(num_fragments_per_sequence):
                frag_size = random.randint(min_size, min(max_size, seq.length))
                start = random.randint(0, seq.length - frag_size)
                frag_seq = seq.sequence[start:start + frag_size]

                frag = TESequence(
                    id=f"{seq.id}|frag{i}|{start}-{start+frag_size}",
                    sequence=frag_seq,
                    te_class=seq.te_class,
                    te_family=seq.te_family,
                    length=len(frag_seq),
                    source="consensus_fragment",
                    location=None,
                    metadata={
                        'parent_id': seq.id,
                        'fragment_index': i,
                        'start': start,
                        'end': start + frag_size
                    }
                )
                fragments.append(frag)

        print(f"    Generated {len(fragments):,} fragments from {len(sequences):,} sequences")

        return fragments
