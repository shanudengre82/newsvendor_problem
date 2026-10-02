"""Generate overview (historical vs forecast) data and figures."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta


def simulated_overview(demand: np.ndarray, mu: float, horizon: int) -> pd.DataFrame:
    """
    Generate overview frame for simulated mode.

    Args:
        demand: Array of historical demand values (simulated).
        mu: Mean demand (the baseline forecast).
        horizon: Number of days to extend forecast beyond history.

    Returns:
        DataFrame with columns: x (day number), actual, forecast, is_future.
        - x: day number (0-indexed)
        - actual: simulated demand for history, NaN for forecast horizon
        - forecast: constant μ across all rows
        - is_future: True for the last `horizon` rows
    """
    days = len(demand)
    total_rows = days + horizon

    rows = []
    for i in range(total_rows):
        is_future = i >= days
        actual = float(demand[i]) if i < days else np.nan

        rows.append({
            "x": i,
            "actual": actual,
            "forecast": float(mu),
            "is_future": is_future
        })

    return pd.DataFrame(rows)


def imported_overview(history: pd.DataFrame, future: pd.DataFrame) -> pd.DataFrame:
    """
    Generate overview frame for imported CSV data.

    Args:
        history: DataFrame with columns: date, actual, forecast.
        future: DataFrame with columns: date, forecast (actual is blank/absent).

    Returns:
        DataFrame with columns: x (date), actual, forecast, is_future.
        - x: date (timestamp)
        - actual: values from history, NaN for future rows
        - forecast: values across both history and future
        - is_future: True for future rows
    """
    rows = []

    # History rows
    for idx, row in history.iterrows():
        rows.append({
            "x": row["date"],
            "actual": row["actual"],
            "forecast": row["forecast"],
            "is_future": False
        })

    # Future rows
    for idx, row in future.iterrows():
        rows.append({
            "x": row["date"],
            "actual": np.nan,
            "forecast": row["forecast"],
            "is_future": True
        })

    return pd.DataFrame(rows)


def overview_figure(df: pd.DataFrame, x_title: str) -> go.Figure:
    """
    Build an overview figure showing historical vs forecast.

    Args:
        df: DataFrame from simulated_overview or imported_overview.
        x_title: Label for the x-axis ("Day" for simulated, "Date" for imported).

    Returns:
        Plotly figure with traces for actual (history) and forecast, shaded forecast window,
        and divider (if future rows exist).
    """
    fig = go.Figure()

    # Actual trace (history only, NaN values are gaps)
    history_mask = ~df["actual"].isna()
    fig.add_trace(go.Scatter(
        x=df.loc[history_mask, "x"],
        y=df.loc[history_mask, "actual"],
        mode="lines+markers",
        name="Actual (history)",
        line=dict(color="steelblue", width=2),
        marker=dict(size=6),
        hovertemplate="<b>Actual</b><br>%{x}<br>%{y:.0f}<extra></extra>"
    ))

    # Forecast trace (across history and future)
    fig.add_trace(go.Scatter(
        x=df["x"],
        y=df["forecast"],
        mode="lines",
        name="Forecast",
        line=dict(color="darkorange", width=2, dash="dash"),
        hovertemplate="<b>Forecast</b><br>%{x}<br>%{y:.0f}<extra></extra>"
    ))

    # Add divider and shaded window if future rows exist
    if df["is_future"].any():
        first_future_idx = df[df["is_future"]].index[0]
        first_future_x = df.loc[first_future_idx, "x"]

        # Vertical divider at first future
        fig.add_vline(
            x=first_future_x,
            line_dash="dash",
            line_color="lightgray",
            line_width=1
        )

        # Shaded forecast window (from first future to end)
        last_x = df["x"].iloc[-1]
        fig.add_vrect(
            x0=first_future_x,
            x1=last_x,
            fillcolor="orange",
            opacity=0.1,
            layer="below",
            line_width=0,
            annotation_text="Forecast →",
            annotation_position="top right",
            annotation_font_size=12,
            annotation_font_color="darkorange"
        )

    fig.update_layout(
        title="Historical vs Forecast",
        xaxis_title=x_title,
        yaxis_title="Units",
        hovermode="x unified",
        height=350,
        template="plotly_white"
    )

    return fig
