import pytest
import numpy as np
import pandas as pd
from newsvendor.model import simulate_demand, simulate, inventory_from_margin


class TestSimulateDemand:
    """Test demand generation."""

    def test_shape(self):
        """Demand array has correct length."""
        demand = simulate_demand(mu=50, sigma=10, days=100, seed=42)
        assert len(demand) == 100

    def test_nonnegative(self):
        """Demand is clipped at 0."""
        # With low mu and high sigma, we can hit clipping.
        demand = simulate_demand(mu=5, sigma=20, days=1000, seed=42)
        assert np.all(demand >= 0)

    def test_integer(self):
        """Demand values are integers."""
        demand = simulate_demand(mu=50, sigma=10, days=100, seed=42)
        assert np.all(demand == demand.astype(int))

    def test_seed_reproducible(self):
        """Same seed gives same demand."""
        d1 = simulate_demand(mu=50, sigma=10, days=100, seed=123)
        d2 = simulate_demand(mu=50, sigma=10, days=100, seed=123)
        np.testing.assert_array_equal(d1, d2)


class TestSimulate:
    """Test single-margin simulation with streak logic."""

    def test_no_stockout(self):
        """No shortage when demand < inventory every day."""
        demand = np.array([5, 10, 8, 6])
        result = simulate(demand=demand, inventory=15, c_under=1.0, c_over=0.5)
        assert len(result) == 4
        assert np.all(result["shortfall"] == 0)
        assert np.all(result["stockout"] == False)
        assert np.all(result["streak"] == 0)

    def test_stockout_loss_single_day(self):
        """Single day stockout: loss = 1 × shortfall × c_under."""
        demand = np.array([10])
        result = simulate(demand=demand, inventory=5, c_under=2.0, c_over=0.5)
        assert result.loc[0, "shortfall"] == 5
        assert result.loc[0, "stockout_loss"] == 1 * 5 * 2.0

    def test_consecutive_stockout_multiplier(self):
        """Consecutive stockouts: loss multiplied by streak day n."""
        demand = np.array([10, 12, 15, 5])  # Days with inventory=8
        result = simulate(demand=demand, inventory=8, c_under=1.0, c_over=0.5)
        # Day 0: demand 10, inventory 8 → shortfall 2, streak 1, loss = 1*2
        assert result.loc[0, "shortfall"] == 2
        assert result.loc[0, "streak"] == 1
        assert result.loc[0, "stockout_loss"] == 1 * 2
        # Day 1: demand 12, inventory 8 → shortfall 4, streak 2, loss = 2*4
        assert result.loc[1, "shortfall"] == 4
        assert result.loc[1, "streak"] == 2
        assert result.loc[1, "stockout_loss"] == 2 * 4
        # Day 2: demand 15, inventory 8 → shortfall 7, streak 3, loss = 3*7
        assert result.loc[2, "shortfall"] == 7
        assert result.loc[2, "streak"] == 3
        assert result.loc[2, "stockout_loss"] == 3 * 7
        # Day 3: demand 5, inventory 8 → no shortage, streak resets to 0
        assert result.loc[3, "shortfall"] == 0
        assert result.loc[3, "streak"] == 0
        assert result.loc[3, "stockout_loss"] == 0

    def test_streak_resets_on_no_stockout(self):
        """Streak resets to 0 when demand <= inventory."""
        demand = np.array([10, 10, 3, 10, 10])
        result = simulate(demand=demand, inventory=5, c_under=1.0, c_over=0.5)
        # Day 0, 1: stockout (streak 1, 2)
        assert result.loc[0, "streak"] == 1
        assert result.loc[1, "streak"] == 2
        # Day 2: no stockout (streak resets)
        assert result.loc[2, "streak"] == 0
        # Day 3, 4: stockout again (streak 1, 2)
        assert result.loc[3, "streak"] == 1
        assert result.loc[4, "streak"] == 2

    def test_overstock_loss(self):
        """Overstock loss = (inventory - demand) × c_over."""
        demand = np.array([5, 10, 8])
        result = simulate(demand=demand, inventory=15, c_under=1.0, c_over=0.5)
        # Day 0: 15 - 5 = 10 excess, loss = 10 * 0.5
        assert result.loc[0, "excess"] == 10
        assert result.loc[0, "overstock_loss"] == 10 * 0.5
        # Day 1: 15 - 10 = 5 excess, loss = 5 * 0.5
        assert result.loc[1, "excess"] == 5
        assert result.loc[1, "overstock_loss"] == 5 * 0.5
        # Day 2: 15 - 8 = 7 excess, loss = 7 * 0.5
        assert result.loc[2, "excess"] == 7
        assert result.loc[2, "overstock_loss"] == 7 * 0.5

    def test_total_loss(self):
        """Total loss = stockout_loss + overstock_loss."""
        demand = np.array([10, 5, 12])
        result = simulate(demand=demand, inventory=8, c_under=1.0, c_over=0.5)
        for idx in range(3):
            expected = result.loc[idx, "stockout_loss"] + result.loc[idx, "overstock_loss"]
            assert result.loc[idx, "total_loss"] == expected

    def test_output_columns(self):
        """Result has all required columns."""
        demand = np.array([10, 5])
        result = simulate(demand=demand, inventory=8, c_under=1.0, c_over=0.5)
        required = ["demand", "inventory", "shortfall", "excess", "streak", "stockout",
                    "overstock_loss", "stockout_loss", "total_loss"]
        for col in required:
            assert col in result.columns

    def test_per_day_inventory_array(self):
        """Per-day inventory array works correctly."""
        demand = np.array([10, 10, 10])
        inventory = np.array([8, 9, 11])  # Varying inventory
        result = simulate(demand=demand, inventory=inventory, c_under=1.0, c_over=0.5)

        assert result.loc[0, "inventory"] == 8
        assert result.loc[1, "inventory"] == 9
        assert result.loc[2, "inventory"] == 11

        # Shortfall should vary with inventory
        assert result.loc[0, "shortfall"] == 2
        assert result.loc[1, "shortfall"] == 1
        assert result.loc[2, "shortfall"] == 0


class TestInventoryFromMargin:
    """Test margin to inventory conversion."""

    def test_units_mode_scalar(self):
        """Units mode with scalar baseline."""
        inv = inventory_from_margin(baseline=50, margin=10, mode="units")
        assert inv == 60

    def test_units_mode_array(self):
        """Units mode with array baseline."""
        baseline = np.array([50, 60, 70])
        inv = inventory_from_margin(baseline=baseline, margin=10, mode="units")
        np.testing.assert_array_equal(inv, np.array([60, 70, 80]))

    def test_percent_mode_scalar(self):
        """Percent mode with scalar baseline."""
        inv = inventory_from_margin(baseline=100, margin=10, mode="percent")
        assert np.isclose(inv, 110)  # 100 * (1 + 10/100)

    def test_percent_mode_array(self):
        """Percent mode with array baseline."""
        baseline = np.array([100, 200])
        inv = inventory_from_margin(baseline=baseline, margin=10, mode="percent")
        np.testing.assert_array_almost_equal(inv, np.array([110, 220]))

    def test_negative_margin_units(self):
        """Negative margin is allowed (reduces inventory)."""
        inv = inventory_from_margin(baseline=50, margin=-10, mode="units")
        assert inv == 40

    def test_negative_margin_percent(self):
        """Negative margin in percent mode."""
        inv = inventory_from_margin(baseline=100, margin=-20, mode="percent")
        assert inv == 80  # 100 * (1 - 20/100)
