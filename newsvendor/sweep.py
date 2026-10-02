"""Margin sweep and optimization."""
import numpy as np
import pandas as pd
from newsvendor.model import simulate, inventory_from_margin


def sweep_margins(
    demand: np.ndarray,
    mu,
    margins: list,
    c_under: float,
    c_over: float,
    mode: str = "units"
) -> pd.DataFrame:
    """
    Sweep over a range of margins using the same demand (common random numbers).

    Args:
        demand: Array of daily demands (fixed across all margins).
        mu: Baseline demand (scalar or per-day array).
           - Scalar: same forecast every day (simulated mode).
           - Array: per-day forecast (real data mode).
        margins: List of margin values to sweep.
        c_under: Underage cost.
        c_over: Overage cost.
        mode: "units" (inventory = mu + margin) or "percent" (inventory = mu × (1 + margin/100)).

    Returns:
        DataFrame with one row per margin, columns: margin, total_loss,
        overstock_loss, stockout_loss, stockout_rate, max_streak.
    """
    results = []

    for margin in margins:
        inventory = inventory_from_margin(mu, margin, mode=mode)
        sim_result = simulate(demand, inventory, c_under, c_over)

        total_loss = sim_result["total_loss"].sum()
        overstock_loss = sim_result["overstock_loss"].sum()
        stockout_loss = sim_result["stockout_loss"].sum()
        stockout_rate = (sim_result["stockout"].sum()) / len(demand)
        max_streak = sim_result["streak"].max()

        results.append({
            "margin": margin,
            "total_loss": total_loss,
            "overstock_loss": overstock_loss,
            "stockout_loss": stockout_loss,
            "stockout_rate": stockout_rate,
            "max_streak": max_streak
        })

    return pd.DataFrame(results)


def best_margin(sweep_df: pd.DataFrame) -> int:
    """
    Find the index of the margin with minimum total loss.

    Args:
        sweep_df: DataFrame from sweep_margins.

    Returns:
        Index (row number) of the best margin.
    """
    return sweep_df["total_loss"].idxmin()


def recommend(
    future_df: pd.DataFrame,
    baseline_col: str,
    margin: float,
    mode: str = "units"
) -> pd.DataFrame:
    """
    Generate recommended inventory for future days given a margin.

    Args:
        future_df: DataFrame with columns: date, forecast (and optionally others).
        baseline_col: Name of the baseline column (usually 'forecast').
        margin: Margin to apply.
        mode: "units" or "percent".

    Returns:
        DataFrame with columns: date, forecast, recommended_stock (integer, rounded up).
    """
    result = future_df[["date", baseline_col]].copy()
    result.columns = ["date", "forecast"]

    result["recommended_stock"] = np.ceil(
        inventory_from_margin(result["forecast"].values, margin, mode=mode)
    ).astype(int)

    return result
