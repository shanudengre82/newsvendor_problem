"""Core simulation logic for the newsvendor problem."""
import numpy as np
import pandas as pd


def expected_demand(mu: float, seasonality: float, n: int, period: int = 7) -> np.ndarray:
    """
    Generate seasonal expected demand using a sinusoidal curve.

    Args:
        mu: Base mean demand.
        seasonality: Amplitude as a fraction of mu (0 = flat, 0.2 = ±20% variation).
        n: Number of periods to generate.
        period: Cycle length in days (default 7 for weekly).

    Returns:
        Array of expected demand values with seasonal pattern.
    """
    t = np.arange(n)
    expected = mu * (1 + seasonality * np.sin(2 * np.pi * t / period))
    return expected


def inventory_from_margin(baseline, margin: float, mode: str = "units"):
    """
    Calculate inventory from baseline and margin.

    Args:
        baseline: Scalar or array of baseline (mean/forecast) values.
        margin: Safety margin (units or fraction depending on mode).
        mode: "units" → inventory = baseline + margin
              "percent" → inventory = baseline × (1 + margin/100)

    Returns:
        Inventory as scalar or array (same shape as baseline).
    """
    if mode == "units":
        return baseline + margin
    elif mode == "percent":
        return baseline * (1 + margin / 100.0)
    else:
        raise ValueError(f"mode must be 'units' or 'percent', got {mode}")


def simulate_demand(mu, sigma: float, days: int, seed: int) -> np.ndarray:
    """
    Generate daily demand from a normal distribution.

    Args:
        mu: Mean demand. Can be:
            - Scalar (float): constant mean for all days.
            - Array: per-day expected mean (e.g., from expected_demand).
        sigma: Standard deviation (forecast error spread).
        days: Number of days to simulate.
        seed: Random seed for reproducibility.

    Returns:
        Array of demand values (non-negative integers, rounded with rint).
    """
    rng = np.random.RandomState(seed)

    # Broadcast mu to array if scalar
    if isinstance(mu, (int, float)):
        mu_array = np.full(days, mu)
    else:
        mu_array = np.asarray(mu)

    # Generate noise
    noise = rng.normal(0, sigma, days)

    # Demand = expected + noise, clipped and rounded
    demand = mu_array + noise
    demand = np.maximum(demand, 0)  # Clip at 0
    return np.rint(demand).astype(int)


def simulate(
    demand: np.ndarray,
    inventory,
    c_under: float,
    c_over: float
) -> pd.DataFrame:
    """
    Simulate a newsvendor problem over multiple days.

    Args:
        demand: Array of daily demands.
        inventory: Daily inventory level. Can be:
                   - Scalar (float): constant inventory for all days.
                   - Array: per-day inventory levels.
        c_under: Underage cost (per unit short, multiplied by streak day).
        c_over: Overage cost (per unit left over).

    Returns:
        DataFrame with columns: demand, inventory, shortfall, excess, streak,
        stockout, overstock_loss, stockout_loss, total_loss.
    """
    days = len(demand)

    # Broadcast inventory to array if scalar
    if isinstance(inventory, (int, float)):
        inventory = np.full(days, inventory)
    else:
        inventory = np.asarray(inventory)

    results = []
    streak = 0

    for day in range(days):
        d = demand[day]
        inv = float(inventory[day])

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
