"""Generate overview (historical vs forecast) data and figures."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from .model import inventory_from_margin


def simulated_overview(demand: np.ndarray, forecast: np.ndarray, horizon: int) -> pd.DataFrame:
    """
    Generate overview frame for simulated mode.

    Args:
        demand: Array of historical demand values (simulated).
        forecast: Array of forecast values (expected demand, rounded). Length = days + horizon.
        horizon: Number of days to extend forecast beyond history.

    Returns:
        DataFrame with columns: x (day number), actual, forecast, is_future.
        - x: day number (0-indexed)
        - actual: simulated demand for history, NaN for forecast horizon
        - forecast: seasonal forecast across all rows
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
            "forecast": float(forecast[i]),
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


def add_stock(df: pd.DataFrame, margin: float, mode: str = "units") -> pd.DataFrame:
    """
    Add stock level, stockout flag, and waste to overview DataFrame.

    Args:
        df: DataFrame from simulated_overview or imported_overview.
        margin: Safety margin (units or percent).
        mode: "units" → stock = forecast + margin; "percent" → stock = forecast × (1 + margin/100).

    Returns:
        DataFrame with added columns: stock, stockout, waste.
        - stock: Inventory level (forecast + margin).
        - stockout: Boolean, True if actual > stock (only for history rows).
        - waste: Excess inventory where stock > actual (only for history rows, NaN for future).
    """
    df = df.copy()

    # Calculate stock level
    df["stock"] = inventory_from_margin(df["forecast"].values, margin, mode)

    # Stockout flag: actual > stock (only for history rows with actual values)
    df["stockout"] = (df["actual"] > df["stock"]) & (~df["actual"].isna())

    # Waste: stock - actual where stock > actual (zero otherwise)
    # Only for history rows; NaN for future
    waste = np.where(
        ~df["actual"].isna(),
        np.maximum(0, df["stock"] - df["actual"]),
        np.nan
    )
    df["waste"] = waste

    return df


def overview_figure(df: pd.DataFrame, x_title: str) -> go.Figure:
    """
    Build an overview figure showing historical vs forecast, stock level, and stockout/waste.

    Args:
        df: DataFrame from simulated_overview or imported_overview, with columns added by add_stock().
        x_title: Label for the x-axis ("Day" for simulated, "Date" for imported).

    Returns:
        Plotly figure with traces for actual (history), forecast, stock level, stockout markers,
        waste shading, divider, and forecast window.
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

    # Stock level trace (across history and future)
    if "stock" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["x"],
            y=df["stock"],
            mode="lines",
            name="Stock level (forecast + margin)",
            line=dict(color="green", width=2, dash="dot"),
            hovertemplate="<b>Stock</b><br>%{x}<br>%{y:.0f}<extra></extra>"
        ))

        # Waste fill (shaded area where stock > actual, history only)
        waste_mask = ~df["waste"].isna() & (df["waste"] > 0)
        if waste_mask.any():
            # Lower trace: min(actual, stock) for the fill area
            lower_y = np.minimum(df["actual"], df["stock"])
            fig.add_trace(go.Scatter(
                x=df.loc[waste_mask, "x"],
                y=df.loc[waste_mask, "stock"],
                mode="lines",
                name="Waste (excess inventory)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=True,
                hovertemplate="<b>Waste</b><br>%{x}<br>%{y:.0f}<extra></extra>"
            ))

            # Add invisible lower trace for fill
            fig.add_trace(go.Scatter(
                x=df.loc[waste_mask, "x"],
                y=df.loc[waste_mask, "actual"],
                mode="lines",
                name="Waste (excess inventory)",
                line=dict(color="rgba(0,0,0,0)"),
                showlegend=False,
                fill="tonexty",
                fillcolor="rgba(0,200,0,0.2)",
                hoverinfo="skip"
            ))

        # Stockout markers (red dots on days with actual > stock)
        stockout_mask = df["stockout"] == True
        if stockout_mask.any():
            fig.add_trace(go.Scatter(
                x=df.loc[stockout_mask, "x"],
                y=df.loc[stockout_mask, "actual"],
                mode="markers",
                name="Stockout days",
                marker=dict(size=10, color="red", symbol="x"),
                hovertemplate="<b>Stockout</b><br>%{x}<br>%{y:.0f}<extra></extra>"
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
        title="Historical vs Forecast (with Stock Level)",
        xaxis_title=x_title,
        yaxis_title="Units",
        hovermode="x unified",
        height=400,
        template="plotly_white"
    )

    return fig
