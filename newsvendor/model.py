"""Core simulation logic for the newsvendor problem."""
import numpy as np
import pandas as pd


def simulate_demand(mu: float, sigma: float, days: int, seed: int) -> np.ndarray:
    """
    Generate daily demand from a normal distribution.

    Args:
        mu: Mean demand.
        sigma: Standard deviation.
        days: Number of days to simulate.
        seed: Random seed for reproducibility.

    Returns:
        Array of demand values (non-negative integers).
    """
    rng = np.random.RandomState(seed)
    demand = rng.normal(mu, sigma, days)
    demand = np.maximum(demand, 0)  # Clip at 0
    return demand.astype(int)


def simulate(
    demand: np.ndarray,
    inventory: float,
    c_under: float,
    c_over: float
) -> pd.DataFrame:
    """
    Simulate a newsvendor problem over multiple days.

    Args:
        demand: Array of daily demands.
        inventory: Daily inventory level (constant for this run).
        c_under: Underage cost (per unit short, multiplied by streak day).
        c_over: Overage cost (per unit left over).

    Returns:
        DataFrame with columns: demand, inventory, shortfall, excess, streak,
        stockout, overstock_loss, stockout_loss, total_loss.
    """
    days = len(demand)
    results = []
    streak = 0

    for day in range(days):
        d = demand[day]
        inv = inventory

        # Shortfall and excess
        shortfall = max(0, d - inv)
        excess = max(0, inv - d)

        # Stockout flag
        is_stockout = shortfall > 0

        # Update streak
        if is_stockout:
            streak += 1
        else:
            streak = 0

        # Losses
        stockout_loss = streak * shortfall * c_under
        overstock_loss = excess * c_over
        total_loss = stockout_loss + overstock_loss

        results.append({
            "demand": d,
            "inventory": inv,
            "shortfall": shortfall,
            "excess": excess,
            "streak": streak,
            "stockout": is_stockout,
            "overstock_loss": overstock_loss,
            "stockout_loss": stockout_loss,
            "total_loss": total_loss
        })

    return pd.DataFrame(results)
