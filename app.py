from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_generation import write_default_datasets
from src.exports import create_excel_summary_report, create_powerbi_ready_dataset
from src.improvement import calculate_nvaa_savings, identify_kaizen_opportunities
from src.validation import validate_mes_data


BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw_mes_production_log.csv"
MANUAL_STEPS_PATH = DATA_DIR / "manual_reporting_steps.csv"
POWERBI_DATA_PATH = DATA_DIR / "powerbi_ready_oee_dataset.csv"


st.set_page_config(
    page_title="Manufacturing Excellence OEE Dashboard",
    page_icon="ME",
    layout="wide",
)


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.25rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e3e8ef;
        border-radius: 8px;
        padding: 0.85rem 1rem;
    }
    div[data-testid="stMetricLabel"] p {
        color: #5b6776;
        font-size: 0.85rem;
    }
    div[data-testid="stMetricValue"] {
        color: #17212b;
    }
    .app-subtitle {
        color: #4f5b68;
        margin-top: -0.35rem;
        max-width: 1040px;
    }
    .section-note {
        color: #586575;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not RAW_DATA_PATH.exists() or not MANUAL_STEPS_PATH.exists() or not POWERBI_DATA_PATH.exists():
        write_default_datasets(DATA_DIR)

    raw_df = pd.read_csv(RAW_DATA_PATH)
    manual_steps_df = pd.read_csv(MANUAL_STEPS_PATH)
    clean_oee_df, issues_df = validate_mes_data(raw_df)
    clean_oee_df["date"] = pd.to_datetime(clean_oee_df["date"], errors="coerce")
    raw_df["date"] = pd.to_datetime(raw_df["date"], errors="coerce")
    powerbi_df = create_powerbi_ready_dataset(clean_oee_df)
    return raw_df, manual_steps_df, clean_oee_df, issues_df, powerbi_df


def as_percent(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.1%}"


def as_number(value: float | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:,.{decimals}f}"


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def boolean_mask(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "yes", "1"})


def apply_filters(
    df: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp],
    lines: list[str],
    shifts: list[str],
    families: list[str],
) -> pd.DataFrame:
    filtered = df.copy()
    start_date, end_date = date_range
    filtered = filtered.loc[
        (filtered["date"].dt.date >= start_date.date())
        & (filtered["date"].dt.date <= end_date.date())
    ]
    if lines:
        filtered = filtered.loc[filtered["line"].isin(lines)]
    if shifts:
        filtered = filtered.loc[filtered["shift"].isin(shifts)]
    if families:
        filtered = filtered.loc[filtered["product_family"].isin(families)]
    return filtered


def filter_issue_table(
    issues_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    filtered_source_ids: set[int],
) -> pd.DataFrame:
    context_columns = [
        "source_row_id",
        "date",
        "shift",
        "line",
        "machine",
        "product_family",
        "downtime_reason",
    ]
    raw_context = raw_df.copy().reset_index(drop=True)
    raw_context.insert(0, "source_row_id", raw_context.index + 1)
    issue_context = issues_df.merge(
        raw_context[context_columns],
        left_on="row_id",
        right_on="source_row_id",
        how="left",
    )
    return issue_context.loc[
        issue_context["row_id"].eq(0) | issue_context["row_id"].isin(filtered_source_ids)
    ].drop(columns=["source_row_id"], errors="ignore")


def plot_empty(message: str) -> None:
    st.info(message)


raw_df, manual_steps_df, clean_oee_df, issues_df, full_powerbi_df = load_data()
nvaa_df = calculate_nvaa_savings(manual_steps_df)

st.title("Manufacturing Excellence OEE & Reporting Automation Dashboard")

min_date = clean_oee_df["date"].min()
max_date = clean_oee_df["date"].max()
filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns([1.5, 1, 1, 1.25])

with filter_col_1:
    selected_dates = st.date_input(
        "Date range",
        value=(min_date.date(), max_date.date()),
        min_value=min_date.date(),
        max_value=max_date.date(),
    )
with filter_col_2:
    selected_lines = st.multiselect("Line", sorted(clean_oee_df["line"].dropna().unique()))
with filter_col_3:
    selected_shifts = st.multiselect("Shift", sorted(clean_oee_df["shift"].dropna().unique()))
with filter_col_4:
    selected_families = st.multiselect(
        "Product family",
        sorted(clean_oee_df["product_family"].dropna().unique()),
    )

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    date_range = (pd.Timestamp(selected_dates[0]), pd.Timestamp(selected_dates[1]))
else:
    selected_date = pd.Timestamp(selected_dates)
    date_range = (selected_date, selected_date)

filtered_oee_df = apply_filters(
    clean_oee_df,
    date_range,
    selected_lines,
    selected_shifts,
    selected_families,
)
filtered_raw_df = apply_filters(
    raw_df,
    date_range,
    selected_lines,
    selected_shifts,
    selected_families,
)
filtered_source_ids = set((filtered_raw_df.index + 1).astype(int))
filtered_issues_df = filter_issue_table(issues_df, raw_df, filtered_source_ids)
filtered_powerbi_df = create_powerbi_ready_dataset(filtered_oee_df)
kaizen_df = identify_kaizen_opportunities(filtered_oee_df)

tabs = st.tabs(
    [
        "Executive Overview",
        "OEE & Loss Analysis",
        "MES Data Quality",
        "RCA & Kaizen Opportunities",
        "Power BI / Excel Export",
    ]
)

with tabs[0]:
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_5, metric_6, metric_7, metric_8 = st.columns(4)

    with metric_1:
        st.metric("Overall OEE", as_percent(filtered_oee_df["oee"].mean()))
    with metric_2:
        st.metric("Availability", as_percent(filtered_oee_df["availability"].mean()))
    with metric_3:
        st.metric("Performance", as_percent(filtered_oee_df["performance"].mean()))
    with metric_4:
        st.metric("Quality", as_percent(filtered_oee_df["quality"].mean()))
    with metric_5:
        st.metric("Scrap Rate", as_percent(filtered_oee_df["scrap_rate"].mean()))
    with metric_6:
        st.metric(
            "Total Downtime",
            f"{as_number(filtered_oee_df['unplanned_downtime_minutes'].sum())} min",
        )
    with metric_7:
        st.metric(
            "Estimated NVAA Time Saved",
            f"{nvaa_df['monthly_saved_hours'].sum():.1f} h/month",
        )
    with metric_8:
        st.metric("Records in Scope", as_number(len(filtered_oee_df)))

    st.divider()
    overview_left, overview_right = st.columns([1.35, 1])
    with overview_left:
        if filtered_oee_df.empty:
            plot_empty("No records match the current filter selection.")
        else:
            daily_oee = (
                filtered_oee_df.groupby("date", as_index=False)[["oee", "availability", "performance", "quality"]]
                .mean()
                .sort_values("date")
            )
            fig = px.line(
                daily_oee,
                x="date",
                y=["oee", "availability", "performance", "quality"],
                markers=True,
                labels={"value": "Rate", "date": "Date", "variable": "Metric"},
                title="Daily OEE and Factor Trend",
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(legend_title_text="", height=420)
            st.plotly_chart(fig, use_container_width=True)

    with overview_right:
        st.subheader("Manual Reporting Automation Impact")
        savings_view = nvaa_df[
            [
                "process_step",
                "frequency",
                "before_minutes",
                "after_minutes",
                "time_saved_minutes",
                "monthly_saved_hours",
                "value_added_type",
            ]
        ].copy()
        st.dataframe(
            savings_view,
            hide_index=True,
            use_container_width=True,
            column_config={
                "process_step": "Process step",
                "before_minutes": "Before min",
                "after_minutes": "After min",
                "time_saved_minutes": "Saved min",
                "monthly_saved_hours": st.column_config.NumberColumn("Saved h/month", format="%.1f"),
            },
        )

with tabs[1]:
    if filtered_oee_df.empty:
        plot_empty("No records match the current filter selection.")
    else:
        analysis_col_1, analysis_col_2 = st.columns(2)
        with analysis_col_1:
            line_oee = (
                filtered_oee_df.groupby("line", as_index=False)["oee"]
                .mean()
                .sort_values("oee", ascending=False)
            )
            fig = px.bar(
                line_oee,
                x="line",
                y="oee",
                color="oee",
                color_continuous_scale=["#D84E35", "#F1B84B", "#1F6F78"],
                labels={"line": "Line", "oee": "OEE"},
                title="Line-Based OEE Comparison",
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(height=380, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

        with analysis_col_2:
            shift_oee = (
                filtered_oee_df.groupby("shift", as_index=False)["oee"]
                .mean()
                .sort_values("oee", ascending=False)
            )
            fig = px.bar(
                shift_oee,
                x="shift",
                y="oee",
                color="shift",
                color_discrete_sequence=["#1F6F78", "#D84E35", "#6A8D73"],
                labels={"shift": "Shift", "oee": "OEE"},
                title="Shift OEE Comparison",
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        factor_col, scrap_col = st.columns(2)
        with factor_col:
            factor_view = filtered_oee_df[["availability", "performance", "quality"]].mean().reset_index()
            factor_view.columns = ["factor", "value"]
            fig = px.bar(
                factor_view,
                x="factor",
                y="value",
                color="factor",
                color_discrete_sequence=["#1F6F78", "#F1B84B", "#6A8D73"],
                labels={"factor": "OEE factor", "value": "Rate"},
                title="Availability / Performance / Quality Breakdown",
            )
            fig.update_yaxes(tickformat=".0%")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with scrap_col:
            scrap_trend = (
                filtered_oee_df.groupby("date", as_index=False)["scrap_rate"]
                .mean()
                .sort_values("date")
            )
            fig = px.line(
                scrap_trend,
                x="date",
                y="scrap_rate",
                markers=True,
                labels={"date": "Date", "scrap_rate": "Scrap rate"},
                title="Scrap Rate Trend",
            )
            fig.update_yaxes(tickformat=".1%")
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)

        pareto = (
            filtered_oee_df.groupby("downtime_reason", as_index=False)["unplanned_downtime_minutes"]
            .sum()
            .sort_values("unplanned_downtime_minutes", ascending=False)
        )
        pareto["cumulative_percent"] = (
            pareto["unplanned_downtime_minutes"].cumsum()
            / pareto["unplanned_downtime_minutes"].sum()
            * 100
        )
        fig = go.Figure()
        fig.add_bar(
            x=pareto["downtime_reason"],
            y=pareto["unplanned_downtime_minutes"],
            name="Downtime minutes",
            marker_color="#1F6F78",
        )
        fig.add_trace(
            go.Scatter(
                x=pareto["downtime_reason"],
                y=pareto["cumulative_percent"],
                name="Cumulative %",
                mode="lines+markers",
                yaxis="y2",
                line=dict(color="#D84E35", width=3),
            )
        )
        fig.update_layout(
            title="Downtime Reason Pareto",
            xaxis_title="Downtime reason",
            yaxis=dict(title="Downtime minutes"),
            yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
            height=430,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    issue_count = len(filtered_issues_df)
    error_count = int((filtered_issues_df["severity"] == "Error").sum()) if issue_count else 0
    warning_count = int((filtered_issues_df["severity"] == "Warning").sum()) if issue_count else 0
    performance_warning_count = int(
        (filtered_issues_df["issue_category"] == "performance over 100%").sum()
    ) if issue_count else 0
    correction_count = int(boolean_mask(filtered_raw_df["mes_correction_required"]).sum())

    dq_col_1, dq_col_2, dq_col_3, dq_col_4 = st.columns(4)
    with dq_col_1:
        st.metric("Data Quality Issues", as_number(issue_count))
    with dq_col_2:
        st.metric("Error Issues", as_number(error_count))
    with dq_col_3:
        st.metric("Warning Issues", as_number(warning_count))
    with dq_col_4:
        st.metric("Correction Required Records", as_number(correction_count))

    dq_chart_col, warning_col = st.columns([1.1, 1])
    with dq_chart_col:
        if filtered_issues_df.empty:
            plot_empty("No MES data-quality issues in the current filter selection.")
        else:
            issue_summary = (
                filtered_issues_df.groupby(["issue_category", "severity"], as_index=False)
                .size()
                .sort_values("size", ascending=False)
            )
            fig = px.bar(
                issue_summary,
                x="issue_category",
                y="size",
                color="severity",
                color_discrete_map={"Error": "#D84E35", "Warning": "#F1B84B"},
                labels={"issue_category": "Issue category", "size": "Records"},
                title="MES Data Quality Issue Categories",
            )
            fig.update_layout(height=380, xaxis_tickangle=-20)
            st.plotly_chart(fig, use_container_width=True)

    with warning_col:
        st.subheader("MES Warning Signals")
        st.metric("Performance > 100% Warnings", as_number(performance_warning_count))
        st.metric(
            "Records Kept With Warning",
            as_number(int(filtered_oee_df["has_data_quality_warning"].sum())),
        )
        st.markdown(
            "<p class='section-note'>Performance above 100% is not clipped because it is a useful "
            "signal for cycle-time master-data, counter, or small-stop capture review.</p>",
            unsafe_allow_html=True,
        )

    st.subheader("Data Quality Issue Table")
    st.dataframe(
        filtered_issues_df[
            [
                "row_id",
                "date",
                "shift",
                "line",
                "machine",
                "product_family",
                "issue_category",
                "severity",
                "issue_detail",
                "recommended_action",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Correction Required Records")
    correction_records = filtered_raw_df.loc[boolean_mask(filtered_raw_df["mes_correction_required"])]
    st.dataframe(
        correction_records[
            [
                "date",
                "shift",
                "line",
                "machine",
                "product_family",
                "downtime_reason",
                "mes_correction_reason",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )

with tabs[3]:
    if filtered_oee_df.empty or kaizen_df.empty:
        plot_empty("No RCA or Kaizen opportunities match the current filter selection.")
    else:
        top_reason = (
            filtered_oee_df.groupby("downtime_reason")["unplanned_downtime_minutes"]
            .sum()
            .sort_values(ascending=False)
        )
        top_opportunity = kaizen_df.iloc[0]
        rca_col_1, rca_col_2, rca_col_3 = st.columns(3)
        with rca_col_1:
            st.metric("Top Recurring Downtime Reason", str(top_reason.index[0]))
        with rca_col_2:
            st.metric("Top Affected Line", str(top_opportunity["affected_line"]))
        with rca_col_3:
            st.metric("Top Affected Machine", str(top_opportunity["affected_machine"]))

        priority_chart = kaizen_df.head(8).sort_values("priority_score")
        fig = px.bar(
            priority_chart,
            x="priority_score",
            y="opportunity",
            color="downtime_reason",
            orientation="h",
            labels={"priority_score": "Priority score", "opportunity": "Opportunity"},
            title="Prioritized RCA / Kaizen Opportunities",
            color_discrete_sequence=["#1F6F78", "#D84E35", "#F1B84B", "#6A8D73", "#7B5EA7"],
        )
        fig.update_layout(height=430, legend_title_text="Downtime reason")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            kaizen_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "avg_oee": st.column_config.NumberColumn("avg_oee", format="%.3f"),
                "avg_scrap_rate": st.column_config.NumberColumn("avg_scrap_rate", format="%.3f"),
                "priority_score": st.column_config.NumberColumn("priority_score", format="%.1f"),
            },
        )

with tabs[4]:
    export_col_1, export_col_2, export_col_3 = st.columns(3)
    with export_col_1:
        st.download_button(
            label="Download Power BI-ready CSV",
            data=csv_bytes(full_powerbi_df),
            file_name="powerbi_ready_oee_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with export_col_2:
        st.download_button(
            label="Download filtered cleaned OEE CSV",
            data=csv_bytes(filtered_powerbi_df),
            file_name="filtered_cleaned_oee_dataset.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with export_col_3:
        excel_bytes = create_excel_summary_report(
            filtered_oee_df,
            manual_steps_df,
            filtered_issues_df,
            kaizen_df,
        )
        st.download_button(
            label="Download filtered Excel report",
            data=excel_bytes,
            file_name="manufacturing_excellence_oee_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.subheader("Power BI-ready Dataset Preview")
    st.dataframe(
        full_powerbi_df.head(25),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader("Power BI Import Notes")
    st.markdown(
        """
        1. Open Power BI Desktop and choose **Get Data > Text/CSV**.
        2. Select `powerbi_ready_oee_dataset.csv`.
        3. Confirm `date` as Date, KPI fields as Decimal Number, and `date_key` as Text.
        4. Build visuals using `oee_percent`, `availability_percent`, `performance_percent`, `quality_percent`, `scrap_rate_percent`, and `downtime_rate_percent`.
        """
    )
