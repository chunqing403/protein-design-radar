# Protein Design Paper Radar

Daily frontier papers for deep learning-based protein design, protein engineering, and biomolecular modeling.

This repository is inspired by curated paper lists such as `Peldom/papers_for_protein_design_using_DL`, but is designed to update itself every day. The newest recommended papers are written directly into this README.

<!-- PAPER_RADAR:START -->
## Latest Recommendations

Updated: **2026-06-30** (`2026-06-30T03:16:43Z`)

| # | Paper | Source | Topics | Score |
|---|---|---|---|---:|
| 1 | [EvoSeq-ML: Advancing Data-Centric Machine Learning with Evolutionary-Informed Protein Sequence Representation and Generation](https://doi.org/10.1101/2024.10.02.616302)<br><sub>Mardikoraem, M., Pascual, N. S., Eaves, J. N. et al.</sub> | biorxiv<br>2026-06-27 | Enzymes and function | 17 |
| 2 | [Multi-dimensional orchestration of binders for improved CAR-T immunotherapy.](https://pubmed.ncbi.nlm.nih.gov/42365891/)<br><sub>Zhu C, Jiang Z, Jing R et al.</sub> | PubMed<br>2026 Jun 28 | Binders and therapeutics | 9 |
| 3 | [Effective structure-aware protein alignment via residue-level contrastive learning](https://doi.org/10.1101/2024.03.09.583681)<br><sub>You, R., Wang, Z., Liu, K. et al.</sub> | biorxiv<br>2026-06-27 | Protein language models | 8 |
| 4 | [Structural feature-based machine learning benchmarking for protein interface prediction.](https://pubmed.ncbi.nlm.nih.gov/42365029/)<br><sub>Topuz T, Erdem Z, Bisgin H et al.</sub> | PubMed<br>2026 Jun 27 | Binders and therapeutics | 7 |
| 5 | [Ultrasensitive de novo Protein Sandwich Lateral flow Fluorescence Assay for Cortisol in Saliva and Serum using Quantum dots and Europium Nanoparticles.](https://pubmed.ncbi.nlm.nih.gov/42364004/)<br><sub>Bruno JG, Chen Y, Mahrat R</sub> | PubMed<br>2026 Jun 27 | Experimental validation | 7 |

### By Topic

#### Binders and therapeutics

- [Multi-dimensional orchestration of binders for improved CAR-T immunotherapy.](https://pubmed.ncbi.nlm.nih.gov/42365891/) (PubMed, 2026 Jun 28)
- [Structural feature-based machine learning benchmarking for protein interface prediction.](https://pubmed.ncbi.nlm.nih.gov/42365029/) (PubMed, 2026 Jun 27)

#### Enzymes and function

- [EvoSeq-ML: Advancing Data-Centric Machine Learning with Evolutionary-Informed Protein Sequence Representation and Generation](https://doi.org/10.1101/2024.10.02.616302) (biorxiv, 2026-06-27)

#### Experimental validation

- [Ultrasensitive de novo Protein Sandwich Lateral flow Fluorescence Assay for Cortisol in Saliva and Serum using Quantum dots and Europium Nanoparticles.](https://pubmed.ncbi.nlm.nih.gov/42364004/) (PubMed, 2026 Jun 27)

#### Protein language models

- [Effective structure-aware protein alignment via residue-level contrastive learning](https://doi.org/10.1101/2024.03.09.583681) (biorxiv, 2026-06-27)

### Archive

- [Daily report for 2026-06-30](outputs/daily/2026-06-30.md)
- [Latest report](outputs/latest.md)

<!-- PAPER_RADAR:END -->

## What It Does

- Searches arXiv, bioRxiv, medRxiv, and PubMed.
- Scores papers with configurable positive and negative keywords.
- Deduplicates by DOI, arXiv ID, PubMed ID, or normalized title.
- Persists seen papers in `data/seen.json`.
- Writes the latest recommendations directly into this README.
- Also writes archive reports to `outputs/daily/YYYY-MM-DD.md` and `outputs/latest.md`.
- Runs daily by GitHub Actions and commits new recommendations.

## Quick Start

```bash
python scripts/daily_recommend.py
```

Use a custom date or output directory:

```bash
python scripts/daily_recommend.py --date 2026-06-30 --days-back 2 --out outputs/daily
```

## Configure Topics

Edit `config/topics.json`.

- `queries`: broad search phrases sent to literature sources.
- `positive_keywords`: terms that increase relevance.
- `negative_keywords`: terms that reduce noise.
- `topic_profiles`: named subareas used for report labels.

The default profile focuses on deep learning for protein design:

- protein structure generation
- diffusion and flow matching models
- sequence design and inverse folding
- protein language models
- binder/enzyme/antibody design
- wet-lab validation signals

## Daily Automation

The workflow in `.github/workflows/daily.yml` runs every day at 00:20 UTC, which is 08:20 in China Standard Time. It:

1. Runs `scripts/daily_recommend.py`.
2. Updates this README with the latest recommended papers.
3. Commits changed files under `README.md`, `outputs/`, and `data/`.
4. Pushes back to the current branch.

Enable GitHub Actions write permission:

`Settings` -> `Actions` -> `General` -> `Workflow permissions` -> `Read and write permissions`.

## Optional Secrets

No API key is required for the default run. If you use PubMed heavily, add:

- `NCBI_API_KEY`
- `NCBI_EMAIL`

The script will automatically use them when present.

## Push Channels

GitHub commit push is included. For WeChat/Feishu/email/Slack, add a small notifier after report generation and store webhook URLs as GitHub Secrets.
