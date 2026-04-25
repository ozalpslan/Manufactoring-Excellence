from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.oee import calculate_oee


REQUIRED_FIELDS = [
    "date",
    "shift",
    "line",
    "machine",
    "product_family",
    "planned_shift_minutes",
    "planned_break_minutes",
    "planned_production_time_minutes",
    "unplanned_downtime_minutes",
    "downtime_reason",
    "ideal_cycle_time_seconds",
    "total_count",
    "defect_count",
]


@dataclass(frozen=True)
class Issue:
    row_id: int
    issue_category: str
    issue_detail: str
    severity: str
    recommended_action: str


def _is_missing(value: object) -> bool:
    return pd.isna(value) or (isinstance(value, str) and value.strip() == "")


def _to_number(value: object) -> float | None:
    converted = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(converted):
        return None
    return float(converted)


def validate_mes_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Validate raw MES-like records and return clean records plus issue log.

    Error rows are removed from the clean dataset. Warning rows are kept so the
    dashboard can show suspicious but still analyzable records, such as
    performance above 100%.
    """
    working = df.copy().reset_index(drop=True)
    working.insert(0, "source_row_id", working.index + 1)
    calculated = calculate_oee(working)
    issues: list[Issue] = []

    missing_columns = [column for column in REQUIRED_FIELDS if column not in working.columns]
    for column in missing_columns:
        issues.append(
            Issue(
                row_id=0,
                issue_category="missing field",
                issue_detail=f"Required column is missing: {column}",
                severity="Error",
                recommended_action="Add the missing field to the MES export mapping.",
            )
        )

    for idx, row in working.iterrows():
        row_id = int(row["source_row_id"])

        for column in REQUIRED_FIELDS:
            if column in working.columns and _is_missing(row[column]):
                issues.append(
                    Issue(
                        row_id=row_id,
                        issue_category="missing field",
                        issue_detail=f"{column} is missing.",
                        severity="Error" if column in {"date", "shift", "line", "machine"} else "Warning",
                        recommended_action="Complete the missing MES field before daily KPI publication.",
                    )
                )

        planned_shift = _to_number(row.get("planned_shift_minutes"))
        planned_break = _to_number(row.get("planned_break_minutes"))
        planned_time = _to_number(row.get("planned_production_time_minutes"))
        downtime = _to_number(row.get("unplanned_downtime_minutes"))
        total_count = _to_number(row.get("total_count"))
        defect_count = _to_number(row.get("defect_count"))
        ideal_cycle_time = _to_number(row.get("ideal_cycle_time_seconds"))

        if planned_shift is not None and planned_break is not None and planned_time is not None:
            expected_planned_time = planned_shift - planned_break
            if abs(expected_planned_time - planned_time) > 0.01:
                issues.append(
                    Issue(
                        row_id=row_id,
                        issue_category="invalid downtime",
                        issue_detail=(
                            "planned_production_time_minutes does not match "
                            "planned_shift_minutes minus planned_break_minutes."
                        ),
                        severity="Warning",
                        recommended_action="Align shift calendar and break-time logic in the MES extraction.",
                    )
                )

        if planned_time is not None and planned_time <= 0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid downtime",
                    issue_detail="planned_production_time_minutes must be greater than zero.",
                    severity="Error",
                    recommended_action="Review shift calendar, break duration, and downtime mapping.",
                )
            )

        if downtime is not None and downtime < 0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid downtime",
                    issue_detail="unplanned_downtime_minutes cannot be negative.",
                    severity="Error",
                    recommended_action="Correct the downtime transaction sign before KPI calculation.",
                )
            )

        if planned_time is not None and downtime is not None and downtime > planned_time:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid downtime",
                    issue_detail="unplanned_downtime_minutes is greater than planned production time.",
                    severity="Error",
                    recommended_action="Check duplicate downtime entries or incorrect shift assignment.",
                )
            )

        if total_count is not None and total_count < 0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid count",
                    issue_detail="total_count cannot be negative.",
                    severity="Error",
                    recommended_action="Correct production count sign or MES counter reset logic.",
                )
            )

        if defect_count is not None and defect_count < 0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid count",
                    issue_detail="defect_count cannot be negative.",
                    severity="Error",
                    recommended_action="Correct quality count sign before report generation.",
                )
            )

        if total_count is not None and total_count == 0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid count",
                    issue_detail="total_count is zero, so Quality and OEE cannot be calculated for this record.",
                    severity="Warning",
                    recommended_action="Confirm whether this was a no-production shift or a missing count upload.",
                )
            )

        if (
            total_count is not None
            and defect_count is not None
            and total_count >= 0
            and defect_count > total_count
        ):
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid count",
                    issue_detail="defect_count is greater than total_count.",
                    severity="Error",
                    recommended_action="Reconcile quality rejection counts with total production counts.",
                )
            )

        if ideal_cycle_time is not None and ideal_cycle_time <= 0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="invalid count",
                    issue_detail="ideal_cycle_time_seconds must be greater than zero.",
                    severity="Error",
                    recommended_action="Update the product master data cycle-time value.",
                )
            )

        performance = calculated.loc[idx, "performance"]
        if pd.notna(performance) and performance > 1.0:
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="performance over 100%",
                    issue_detail=f"Performance is {performance:.1%}, which indicates a cycle-time or count issue.",
                    severity="Warning",
                    recommended_action="Validate ideal cycle time, counter accuracy, and small-stop capture.",
                )
            )

        correction_required = row.get("mes_correction_required")
        if isinstance(correction_required, str):
            correction_required = correction_required.strip().lower() in {"true", "yes", "1"}
        if bool(correction_required):
            reason = row.get("mes_correction_reason", "No reason provided")
            issues.append(
                Issue(
                    row_id=row_id,
                    issue_category="MES correction required",
                    issue_detail=f"MES correction required: {reason}",
                    severity="Warning",
                    recommended_action="Close the manual correction loop before final reporting.",
                )
            )

    issues_df = pd.DataFrame([issue.__dict__ for issue in issues])
    if issues_df.empty:
        issues_df = pd.DataFrame(
            columns=[
                "row_id",
                "issue_category",
                "issue_detail",
                "severity",
                "recommended_action",
            ]
        )

    if "source_row_id" in calculated.columns:
        error_row_ids = set(issues_df.loc[issues_df["severity"] == "Error", "row_id"])
        warning_row_ids = set(issues_df.loc[issues_df["severity"] == "Warning", "row_id"])
        calculated["has_data_quality_error"] = calculated["source_row_id"].isin(error_row_ids)
        calculated["has_data_quality_warning"] = calculated["source_row_id"].isin(warning_row_ids)
        calculated["data_quality_status"] = "Clean"
        calculated.loc[calculated["has_data_quality_warning"], "data_quality_status"] = "Warning"
        calculated.loc[calculated["has_data_quality_error"], "data_quality_status"] = "Error"
        clean_df = calculated.loc[~calculated["has_data_quality_error"]].copy()
    else:
        clean_df = calculated.copy()

    return clean_df.reset_index(drop=True), issues_df.reset_index(drop=True)
