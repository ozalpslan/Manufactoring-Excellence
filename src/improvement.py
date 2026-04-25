from __future__ import annotations

import pandas as pd


FREQUENCY_TO_MONTHLY_OCCURRENCES = {
    "Shiftly": 65,
    "Daily": 22,
    "Weekly": 4,
    "Monthly": 1,
}


RECOMMENDATION_RULES = {
    "Changeover": {
        "rca": "Setup variation and non-standard handoff steps are likely increasing changeover losses.",
        "kaizen": "Run a SMED workshop and introduce a standardized setup checklist.",
    },
    "Breakdown": {
        "rca": "Repeated technical stops may point to weak preventive-maintenance triggers.",
        "kaizen": "Review preventive-maintenance intervals and top-failure spare-parts readiness.",
    },
    "Material Waiting": {
        "rca": "Line starvation suggests a gap in staging, replenishment, or kanban sizing.",
        "kaizen": "Review material staging windows, supermarket levels, and kanban signals.",
    },
    "Quality Hold": {
        "rca": "Quality containment may be reacting late to process-parameter drift.",
        "kaizen": "Review process parameters, first-off checks, and quality-gate escalation rules.",
    },
    "Packaging Jam": {
        "rca": "Packaging-flow instability may be linked to machine condition or packaging material variation.",
        "kaizen": "Check packaging equipment condition, change parts, and material specification stability.",
    },
    "Cleaning": {
        "rca": "Cleaning duration variation can indicate unclear standards or poor preparation.",
        "kaizen": "Standardize cleaning preparation, tools, and release criteria.",
    },
    "Minor Stops": {
        "rca": "Frequent short stops are often under-classified and hide repeatable micro-losses.",
        "kaizen": "Capture minor-stop tags at operator level and review the top repeat locations daily.",
    },
}


def calculate_nvaa_savings(manual_steps_df: pd.DataFrame) -> pd.DataFrame:
    result = manual_steps_df.copy()
    result["before_minutes"] = pd.to_numeric(result["before_minutes"], errors="coerce").fillna(0)
    result["after_minutes"] = pd.to_numeric(result["after_minutes"], errors="coerce").fillna(0)
    result["time_saved_minutes"] = (result["before_minutes"] - result["after_minutes"]).clip(lower=0)
    result["saving_percent"] = result["time_saved_minutes"] / result["before_minutes"].where(
        result["before_minutes"] > 0
    )
    result["monthly_occurrences"] = result["frequency"].map(FREQUENCY_TO_MONTHLY_OCCURRENCES).fillna(1)
    result["monthly_before_minutes"] = result["before_minutes"] * result["monthly_occurrences"]
    result["monthly_after_minutes"] = result["after_minutes"] * result["monthly_occurrences"]
    result["monthly_saved_minutes"] = result["time_saved_minutes"] * result["monthly_occurrences"]
    result["monthly_saved_hours"] = result["monthly_saved_minutes"] / 60
    return result


def _recommendation_for(reason: str) -> tuple[str, str]:
    rule = RECOMMENDATION_RULES.get(
        reason,
        {
            "rca": "Loss pattern should be reviewed with operators and maintenance using a short RCA session.",
            "kaizen": "Create a focused improvement action with owner, due date, and before/after KPI tracking.",
        },
    )
    return rule["rca"], rule["kaizen"]


def identify_kaizen_opportunities(oee_df: pd.DataFrame) -> pd.DataFrame:
    if oee_df.empty:
        return pd.DataFrame(
            columns=[
                "opportunity",
                "downtime_reason",
                "affected_line",
                "affected_machine",
                "occurrence_count",
                "total_downtime_minutes",
                "total_defects",
                "avg_oee",
                "avg_scrap_rate",
                "priority_score",
                "rca_hypothesis",
                "kaizen_recommendation",
            ]
        )

    working = oee_df.copy()
    working["unplanned_downtime_minutes"] = pd.to_numeric(
        working["unplanned_downtime_minutes"], errors="coerce"
    ).fillna(0)
    working["defect_count"] = pd.to_numeric(working["defect_count"], errors="coerce").fillna(0)
    working["oee"] = pd.to_numeric(working["oee"], errors="coerce")
    working["scrap_rate"] = pd.to_numeric(working["scrap_rate"], errors="coerce")

    grouped = (
        working.groupby(["downtime_reason", "line", "machine"], dropna=False)
        .agg(
            occurrence_count=("source_row_id", "count") if "source_row_id" in working.columns else ("date", "count"),
            total_downtime_minutes=("unplanned_downtime_minutes", "sum"),
            total_defects=("defect_count", "sum"),
            avg_oee=("oee", "mean"),
            avg_scrap_rate=("scrap_rate", "mean"),
        )
        .reset_index()
    )
    grouped = grouped.loc[
        (grouped["total_downtime_minutes"] > 0) | (grouped["total_defects"] > 0)
    ].copy()

    if grouped.empty:
        return identify_kaizen_opportunities(pd.DataFrame())

    oee_loss_points = (1 - grouped["avg_oee"].fillna(0)).clip(lower=0) * 100
    grouped["priority_score"] = (
        grouped["total_downtime_minutes"] * 0.55
        + grouped["total_defects"] * 0.02
        + grouped["occurrence_count"] * 4
        + oee_loss_points * 0.75
    ).round(1)

    recommendations = grouped["downtime_reason"].apply(_recommendation_for)
    grouped["rca_hypothesis"] = [item[0] for item in recommendations]
    grouped["kaizen_recommendation"] = [item[1] for item in recommendations]
    grouped["opportunity"] = (
        grouped["downtime_reason"].fillna("Unclassified")
        + " loss on "
        + grouped["line"].fillna("unknown line")
    )
    grouped = grouped.rename(
        columns={
            "line": "affected_line",
            "machine": "affected_machine",
        }
    )

    return grouped[
        [
            "opportunity",
            "downtime_reason",
            "affected_line",
            "affected_machine",
            "occurrence_count",
            "total_downtime_minutes",
            "total_defects",
            "avg_oee",
            "avg_scrap_rate",
            "priority_score",
            "rca_hypothesis",
            "kaizen_recommendation",
        ]
    ].sort_values("priority_score", ascending=False, ignore_index=True)
