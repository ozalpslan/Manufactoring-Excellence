from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PRODUCT_FAMILIES = ["Ice Cream Bar", "Cone", "Cup", "Multipack", "Sandwich"]
DOWNTIME_REASONS = [
    "Breakdown",
    "Changeover",
    "Cleaning",
    "Material Waiting",
    "Packaging Jam",
    "Quality Hold",
    "Minor Stops",
]
LINES = ["Line 1", "Line 2", "Line 3", "Line 4"]
MACHINES = {
    "Line 1": ["Filler 1", "Wrapper 1", "Cartoner 1"],
    "Line 2": ["Filler 2", "Freezer 2", "Case Packer 2"],
    "Line 3": ["Moulder 3", "Wrapper 3", "Case Packer 3"],
    "Line 4": ["Extruder 4", "Wrapper 4", "Cartoner 4"],
}
SHIFTS = ["Morning", "Evening", "Night"]
TEAMS = ["Team A", "Team B", "Team C", "Team D"]


def generate_mes_production_log(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start_date = pd.Timestamp("2026-01-06")
    dates = pd.date_range(start_date, periods=42, freq="D")
    records: list[dict[str, object]] = []

    for date in dates:
        for shift in SHIFTS:
            for line in LINES:
                product_family = rng.choice(PRODUCT_FAMILIES)
                machine = rng.choice(MACHINES[line])
                planned_shift_minutes = 480
                planned_break_minutes = 45 if shift != "Night" else 40
                planned_production_time = planned_shift_minutes - planned_break_minutes
                base_downtime = {
                    "Line 1": 30,
                    "Line 2": 42,
                    "Line 3": 35,
                    "Line 4": 50,
                }[line]
                downtime_reason = rng.choice(
                    DOWNTIME_REASONS,
                    p=[0.18, 0.18, 0.12, 0.12, 0.18, 0.09, 0.13],
                )
                downtime_modifier = {
                    "Breakdown": 22,
                    "Changeover": 18,
                    "Cleaning": 12,
                    "Material Waiting": 16,
                    "Packaging Jam": 24,
                    "Quality Hold": 14,
                    "Minor Stops": 10,
                }[downtime_reason]
                unplanned_downtime = max(
                    0,
                    int(rng.normal(base_downtime + downtime_modifier, 16)),
                )
                ideal_cycle_time = {
                    "Ice Cream Bar": 1.15,
                    "Cone": 1.35,
                    "Cup": 1.05,
                    "Multipack": 1.65,
                    "Sandwich": 1.25,
                }[product_family]
                operating_time = planned_production_time - unplanned_downtime
                performance_factor = rng.normal(0.86, 0.08)
                total_count = max(
                    0,
                    int((operating_time * 60 / ideal_cycle_time) * performance_factor),
                )
                scrap_rate = max(0.005, rng.normal(0.025, 0.012))
                if downtime_reason == "Quality Hold":
                    scrap_rate += 0.025
                defect_count = int(total_count * scrap_rate)

                correction_required = rng.random() < 0.07
                correction_reason = ""
                if correction_required:
                    correction_reason = rng.choice(
                        [
                            "Downtime reason manually reclassified",
                            "Counter reconciliation pending",
                            "Shift handover note missing",
                            "Quality rejection code needs approval",
                        ]
                    )

                records.append(
                    {
                        "date": date.date().isoformat(),
                        "shift": shift,
                        "line": line,
                        "machine": machine,
                        "product_family": product_family,
                        "planned_shift_minutes": planned_shift_minutes,
                        "planned_break_minutes": planned_break_minutes,
                        "planned_production_time_minutes": planned_production_time,
                        "unplanned_downtime_minutes": unplanned_downtime,
                        "downtime_reason": downtime_reason,
                        "ideal_cycle_time_seconds": ideal_cycle_time,
                        "total_count": total_count,
                        "defect_count": defect_count,
                        "operator_team": rng.choice(TEAMS),
                        "mes_correction_required": bool(correction_required),
                        "mes_correction_reason": correction_reason,
                    }
                )

    df = pd.DataFrame(records)

    # Deliberate synthetic MES issues used by the dashboard and tests.
    issue_updates = {
        5: {"line": "", "mes_correction_required": True, "mes_correction_reason": "Line field missing"},
        17: {
            "unplanned_downtime_minutes": 510,
            "mes_correction_required": True,
            "mes_correction_reason": "Downtime exceeds available production time",
        },
        33: {
            "defect_count": int(df.loc[33, "total_count"]) + 25,
            "mes_correction_required": True,
            "mes_correction_reason": "Reject count greater than total count",
        },
        61: {
            "total_count": 0,
            "defect_count": 0,
            "mes_correction_required": True,
            "mes_correction_reason": "Zero-count production record",
        },
        88: {
            "shift": "",
            "mes_correction_required": True,
            "mes_correction_reason": "Shift field missing",
        },
        112: {
            "unplanned_downtime_minutes": -8,
            "mes_correction_required": True,
            "mes_correction_reason": "Negative downtime transaction",
        },
        145: {
            "ideal_cycle_time_seconds": float(df.loc[145, "ideal_cycle_time_seconds"]) * 1.35,
            "mes_correction_required": True,
            "mes_correction_reason": "Ideal cycle time master data needs review",
        },
        190: {
            "planned_production_time_minutes": 460,
            "mes_correction_required": True,
            "mes_correction_reason": "Shift calendar mismatch",
        },
    }
    for row_index, updates in issue_updates.items():
        for column, value in updates.items():
            df.loc[row_index, column] = value

    return df


def generate_manual_reporting_steps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "process_step": "MES export download",
                "current_owner": "Production clerk",
                "frequency": "Daily",
                "before_minutes": 20,
                "after_minutes": 4,
                "value_added_type": "NVAA",
                "automation_note": "Automated CSV ingestion from the standard export folder.",
            },
            {
                "process_step": "Excel copy-paste consolidation",
                "current_owner": "Shift supervisor",
                "frequency": "Daily",
                "before_minutes": 35,
                "after_minutes": 3,
                "value_added_type": "NVAA",
                "automation_note": "pandas pipeline consolidates all records into one clean table.",
            },
            {
                "process_step": "Downtime reason grouping",
                "current_owner": "Process engineer",
                "frequency": "Daily",
                "before_minutes": 25,
                "after_minutes": 5,
                "value_added_type": "NNVA",
                "automation_note": "Standard downtime taxonomy and automatic Pareto grouping.",
            },
            {
                "process_step": "OEE formula update",
                "current_owner": "Manufacturing excellence analyst",
                "frequency": "Daily",
                "before_minutes": 30,
                "after_minutes": 2,
                "value_added_type": "NVAA",
                "automation_note": "Availability, Performance, Quality, and OEE calculated automatically.",
            },
            {
                "process_step": "Daily report formatting",
                "current_owner": "Production clerk",
                "frequency": "Daily",
                "before_minutes": 25,
                "after_minutes": 5,
                "value_added_type": "NVAA",
                "automation_note": "Streamlit and Excel export standardize the report layout.",
            },
            {
                "process_step": "Power BI dataset refresh preparation",
                "current_owner": "Data analyst",
                "frequency": "Weekly",
                "before_minutes": 45,
                "after_minutes": 8,
                "value_added_type": "NVAA",
                "automation_note": "Power BI-ready dataset generated with date keys and KPI columns.",
            },
        ]
    )


def write_default_datasets(data_dir: str | Path = "data") -> None:
    from src.exports import create_powerbi_ready_dataset
    from src.validation import validate_mes_data

    output_dir = Path(data_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_df = generate_mes_production_log()
    manual_steps_df = generate_manual_reporting_steps()
    clean_df, _ = validate_mes_data(raw_df)
    powerbi_df = create_powerbi_ready_dataset(clean_df)

    raw_df.to_csv(output_dir / "raw_mes_production_log.csv", index=False)
    manual_steps_df.to_csv(output_dir / "manual_reporting_steps.csv", index=False)
    powerbi_df.to_csv(output_dir / "powerbi_ready_oee_dataset.csv", index=False)


if __name__ == "__main__":
    write_default_datasets()
