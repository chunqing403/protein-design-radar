# Protein Design Paper Radar

Daily paper recommendations for protein design, protein engineering, and deep learning.

This repository is a lightweight, configurable alternative to manually curated paper lists. It searches fresh papers and preprints, ranks them against topic profiles, writes a Markdown daily digest, and can push the result automatically with GitHub Actions.

## What It Does

- Searches arXiv, bioRxiv, medRxiv, and PubMed.
- Scores papers with configurable positive and negative keywords.
- Deduplicates by DOI, arXiv ID, PubMed ID, or normalized title.
- Persists seen papers in `data/seen.json`.
- Writes daily reports to `outputs/daily/YYYY-MM-DD.md`.
- Updates `outputs/latest.md` for an easy stable link.
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
2. Commits changed files under `outputs/` and `data/`.
3. Pushes back to the current branch.

Enable GitHub Actions write permission:

`Settings` -> `Actions` -> `General` -> `Workflow permissions` -> `Read and write permissions`.

## Optional Secrets

No API key is required for the default run. If you use PubMed heavily, add:

- `NCBI_API_KEY`
- `NCBI_EMAIL`

The script will automatically use them when present.

## Push Channels

GitHub commit push is included. For WeChat/Feishu/email/Slack, add a small notifier after report generation and store webhook URLs as GitHub Secrets.

