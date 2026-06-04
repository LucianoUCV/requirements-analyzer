# Requirements Analyzer

An intelligent software requirements analysis system. Given a Software Requirements Specification (SRS), it classifies each requirement, flags quality smells, and surfaces duplicate and contradictory requirement pairs.

Bachelor's thesis, University of Craiova (Computer Science).

## Capabilities

Four analyses, run end-to-end by `pipeline.py`:

1. **Classification** - assigns each requirement to one of 12 categories: Functional (F) + 11 non-functional sub-classes (Security, Performance, Usability, Legal, Operational, Maintainability, Look & Feel, Scalability, Portability, Availability, Fault Tolerance). Also reports binary FR/NFR. Both classifiers are fine-tuned `bert-base-uncased`. When the input carries an existing `class` column, a **verification mode** cross-checks those labels against the model and flags likely mislabels. Each report also includes a 0–100 **quality score** summarising smell, duplicate, contradiction, and mislabel prevalence.
2. **Smell detection** - flags each requirement for three smells:
   - `ambiguity` (multi-label BERT)
   - `weak_verb` (multi-label BERT)
   - `incompleteness` (rule-based regex)
3. **Duplicate detection** - for each project, finds pairs of requirements with cosine similarity ≥ threshold (default 0.85) using a pre-trained Sentence-BERT encoder (`all-MiniLM-L6-v2`).
4. **Contradiction detection** - for each project, finds pairs with similarity in [0.65, 0.985] that exhibit at least one rule-based conflict (negation flip or unit-aware numerical mismatch).

## Dataset

PROMISE+ (Zenodo: https://zenodo.org/records/12805484): 3677 requirements across 88 projects, manually labeled for both functional / non-functional classification and quality smells. Stored as `data/processed/promise_final.csv`.

## Results - Classification

Evaluated on a cross-project test split (18 projects never seen in training). F1 macro is the primary metric. Single fixed seed (42); 

| Task | Model | F1 macro |
|---|---|---|
| 12-class NFR | TF-IDF + LinearSVC (baseline) | 0.3112 |
| 12-class NFR | **BERT (`bert-base-uncased`)** | **0.3447** |
| Binary FR/NFR | TF-IDF + LinearSVC (baseline) | 0.7079 |
| Binary FR/NFR | **BERT (`bert-base-uncased`)** | **0.7103** |

BERT's advantage over baseline is not that obvious ( only on the per class F1 macro analysis ) because the dataset is small and extremely unbalanced ( main problem ), some classes ( Fault Tolerance, Legal, ... ) have so few examples that the model can't learn and predict them correctly. 

## Results - Smell detection

Same cross-project test split. `ambiguity` and `weak_verb` are detected by a single multi-label BERT (`bert-base-uncased`); `incompleteness` by a precision-oriented regex (only 25 positive examples exist in the corpus, too few to train a model).

| Smell | Method | F1 |
|---|---|---|
| ambiguity | **BERT (multi-label)** | **0.880** |
| weak_verb | **BERT (multi-label)** | **0.929** |
| incompleteness | rule-based regex | 0.222 |

BERT's macro F1 over the two learned smells is **0.904**. Incompleteness flags only explicit placeholders (`TBD`, `<x>`, `...`, `[INSERT_]`).

## Results - Duplicates & contradictions

PROMISE+ has no labels for duplicates or contradictions, so the pre-trained SBERT model is used directly, with no fine-tunning. 

## Project structure

```
requirements-analyzer/
├── data/
│   ├── raw/                            # original dataset
│   └── processed/promise_final.csv     # cleaned and labeled dataset
├── src/
│   └── data_loader.py                  # ARFF parser
├── notebooks/
│   ├── 01_EDA.ipynb                    # EDA
│   ├── 02_baseline_classification.ipynb  # TF-IDF + LinearSVC baseline
│   ├── 03_bert_classification.ipynb    # BERT multi-class + binary
│   ├── 04_smell_detection.ipynb        # BERT multi-label + incompleteness 
│   └── 05_duplicates_contradictions.ipynb  # SBERT + rule-based conflicts
├── models/                             # trained models (gitignored)
├── figures/                            # figures (PDF + PNG)
├── pipeline.py                         # CLI entry point
├── requirements_analyzer/              # analyzer package (rules, analyzer, report, io)
├── requirements.txt
└── README.md
```

## Installation

Python 3.12+ recommended. Apple Silicon (M-series) supported via PyTorch MPS.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Models

Trained model weights are **not committed** - the `models/` folder is gitignored (`models/*`). Each fine-tuned BERT checkpoint is ~400 MB, far too large for Git, and is fully reproducible from the notebooks. The repository ships the *training code* (notebooks) and *evidence* (figures + metrics), not the binary artifacts.

**You must generate the models locally before running the pipeline.** Run the notebooks top-to-bottom (they fine-tune and save into `models/`):


Each notebook uses the fixed seed (42) and the same cross-project split. Training all three takes roughly 30–45 min on an Apple M-series GPU (MPS).

## Usage

Once the models exist under `models/`, invoke the pipeline:

```bash
# Plain text input, html output
python pipeline.py --input my_requirements.txt --output output/report.html

# CSV input, json output
python pipeline.py --input srs.csv --output output/report.json

# Customize thresholds
python pipeline.py --input srs.csv --output output/report.html \
    --duplicate-threshold 0.90 \
    --contradiction-sim-min 0.70
```

If the CSV includes a `class` column, the pipeline runs in **verification mode** (cross-checking your labels); otherwise it classifies from scratch. The output parent folder (`output/`) is created automatically. Output formats: `.json` or `.html`.

## Methodology highlights

- **Cross-project evaluation** (`GroupShuffleSplit`, `random_state=42`).
- **F1 macro as primary metric**
- **Weighted cross-entropy + 2× oversampling** for the BERT multi-class classifier
- **Pre-trained SBERT (no fine-tuning)** for similarity tasks 
- **Same train/val/test split across all notebooks** 

See `notebooks/` for full methodological details and per-component results.


