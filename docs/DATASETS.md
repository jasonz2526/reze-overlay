# Dataset Split Guide

This project should keep code only. Put all large/raw training datasets in a separate repo (example: `reze-overlay-datasets`).

## 1. Create external dataset repo

```bash
git init ../reze-overlay-datasets
```

Recommended structure:

```text
reze-overlay-datasets/
  scripts/
  notebooks/
  images/
  bubbles-v1/
    data.yaml
    train/
    val/
    test/
  bubbles-v2/
  bubbles-v3/
  manga109s/
  manga109s-yolo/
```

## 2. Move local dataset directories out of this repo

```bash
mv data ../reze-overlay-datasets/
mv dataset ../reze-overlay-datasets/
mv manga109s-dataset ../reze-overlay-datasets/
mv Manga109s ../reze-overlay-datasets/Manga109s
mv images ../reze-overlay-datasets/
mv notebooks ../reze-overlay-datasets/
mv scripts ../reze-overlay-datasets/
```

## 3. Configure this repo to use external datasets

```bash
export REZE_DATASET_ROOT="$HOME/reze-overlay-datasets"
```

For zsh persistence, add to `~/.zshrc`:

```bash
export REZE_DATASET_ROOT="$HOME/reze-overlay-datasets"
```

## 4. Train with Makefile

From this repo root (extension/app repo):

```bash
make train-bubbles
```

Or choose a specific dataset yaml relative path:

```bash
make train-bubbles DATASET_REL=bubbles-v2/data.yaml
```

By default this calls:
- `../reze-overlay-datasets/scripts/train.py`
- with `REZE_DATASET_ROOT=../reze-overlay-datasets`

## 5. Optional: untrack old dataset artifacts from git index

This keeps local files on disk but removes them from git history going forward:

```bash
git rm -r --cached data dataset manga109s-dataset Manga109s images notebooks scripts
```

Then commit:

```bash
git commit -m "chore: split datasets/artifacts out of main repo"
```
