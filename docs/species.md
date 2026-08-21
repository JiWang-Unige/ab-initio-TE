# Species Panel / 主实验物种设计

> Last updated: 2026-06-16.
>
> 本文件是当前 TE-FM 物种与实验版本的主合同。核心原则：
>
> **主训练集要少而有解释力；评估集要宽而有说服力；production model 可以更实用，但不能拿来证明 no-human 泛化。**
>
> 重要表述约束：如果 backbone 预训练时见过 human genome，A 系列只能写成
> **no human supervised TE labels during fine-tuning**，不能写成模型从未见过人类 DNA。

## 1. Experiment Versions

| Version | Name | Train / fine-tune species | Main evaluation species | Core question | Priority |
|---|---|---|---|---|---|
| H0 | Human-only upper-bound | human | human held-out chromosomes; hs1/hg38/hg19 audit | human 内部分割上限与 assembly version 影响 | P0 |
| A0 | Mouse-only no-human anchor | mouse | human T2T; pig/cow/horse | 单一 mammal anchor 能否迁移到人类 | P1 small ablation |
| A1 | Vertebrate no-human model | mouse, zebrafish, chicken, *X. tropicalis* | human T2T; optional opossum/lizard/frog stress | vertebrate diversity 是否改善 human transfer | P1 |
| A2 | Full no-human animal model | mouse, zebrafish, chicken, *X. tropicalis*, fly, worm | human T2T; pig/cow/horse; Apis/Tribolium | 主证明：无 human supervised TE labels 下能否泛化到人类和动物 | P0 |
| B | Animal production model | human + A2 six species | human; animal held-outs | 最终实用动物模型 | P0 |
| C | PlantTE model | rice, maize, sorghum, Brachypodium, Setaria, Arabidopsis +/- tomato | wild rice, teosinte, Arabidopsis lyrata, tomato/soybean/grape | plant-only TE model | P0/P1 |
| D-shared | Animal + plant universal baseline | A2 animals + C plants | animal + plant held-outs | 最朴素 universal model 是否可行 | P1 |
| D-kingdom-head | Animal + plant kingdom-aware model | A2 animals + C plants | animal + plant held-outs | kingdom-specific head 是否提升校准 | P1 recommended |
| E-crossKingdom | Animal + plant + fungi | A2 animals + C plants + fungi core | animal + plant + fungi held-outs | fungi 是否提供泛化收益，还是引入 label noise | P2 after fungi QC |

## 2. Animal Panel

### 2.1 Main Train / Production Species

| Role | English name | Scientific name | Species code | TaxID | Use |
|---|---|---|---|---:|---|
| mammal anchor | Mouse | *Mus musculus* | `mouse` | 10090 | A0/A1/A2/B core |
| final human target / production anchor | Human | *Homo sapiens* | `human` | 9606 | A series held-out; H0/B training |
| teleost anchor | Zebrafish | *Danio rerio* | `zebrafish` | 7955 | A1/A2/B core |
| sauropsid anchor | Chicken | *Gallus gallus* | `chicken` | 9031 | A1/A2/B core |
| amphibian anchor | Western clawed frog | *Xenopus tropicalis* | `western_clawed_frog` | 8364 | A1/A2/B core |
| arthropod anchor | Fruit fly | *Drosophila melanogaster* | `fruit_fly` | 7227 | A2/B core |
| nematode anchor | Nematode | *Caenorhabditis elegans* | `c_elegans` | 6239 | A2/B core |

`Xenopus tropicalis` is the first amphibian anchor because it is diploid and simpler than allotetraploid `Xenopus laevis`; `X. laevis` is reserved for stress testing.

### 2.2 Animal Held-out / Stress / Reserve Pool

| English name | Scientific name | Species code | TaxID | Use |
|---|---|---|---:|---|
| Human T2T / hs1 | *Homo sapiens* | `human` | 9606 | A-series main held-out; H0/B train/eval |
| Pig | *Sus scrofa* | `pig` | 9823 | mammal holdout |
| Cattle | *Bos taurus* | `cattle` | 9913 | mammal holdout |
| Horse | *Equus caballus* | `horse` | 9796 | mammal distance holdout |
| Opossum | *Monodelphis domestica* | `opossum` | TBD | optional marsupial stress; not annotated yet |
| Green anole lizard | *Anolis carolinensis* | `lizard` | TBD | optional reptile stress; not annotated yet |
| African clawed frog | *Xenopus laevis* | `x_laevis` | TBD | polyploid amphibian stress; not annotated yet |
| Western honey bee | *Apis mellifera* | `western_honey_bee` | 7460 | invertebrate holdout |
| Red flour beetle | *Tribolium castaneum* | `red_flour_beetle` | 7070 | insect holdout |
| Rat | *Rattus norvegicus* | `rat` | 10116 | mouse redundancy / QC / ablation; not A2 main train |
| Dog | *Canis lupus familiaris* | `dog` | 9615 | mammal reserve / production extension; not A2 main train |

Conclusion: A2 uses six non-human animals for the main no-human animal model. The wider animal pool is retained for held-out, stress, reserve, and QC roles.

## 3. Plant Panel

PlantTE is a separate model family, not a loose plant sentinel. Plant TE biology is dominated by LTR retrotransposons, nested insertion, recent bursts, and grass/cereal TE expansion, so C should be a plant-specific training design.

### 3.1 Recommended PlantTE Training Species

| English name | Scientific name | Species code | Role | Target ratio | Current annotation status |
|---|---|---|---|---:|---|
| Rice | *Oryza sativa* | `rice` | rice anchor; curated benchmark candidate; monocot | 22% | available |
| Maize | *Zea mays* | `maize` | TE-rich / nested LTR stress | 22% | available |
| Sorghum | *Sorghum bicolor* | `sorghum` | grass intermediate node | 16% | not annotated yet |
| Brachypodium | *Brachypodium distachyon* | `brachypodium` | compact grass model | 16% | not annotated yet |
| Thale cress | *Arabidopsis thaliana* | `thale_cress` | compact dicot contrast | 12% | available |
| Foxtail millet | *Setaria italica* | `setaria_italica` | panicoid grass contrast | 12% | not annotated yet |
| Green foxtail | *Setaria viridis* | `green_foxtail` | interim Setaria proxy | optional | available |
| Tomato | *Solanum lycopersicum* | `tomato` | optional dicot crop contrast; preferred over soybean for first core extension | optional | available |

### 3.2 Plant Held-out / Stress / Reserve Pool

| English name | Scientific name | Species code | Use | Current annotation status |
|---|---|---|---|---|
| Wild rice | *Oryza longistaminata* | `wild_rice` | rice-near held-out | not annotated yet |
| Teosinte | *Zea diploperennis* | `teosinte` | maize-near held-out | not annotated yet |
| Arabidopsis lyrata | *Arabidopsis lyrata* | `arabidopsis_lyrata` | dicot-near held-out | not annotated yet |
| Tomato | *Solanum lycopersicum* | `tomato` | if not training, dicot crop held-out | available |
| Soybean | *Glycine max* | `soybean` | later dicot crop stress; more complex | not annotated yet |
| Grape | *Vitis vinifera* | `grape` | reserve / held-out from previous sentinel | available |

AgroNT can be used as a plant-specific backbone baseline or reference model, but PlantTE Label-A and evaluation remain project-owned.

## 4. Fungi Panel

Fungi are useful but should not block the first mainline. Add fungi only after annotation QC passes; use confidence-aware loss and kingdom-specific heads.

| English name | Scientific name | Species code | Use | Current annotation status |
|---|---|---|---|---|
| Baker yeast | *Saccharomyces cerevisiae* | `yeast` | fungi core | not annotated yet |
| Fission yeast | *Schizosaccharomyces pombe* | `fission_yeast` | fungi core | not annotated yet |
| Bread mold | *Neurospora crassa* | `neurospora` | fungi core | not annotated yet |
| Aspergillus | *Aspergillus nidulans* | `aspergillus` | fungi core | not annotated yet |
| Rice blast fungus | *Magnaporthe oryzae* | `magnaporthe` | fungi core | not annotated yet |
| Fusarium | *Fusarium graminearum* | `fusarium` | fungi core | not annotated yet |
| Cryptococcus | *Cryptococcus neoformans* | `cryptococcus` | fungi core | not annotated yet |

Recommended E-stage ablations:

| Version | Train mix | Sampling ratio | Structure | Purpose |
|---|---|---|---|---|
| E-0F | animal + plant | 50 / 50 | shared backbone + kingdom-specific heads | no fungi control |
| E-20F | animal + plant + fungi | 40 / 40 / 20 | fungi confidence-aware; kingdom-specific heads | main fungi version |
| E-33F | animal + plant + fungi | 33 / 33 / 33 | same | fungi weight ablation |
| E-downweightedF | animal + plant + fungi | 40 / 40 / 20 | fungi loss weight capped 0.5-0.7 | fungi label-noise control |

## 5. Cross-kingdom Architecture Assumption

Preferred structure for D/E:

```text
shared backbone
shared binary TE / non-TE head
shared boundary head
animal-specific TE class head
plant-specific TE class head
fungi-specific TE class head
kingdom-specific calibration layer
```

Rationale: TE body/boundary local grammar may share signal across kingdoms, but TE class distribution, family library coverage, annotation confidence, and calibration differ strongly across animal, plant, and fungi.

## 6. Current RepeatMasker+Dfam Output Views

Experiment-oriented views are stored under:

`software_outputs/repeatmasker_dfam/experiment_views/`

Each view contains:

- `species_manifest.tsv`: role and annotation availability.
- `annotations/`: symlinks to current available Label-A species output directories.

Current views:

- `H0_human_only_upper_bound`
- `A0_mouse_only_no_human`
- `A1_vertebrate_no_human`
- `A2_full_no_human_animal`
- `B_animal_production`
- `C_plantTE`
- `D_cross_kingdom_baseline`
- `E_fungi_future`
- `heldout_stress_pool`

## 7. Priority

1. Run H0 + A2 + B first: prove no-human supervised TE label transfer to human and produce a practical animal model.
2. Run C PlantTE in parallel: rice/maize/grass gradient + Arabidopsis/dicot contrast.
3. Run D animal+plant next: compare shared-head vs kingdom-head.
4. Run E fungi last: only after fungi annotation QC passes.
5. Use A0/A1 as small ablations only; do not run the full backbone matrix for every ablation.
