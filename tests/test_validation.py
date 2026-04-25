import pandas as pd

from src.validation import validate_mes_data


def _valid_row(**overrides):
    row = {
        "date": "2026-01-06",
        "shift": "Morning",
        "line": "Line 1",
        "machine": "Filler 1",
        "product_family": "Cup",
        "planned_shift_minutes": 480,
        "planned_break_minutes": 60,
        "planned_production_time_minutes": 420,
        "unplanned_downtime_minutes": 30,
        "downtime_reason": "Breakdown",
        "ideal_cycle_time_seconds": 1.0,
        "total_count": 1000,
        "defect_count": 20,
        "operator_team": "Team A",
        "mes_correction_required": False,
        "mes_correction_reason": "",
    }
    row.update(overrides)
    return row


def test_defect_count_greater_than_total_count_creates_validation_error():
    _, issues = validate_mes_data(pd.DataFrame([_valid_row(total_count=100, defect_count=101)]))

    issue_text = " ".join(issues["issue_detail"].tolist())
    assert "defect_count is greater than total_count" in issue_text
    assert "Error" in issues["severity"].tolist()


def test_downtime_greater_than_planned_time_creates_validation_error():
    _, issues = validate_mes_data(
        pd.DataFrame([_valid_row(planned_production_time_minutes=420, unplanned_downtime_minutes=421)])
    )

    issue_text = " ".join(issues["issue_detail"].tolist())
    assert "unplanned_downtime_minutes is greater than planned production time" in issue_text
    assert "Error" in issues["severity"].tolist()


def test_zero_total_count_is_warning_without_dropping_pipeline():
    clean_df, issues = validate_mes_data(pd.DataFrame([_valid_row(total_count=0, defect_count=0)]))

    assert len(clean_df) == 1
    assert "Warning" in issues["severity"].tolist()
    assert "total_count is zero" in " ".join(issues["issue_detail"].tolist())


def test_performance_over_100_is_flagged_as_warning():
    clean_df, issues = validate_mes_data(
        pd.DataFrame(
            [
                _valid_row(
                    unplanned_downtime_minutes=120,
                    ideal_cycle_time_seconds=2.0,
                    total_count=10000,
                    defect_count=50,
                )
            ]
        )
    )

    assert clean_df.loc[0, "performance_over_100"]
    assert "performance over 100%" in issues["issue_category"].tolist()
    assert set(issues["severity"]) == {"Warning"}
