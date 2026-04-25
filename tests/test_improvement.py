import pandas as pd

from src.improvement import calculate_nvaa_savings, identify_kaizen_opportunities


def test_nvaa_savings_calculates_saved_minutes_and_hours():
    steps = pd.DataFrame(
        [
            {
                "process_step": "Daily report formatting",
                "current_owner": "Production clerk",
                "frequency": "Daily",
                "before_minutes": 30,
                "after_minutes": 5,
                "value_added_type": "NVAA",
                "automation_note": "Standard report export",
            }
        ]
    )

    result = calculate_nvaa_savings(steps).iloc[0]

    assert result["time_saved_minutes"] == 25
    assert result["monthly_saved_minutes"] == 25 * 22
    assert result["monthly_saved_hours"] == (25 * 22) / 60


def test_kaizen_priority_score_sorts_biggest_loss_first():
    oee_df = pd.DataFrame(
        [
            {
                "source_row_id": 1,
                "date": "2026-01-06",
                "line": "Line 1",
                "machine": "Filler 1",
                "downtime_reason": "Breakdown",
                "unplanned_downtime_minutes": 150,
                "defect_count": 20,
                "oee": 0.55,
                "scrap_rate": 0.02,
            },
            {
                "source_row_id": 2,
                "date": "2026-01-06",
                "line": "Line 2",
                "machine": "Wrapper 2",
                "downtime_reason": "Changeover",
                "unplanned_downtime_minutes": 30,
                "defect_count": 5,
                "oee": 0.78,
                "scrap_rate": 0.01,
            },
        ]
    )

    result = identify_kaizen_opportunities(oee_df)

    assert result.loc[0, "downtime_reason"] == "Breakdown"
    assert result.loc[0, "priority_score"] > result.loc[1, "priority_score"]
