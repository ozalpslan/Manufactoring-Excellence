import math

import pandas as pd

from src.oee import calculate_oee


def test_calculates_availability_performance_quality_and_oee():
    df = pd.DataFrame(
        [
            {
                "planned_shift_minutes": 480,
                "planned_break_minutes": 60,
                "planned_production_time_minutes": 420,
                "unplanned_downtime_minutes": 47,
                "ideal_cycle_time_seconds": 1.0,
                "total_count": 19271,
                "defect_count": 423,
            }
        ]
    )

    result = calculate_oee(df).iloc[0]

    assert math.isclose(result["availability"], 373 / 420, rel_tol=1e-6)
    assert math.isclose(result["performance"], 19271 / (373 * 60), rel_tol=1e-6)
    assert math.isclose(result["quality"], 18848 / 19271, rel_tol=1e-6)
    assert math.isclose(
        result["oee"],
        (373 / 420) * (19271 / (373 * 60)) * (18848 / 19271),
        rel_tol=1e-6,
    )


def test_zero_total_count_does_not_raise_divide_by_zero():
    df = pd.DataFrame(
        [
            {
                "planned_shift_minutes": 480,
                "planned_break_minutes": 60,
                "planned_production_time_minutes": 420,
                "unplanned_downtime_minutes": 20,
                "ideal_cycle_time_seconds": 1.0,
                "total_count": 0,
                "defect_count": 0,
            }
        ]
    )

    result = calculate_oee(df).iloc[0]

    assert not math.isinf(result["performance"])
    assert pd.isna(result["quality"])
    assert pd.isna(result["oee"])


def test_performance_over_100_is_not_clipped():
    df = pd.DataFrame(
        [
            {
                "planned_shift_minutes": 480,
                "planned_break_minutes": 60,
                "planned_production_time_minutes": 420,
                "unplanned_downtime_minutes": 120,
                "ideal_cycle_time_seconds": 2.0,
                "total_count": 10000,
                "defect_count": 100,
            }
        ]
    )

    result = calculate_oee(df).iloc[0]

    assert result["performance"] > 1.0
    assert result["performance_over_100"]
