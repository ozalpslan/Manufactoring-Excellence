# Manufacturing Excellence OEE & Reporting Automation Dashboard

Live Demo: Add the Streamlit Community Cloud URL after deployment  
GitHub Repository: https://github.com/alperozarslan/manufacturing-excellence-oee-dashboard

A digital manufacturing excellence dashboard that automates manual production reporting, validates MES-like production data, calculates OEE, analyzes downtime and scrap losses, and identifies RCA/Kaizen improvement opportunities.

## Business Problem

Manufacturing teams often lose time preparing daily production reports manually: downloading MES exports, copying data into spreadsheets, regrouping downtime reasons, updating OEE formulas, formatting reports, and preparing Power BI refresh files. These steps are largely non-value-added activity and can also hide data-quality issues until after decisions have already been made.

This project shows a practical automated workflow using fully synthetic MES-like data. It converts raw production logs into clean KPIs, flags suspicious records, produces a Power BI-ready dataset, and highlights improvement opportunities for daily performance review.

## Why This Fits Manufacturing Excellence

The dashboard directly supports manufacturing excellence and continuous improvement work:

- Automates manual production reporting steps and estimates NVAA time saved.
- Calculates Availability, Performance, Quality, OEE, scrap rate, and downtime rate.
- Highlights MES data accuracy issues before KPI publication.
- Separates hard data errors from warning signals such as Performance above 100%.
- Uses downtime and scrap losses to prioritize RCA and Kaizen opportunities.
- Exports a standardized dataset that can be imported into Power BI.
- Provides an Excel summary report for MS Office-based reporting routines.

## Features

- Streamlit dashboard with five tabs:
  - Executive Overview
  - OEE & Loss Analysis
  - MES Data Quality
  - RCA & Kaizen Opportunities
  - Power BI / Excel Export
- Plotly charts for daily trends, line comparison, shift comparison, OEE factor breakdown, downtime Pareto, and scrap trend.
- Synthetic production data generator with deliberate MES data-quality issues.
- Rule-based RCA/Kaizen recommendations for recurring loss patterns.
- Downloadable Power BI-ready CSV, filtered cleaned CSV, and Excel report.
- Unit tests for OEE calculations, validation rules, zero-division handling, warning flags, and Kaizen priority sorting.

## OEE Formulas

The project follows the standard OEE structure:

```text
planned_production_time = planned_shift_minutes - planned_break_minutes
operating_time = planned_production_time - unplanned_downtime_minutes
good_count = total_count - defect_count

availability = operating_time / planned_production_time
performance = (ideal_cycle_time_seconds * total_count) / (operating_time * 60)
quality = good_count / total_count
oee = availability * performance * quality

scrap_rate = defect_count / total_count
downtime_rate = unplanned_downtime_minutes / planned_production_time
```

Performance is not capped at 100%. When Performance is above 100%, the dashboard keeps the value visible and flags it as a MES/data-quality warning because it can indicate incorrect ideal cycle time, counter issues, or missing small-stop capture.

References:

- [OEE calculation overview](https://www.oee.com/calculating-oee/)
- [OEE factors: Availability, Performance, Quality](https://www.oee.com/oee-factors/)

## Dataset

All data is synthetic. No real company, brand, factory, production, or logo data is used.

`data/raw_mes_production_log.csv` contains MES-like production records with:

- date, shift, line, machine, product family
- planned shift, break time, planned production time
- unplanned downtime and downtime reason
- ideal cycle time, total count, defect count
- operator team and MES correction fields

`data/manual_reporting_steps.csv` contains manual reporting steps and before/after automation effort.

`data/powerbi_ready_oee_dataset.csv` contains the clean OEE dataset with date keys, calendar columns, KPI decimals, KPI percentages, and data-quality status.

## Dashboard Screenshots

Recommended screenshots for the GitHub README after deployment:

- `docs/screenshots/executive-overview.png`
- `docs/screenshots/oee-loss-analysis.png`
- `docs/screenshots/mes-data-quality.png`
- `docs/screenshots/rca-kaizen-opportunities.png`
- `docs/screenshots/powerbi-excel-export.png`

The local smoke test verified the rendered Streamlit app, tabs, export buttons, and browser console. Browser screenshot capture timed out in the local Codex browser session, so screenshots should be added from the deployed Streamlit app or a local browser session before publishing the final public README.

## Local Setup

```bash
python3 -m pip install -r requirements.txt
python3 -m src.data_generation
python3 -m streamlit run app.py
```

Open the local URL printed by Streamlit, usually:

```text
http://127.0.0.1:8501
```

## Test Command

```bash
python3 -m pytest -q
```

## Deployment Note

Deploy on Streamlit Community Cloud with:

- Repository: `manufacturing-excellence-oee-dashboard`
- Branch: `main`
- Entrypoint: `app.py`
- Python version: `3.12`
- Dependencies: `requirements.txt`

Streamlit deployment references:

- [Deploy your app on Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [App dependencies for Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)

## Power BI Usage Note

1. Open Power BI Desktop.
2. Choose **Get Data > Text/CSV**.
3. Select `data/powerbi_ready_oee_dataset.csv`.
4. Confirm `date` as Date, KPI fields as Decimal Number, and `date_key` as Text.
5. Build visuals from `oee_percent`, `availability_percent`, `performance_percent`, `quality_percent`, `scrap_rate_percent`, and `downtime_rate_percent`.

## CV Bullet

Developed a Manufacturing Excellence dashboard using Python, Streamlit, pandas, and Plotly to automate MES-like production reporting, calculate OEE, validate data quality, analyze downtime/scrap losses, and identify RCA/Kaizen improvement opportunities.
