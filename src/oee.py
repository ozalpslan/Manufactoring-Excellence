from __future__ import annotations

import numpy as np
import pandas as pd


def _numeric_series(df: pd.DataFrame, column: str, default: float = 0.0) -> pd.Series:
    """Return a numeric series aligned to df.index, using default when the column is absent."""
    if column not in df.columns:
        return pd.Series(default, index=df.index, dtype="float64")
    return pd.to_numeric(df[column], errors="coerce")


def _safe_divide(numerator: pd.Series, denominator: pd.Series, valid_mask: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=numerator.index, dtype="float64")
    result.loc[valid_mask] = numerator.loc[valid_mask] / denominator.loc[valid_mask]
    return result


def calculate_oee(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate OEE and related production-loss metrics.

    Performance is intentionally not capped at 100%. Values above 1.0 are useful
    MES/data-quality signals and are flagged by the validation module.
    """
    result = df.copy()

    planned_shift = _numeric_series(result, "planned_shift_minutes")
    planned_break = _numeric_series(result, "planned_break_minutes")
    calculated_planned_time = planned_shift - planned_break

    if "planned_production_time_minutes" in result.columns:
        reported_planned_time = _numeric_series(result, "planned_production_time_minutes")
        planned_time = reported_planned_time.where(reported_planned_time.notna(), calculated_planned_time)
    else:
        planned_time = calculated_planned_time

    downtime = _numeric_series(result, "unplanned_downtime_minutes")
    ideal_cycle_time = _numeric_series(result, "ideal_cycle_time_seconds")
    total_count = _numeric_series(result, "total_count")
    defect_count = _numeric_series(result, "defect_count")

    operating_time = planned_time - downtime
    good_count = total_count - defect_count

    availability_mask = (planned_time > 0) & (operating_time >= 0)
    performance_mask = (operating_time > 0) & (ideal_cycle_time > 0) & (total_count >= 0)
    quality_mask = (total_count > 0) & (good_count >= 0)
    downtime_mask = planned_time > 0

    result["calculated_planned_production_time_minutes"] = calculated_planned_time
    result["planned_production_time_minutes"] = planned_time
    result["operating_time_minutes"] = operating_time
    result["good_count"] = good_count

    result["availability"] = _safe_divide(operating_time, planned_time, availability_mask)
    result["performance"] = _safe_divide(
        ideal_cycle_time * total_count,
        operating_time * 60,
        performance_mask,
    )
    result["quality"] = _safe_divide(good_count, total_count, quality_mask)
    result["oee"] = result["availability"] * result["performance"] * result["quality"]
    result["scrap_rate"] = _safe_divide(defect_count, total_count, total_count > 0)
    result["downtime_rate"] = _safe_divide(downtime, planned_time, downtime_mask)
    result["performance_over_100"] = result["performance"] > 1.0

    return result
