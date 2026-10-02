"""Margin sweep and optimization."""
import numpy as np
import pandas as pd
from newsvendor.model import simulate


def sweep_margins(
    demand: np.ndarray,
    mu: float,
    margins: list,
    c_under: float,
    c_over: float
) -> pd.DataFrame:
    """
    Sweep over a range of margins using the same demand (common random numbers).

    Args:
        demand: Array of daily demands (fixed across all margins).
        mu: Mean demand (used only for reference/validation).
        margins: List of margin values to sweep.
        c_under: Underage cost.
        c_over: Overage cost.

    Returns:
        DataFrame with one row per margin, columns: margin, total_loss,
        overstock_loss, stockout_loss, stockout_rate, max_streak.
    """
    results = []

    for margin in margins:
        inventory = mu + margin
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
