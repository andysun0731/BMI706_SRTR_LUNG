# OPO Lung Transplant Performance — Interactive Visualization Tool

Interactive web tool accompanying the study **"Donor Care Unit Availability and Organ Procurement
Organization Performance in Lung Transplantation"** (Yang Z, et al.; corresponding authors Zhizhou
Yang and Varun Puri), under review.

The tool visualizes national OPTN/SRTR lung-transplant data (Jan 2018–Aug 2025) to let users explore
organ-flow patterns and benchmark **organ procurement organization (OPO)** performance — donor lung
utilization, donor quality, and graft survival — in the context of **donor care unit (DCU)**
availability. This repository contains everything needed to run and reproduce the tool.

Live tool: **http://opolung2025.com/**

---

## The tool

A Streamlit dashboard (`app_final.py`) with three panels:

| Tab | What it shows |
|-----|----------------|
| **Map** | OPO ↔ transplant-center organ-flow ("flight map"), with a date-range slider and CAS-implementation marker; OPOs colored by DCU-availability rate. |
| **Utilization** | Donor lung utilization by OPO (DBD vs DCD, pre/post-CAS) against the national rate, plus mean LUNDON donor-quality score (DBD). |
| **Survival** | Per-OPO Kaplan–Meier graft-survival curves vs a nationwide reference, with **adjusted Cox hazard ratios** (each OPO vs the rest of the United States) and 5-year survival. |

All data the app reads are **pre-aggregated, de-identified summary tables** (`viz_*.csv`); no
record-level data are stored or served.

---

## Repository structure

```
.
├── app_final.py                # Streamlit app (the tool)
├── precompute_final.py         # SRTR analytic files → viz_*.csv (map, KM curves, utilization, LUNDON)
├── precompute_survival_hr.R    # per-OPO adjusted Cox HR (vs rest of US) → viz_survival_hr.csv
├── viz_*.csv                   # pre-aggregated, de-identified inputs the app reads (included)
├── requirements.txt            # Python dependencies for the app
└── Dockerfile                  # container image for the Streamlit app
```

## Running the tool

### Quick start (no SRTR data required)

The pre-aggregated `viz_*.csv` inputs are included, so the app runs as-is:

```bash
pip install -r requirements.txt
streamlit run app_final.py            # opens at http://localhost:8501
```

Or with Docker:

```bash
docker build -t opo-lung-tool .
docker run -p 8501:8501 opo-lung-tool
```

### Regenerating the inputs from source data (optional)

Recreating the `viz_*.csv` from raw data requires SRTR analytic files, which require an approved SRTR request and
Data Use Agreement and are **not distributed here**. With those files available (needs to modify and adapt variable names):

```bash
python precompute_final.py        # → viz_map_data / survival_curves / survival_stats / donor_utilization / lundon_summary
Rscript precompute_survival_hr.R  # → viz_survival_hr.csv (adjusted per-OPO Cox hazard ratios)
```

> The data path is configured near the top of `precompute_final.py` and `precompute_survival_hr.R`
> — update it to point at your local SRTR analytic files. `precompute_survival_hr.R` requires R ≥ 4.5
> with `haven`, `dplyr`, `stringr`, and `survival`.

## Pipeline

```
SRTR analytic files (.sav)        ← SRTR DUA; NOT included
        │
        ▼
precompute_final.py + precompute_survival_hr.R
        │
        ▼
viz_*.csv  (aggregate, de-identified; included)  ──►  app_final.py  (Streamlit dashboard)
```

## Data availability & privacy

Source SRTR data are confidential and governed by a Data Use Agreement; they are **not included** in
this repository (`*.sav` files are git-ignored). Only the pre-aggregated, de-identified summary tables
required to render the dashboard are committed. The statistical analysis code for the manuscript is
maintained separately and is available from the corresponding authors on reasonable request.

## Citation

Yang Z, Liu CR, *et al.* Donor Care Unit Availability and Organ Procurement Organization Performance
in Lung Transplantation. *Manuscript under review.* (Update with the full citation upon publication.)

## Acknowledgement

The interactive tool was inspired by Harvard Medical School **BMI 706: Data Visualization for
Biomedical Applications** (Prof. Nils Gehlenborg).
