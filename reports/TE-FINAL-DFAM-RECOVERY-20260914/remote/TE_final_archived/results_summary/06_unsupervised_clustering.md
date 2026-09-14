# Result 6: Unsupervised Clustering of TE Embeddings

To validate whether the foundation model learns biologically meaningful representations of Transposable Elements (TEs) without explicit supervision, we evaluated the quality of embeddings via unsupervised clustering. We compared the Foundation Model (TE-FM) against a K-mer baseline across different training configurations (A1, A2, B1, B2).

---

## 1. Experimental Design

We utilized the **hg38** test set (n=5,000 sequences) and evaluated clustering performance on the **5 major TE superfamilies**: LINE, SINE, LTR, DNA, and Background.

### 1.1 Configuration Overview (2×2 Design + Baseline)

| Config | Name | Initialization | Backbone | Contrastive Learning | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **K-mer** | Baseline | N/A | N/A | ❌ None | Traditional sequence composition features (6-mer frequency), serving as a lower bound. |
| **A1** | Pre-trained Frozen | **Warm** (Pre-trained) | **Frozen** | ❌ None | Test the zero-shot quality of pre-trained features. |
| **A2** | Random Frozen | **Cold** (Random) | **Frozen** | ❌ None | Control: verify that architecture alone does not produce meaningful features. |
| **B1** | **Pre-trained Trainable** | **Warm** (Pre-trained) | **Trainable** | ✅ **InfoNCE** | Full fine-tuning with contrastive learning; tests maximum potential. |
| **B2** | Pre-trained + Head | **Warm** (Pre-trained) | **Frozen** | ✅ **InfoNCE (Head Only)** | Train projection head only; tests linear separability of frozen features. |

### 1.2 Detailed Configuration Descriptions

#### K-mer Baseline
- **Feature Extraction**: Compute 6-mer frequency vectors for each TE sequence.
- **Dimensionality**: Original 4^6 = 4096 dimensions, reduced to 1280 via PCA for fair comparison.
- **Clustering**: Direct K-Means on the frequency vectors.
- **Limitation**: Captures only surface-level sequence composition (e.g., GC content), no semantic or structural understanding.

#### A1: Pre-trained Frozen (Feature Extraction)
- **Model**: GENERanno-0.5B pre-trained on multi-species genomic data.
- **Training**: **None**. Backbone weights are frozen.
- **Feature Extraction**: Pass TE sequences through the frozen model, use mean-pooled hidden states as embeddings.
- **Rationale**: Tests if the pre-training objective (MLM on genomes) implicitly learns TE-relevant features without any TE-specific supervision.

#### A2: Random Frozen (Architecture Control)
- **Model**: GENERanno-0.5B with **randomly initialized weights**.
- **Training**: **None**. Random weights are frozen.
- **Feature Extraction**: Same as A1, but with random weights.
- **Rationale**: Control group to verify that any observed clustering in A1 is due to **learned weights**, not the transformer architecture or projection dimensions.

#### B1: Pre-trained Trainable (Full Fine-tuning with Contrastive Learning)
- **Model**: GENERanno-0.5B initialized with pre-trained weights.
- **Training**: **Full fine-tuning** with **InfoNCE (NT-Xent) loss**.
    - In-batch negatives: All other samples in the batch serve as negatives.
    - Temperature: τ = 0.07.
    - Objective: Pull embeddings of same-class TEs together, push different-class TEs apart.
- **Projection Head**: 2-layer MLP (1280 → 512 → 128) for contrastive learning.
- **Rationale**: Tests the model's maximum potential when allowed to adapt its entire representation to the TE clustering task.

#### B2: Pre-trained + Projection Head (Linear Probe with Contrastive Learning)
- **Model**: GENERanno-0.5B with **frozen pre-trained weights**.
- **Training**: **Only the projection head** is trained with InfoNCE loss.
- **Rationale**: Tests if the pre-trained features are already linearly separable, and if a simple projection can improve clustering without modifying the backbone.

---

## 2. Clustering Performance

We used **K-Means** clustering on the embedding vectors and measured performance using:
- **ARI (Adjusted Rand Index)**: Measures agreement between clusters and true labels, adjusted for chance.
- **NMI (Normalized Mutual Information)**: Measures information shared between clusters and true labels.
- **Purity**: Fraction of samples correctly assigned to the majority class in each cluster.

| Model | Configuration | ARI | NMI | Purity | Key Insight |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **K-mer** | Baseline | 0.0425 | 0.0729 | 0.3237 | Poor; composition alone weakly distinguishes classes. |
| **A2** | Random Frozen | 0.0172 | 0.0312 | 0.2027 | **Failure**; random weights = random features. |
| **A1** | Pre-trained Frozen | 0.0897 | 0.1197 | 0.3946 | **+111% ARI vs K-mer**. Pre-training helps, but clusters overlap. |
| **B2** | Pre-trained + Head | 0.0685 | 0.0984 | 0.3541 | Projection head alone is insufficient to disentangle features. |
| **B1** | **Pre-trained Trainable** | **0.6928** | **0.7164** | **0.8595** | **+1530% ARI vs K-mer**. Full fine-tuning is critical. |

---

## 3. Key Findings

### 3.1 Fine-Tuning is Critical (B1 vs A1)
- **A1 (Frozen)**: Pre-trained features show some structure (ARI 0.09 > K-mer 0.04), but clusters heavily overlap.
- **B1 (Trainable)**: Full fine-tuning with contrastive learning dramatically improves clustering (ARI 0.69).
- **Conclusion**: Pre-trained representations contain useful information, but **contrastive fine-tuning is required** to align the embedding space with TE taxonomy.

### 3.2 Pre-training Provides a Strong Starting Point (A1 vs A2)
- **A1 (Pre-trained)**: ARI 0.09.
- **A2 (Random)**: ARI 0.02.
- **Conclusion**: Pre-training on genomic data provides **meaningful initialization** that captures some TE-relevant features, even without TE-specific supervision.

### 3.3 Projection Head Alone is Insufficient (B2 vs B1)
- **B2 (Frozen + Head)**: ARI 0.07.
- **B1 (Trainable)**: ARI 0.69.
- **Conclusion**: The pre-trained features are **not linearly separable** by TE class. Full backbone fine-tuning is needed to reshape the representation space.

### 3.4 Superiority over K-mer Baseline
- **B1** achieves **16× higher ARI** than K-mer (0.69 vs 0.04).
- **Conclusion**: The foundation model learns **complex, higher-order patterns** (motifs, structural elements) that distinguish TE families, far beyond simple sequence composition.

---

## 4. Visualization Plan

We will create **t-SNE/UMAP plots** to visually demonstrate:
1. **K-mer Space**: Disorganized "hairball" with weak separation.
2. **A1 (Frozen)**: Partial structure but significant overlap between classes.
3. **B1 (Fine-tuned)**: Distinct, well-separated clusters corresponding to TE superfamilies.
