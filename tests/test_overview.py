"""Tests for overview (historical vs forecast) plotting."""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from newsvendor.overview import simulated_overview, imported_overview, add_stock
from newsvendor.model import expected_demand, simulate


class TestSimulatedOverview:
    """Test simulated mode overview frame generation."""

    def test_shape_with_horizon(self):
        """Frame has days + horizon rows."""
        demand = np.array([10, 11, 12, 13, 14])
        forecast = expected_demand(mu=12, seasonality=0, n=5+3, period=7)
        overview = simulated_overview(demand, forecast=forecast, horizon=3)

        assert len(overview) == 8  # 5 days + 3 horizon
        assert list(overview.columns) == ["x", "actual", "forecast", "is_future"]

    def test_actual_values_history_only(self):
        """Actual values exist only in history, NaN in forecast horizon."""
        demand = np.array([10, 11, 12])
        forecast = expected_demand(mu=12, seasonality=0, n=3+2, period=7)
        overview = simulated_overview(demand, forecast=forecast, horizon=2)

        # First 3 rows: actual demand
        assert overview.loc[0, "actual"] == 10
        assert overview.loc[1, "actual"] == 11
        assert overview.loc[2, "actual"] == 12

        # Last 2 rows: NaN (future)
        assert pd.isna(overview.loc[3, "actual"])
        assert pd.isna(overview.loc[4, "actual"])

    def test_forecast_matches_input(self):
        """Forecast column equals the input forecast array."""
        demand = np.array([10, 11, 12])
        forecast = expected_demand(mu=15, seasonality=0.1, n=5, period=7)
        overview = simulated_overview(demand, forecast=forecast, horizon=2)

        for idx in range(len(overview)):
            assert overview.loc[idx, "forecast"] == forecast[idx]

    def test_is_future_flag(self):
        """is_future flags last horizon rows."""
        demand = np.array([10, 11])
        forecast = expected_demand(mu=12, seasonality=0, n=4, period=7)
        overview = simulated_overview(demand, forecast=forecast, horizon=2)

        assert overview.loc[0, "is_future"] == False
        assert overview.loc[1, "is_future"] == False
        assert overview.loc[2, "is_future"] == True
        assert overview.loc[3, "is_future"] == True

    def test_zero_horizon(self):
        """Horizon of 0 means no future rows (history only)."""
        demand = np.array([10, 11, 12])
        forecast = expected_demand(mu=12, seasonality=0, n=3, period=7)
        overview = simulated_overview(demand, forecast=forecast, horizon=0)

        assert len(overview) == 3
        assert overview["is_future"].sum() == 0

    def test_x_is_day_number(self):
        """x column is day number (0-indexed)."""
        demand = np.array([10, 11, 12])
        forecast = expected_demand(mu=12, seasonality=0, n=4, period=7)
        overview = simulated_overview(demand, forecast=forecast, horizon=1)

        assert list(overview["x"]) == [0, 1, 2, 3]


class TestImportedOverview:
    """Test imported (real data) mode overview frame generation."""

    def test_with_history_and_future(self):
        """Frame includes history and future rows."""
        history = pd.DataFrame({
            "date": [datetime(2026, 1, i) for i in range(1, 4)],
            "actual": [10, 11, 12],
            "forecast": [12, 13, 14]
        })
        future = pd.DataFrame({
            "date": [datetime(2026, 1, 4), datetime(2026, 1, 5)],
            "forecast": [15, 16]
        })

        overview = imported_overview(history, future)

        assert len(overview) == 5
        assert list(overview.columns) == ["x", "actual", "forecast", "is_future"]

    def test_actual_in_history_only(self):
        """Actual values present in history, NaN in future."""
        history = pd.DataFrame({
            "date": [datetime(2026, 1, 1), datetime(2026, 1, 2)],
            "actual": [10, 11],
            "forecast": [12, 13]
        })
        future = pd.DataFrame({
            "date": [datetime(2026, 1, 3)],
            "forecast": [14]
        })

        overview = imported_overview(history, future)

        assert overview.loc[0, "actual"] == 10
        assert overview.loc[1, "actual"] == 11
        assert pd.isna(overview.loc[2, "actual"])

    def test_forecast_across_history_and_future(self):
        """Forecast values present on every row (history and future)."""
        history = pd.DataFrame({
            "date": [datetime(2026, 1, 1)],
            "actual": [10],
            "forecast": [12]
        })
        future = pd.DataFrame({
            "date": [datetime(2026, 1, 2)],
            "forecast": [14]
        })

        overview = imported_overview(history, future)

        assert overview.loc[0, "forecast"] == 12
        assert overview.loc[1, "forecast"] == 14

    def test_is_future_flags(self):
        """is_future flags future rows only."""
        history = pd.DataFrame({
            "date": [datetime(2026, 1, 1), datetime(2026, 1, 2)],
            "actual": [10, 11],
            "forecast": [12, 13]
        })
        future = pd.DataFrame({
            "date": [datetime(2026, 1, 3)],
            "forecast": [14]
        })

        overview = imported_overview(history, future)

        assert overview.loc[0, "is_future"] == False
        assert overview.loc[1, "is_future"] == False
        assert overview.loc[2, "is_future"] == True

    def test_history_only_no_future(self):
        """Works with history-only data (no future rows)."""
        history = pd.DataFrame({
            "date": [datetime(2026, 1, 1), datetime(2026, 1, 2)],
            "actual": [10, 11],
            "forecast": [12, 13]
        })
        future = pd.DataFrame()  # Empty

        overview = imported_overview(history, future)

        assert len(overview) == 2
        assert overview["is_future"].sum() == 0
        assert not overview["actual"].isna().any()

    def test_x_is_date(self):
        """x column contains the dates (as objects/strings for plotting)."""
        dates = [datetime(2026, 1, 1), datetime(2026, 1, 2)]
        history = pd.DataFrame({
            "date": dates,
            "actual": [10, 11],
            "forecast": [12, 13]
        })
        future = pd.DataFrame()

        overview = imported_overview(history, future)

        # Dates should be preserved (as Timestamp or datetime objects)
        assert pd.api.types.is_datetime64_any_dtype(overview["x"])


class TestAddStock:
    """Test add_stock() function for adding inventory and loss calculations."""

    def test_columns_added(self):
        """add_stock adds stock, stockout, and waste columns."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 15, 8],
            "forecast": [12, 12, 12],
            "is_future": [False, False, False]
        })
        result = add_stock(df, margin=5, mode="units")

        assert "stock" in result.columns
        assert "stockout" in result.columns
        assert "waste" in result.columns

    def test_stock_units_mode(self):
        """Stock = forecast + margin (units mode)."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 15, 8],
            "forecast": [12, 14, 10],
            "is_future": [False, False, False]
        })
        result = add_stock(df, margin=5, mode="units")

        assert result.loc[0, "stock"] == 17  # 12 + 5
        assert result.loc[1, "stock"] == 19  # 14 + 5
        assert result.loc[2, "stock"] == 15  # 10 + 5

    def test_stock_percent_mode(self):
        """Stock = forecast × (1 + margin/100) (percent mode)."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 15, 8],
            "forecast": [100, 200, 50],
            "is_future": [False, False, False]
        })
        result = add_stock(df, margin=10, mode="percent")

        assert np.isclose(result.loc[0, "stock"], 110)  # 100 * 1.1
        assert np.isclose(result.loc[1, "stock"], 220)  # 200 * 1.1
        assert np.isclose(result.loc[2, "stock"], 55)   # 50 * 1.1

    def test_stockout_flag_margin_zero(self):
        """At margin=0 (stock=forecast), stockout iff actual > forecast."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 13, 8],
            "forecast": [12, 12, 12],
            "is_future": [False, False, False]
        })
        result = add_stock(df, margin=0, mode="units")

        assert result.loc[0, "stockout"] == False  # 10 < 12, no stockout
        assert result.loc[1, "stockout"] == True   # 13 > 12, stockout
        assert result.loc[2, "stockout"] == False  # 8 < 12, no stockout

    def test_stockout_flag_with_margin(self):
        """With margin > 0, stockout iff actual > stock."""
        df = pd.DataFrame({
            "x": [0, 1, 2, 3],
            "actual": [10, 15, 17, 8],
            "forecast": [12, 14, 16, 10],
            "is_future": [False, False, False, False]
        })
        result = add_stock(df, margin=5, mode="units")
        # stock = [17, 19, 21, 15]

        assert result.loc[0, "stockout"] == False  # 10 < 17, no stockout
        assert result.loc[1, "stockout"] == False  # 15 < 19, no stockout
        assert result.loc[2, "stockout"] == False  # 17 < 21, no stockout
        assert result.loc[3, "stockout"] == False  # 8 < 15, no stockout

    def test_waste_calculation(self):
        """Waste = max(0, stock - actual) for history rows."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 15, 8],
            "forecast": [12, 14, 10],
            "is_future": [False, False, False]
        })
        result = add_stock(df, margin=5, mode="units")
        # stock = [17, 19, 15]

        assert result.loc[0, "waste"] == 7   # 17 - 10
        assert result.loc[1, "waste"] == 4   # 19 - 15
        assert result.loc[2, "waste"] == 7   # 15 - 8

    def test_waste_nan_for_future(self):
        """Waste is NaN for future rows (where actual is NaN)."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 15, np.nan],
            "forecast": [12, 14, 10],
            "is_future": [False, False, True]
        })
        result = add_stock(df, margin=5, mode="units")

        assert result.loc[0, "waste"] == 7
        assert result.loc[1, "waste"] == 4
        assert pd.isna(result.loc[2, "waste"])

    def test_stockout_flag_false_for_future(self):
        """Stockout is False for future rows (where actual is NaN)."""
        df = pd.DataFrame({
            "x": [0, 1, 2],
            "actual": [10, 15, np.nan],
            "forecast": [12, 14, 10],
            "is_future": [False, False, True]
        })
        result = add_stock(df, margin=5, mode="units")

        assert result.loc[0, "stockout"] == False
        assert result.loc[1, "stockout"] == False
        assert result.loc[2, "stockout"] == False

    def test_agreement_with_simulate(self):
        """add_stock calculations agree with simulate() for same demand/inventory."""
        # Create a simple scenario
        demand = np.array([10, 15, 8, 12])
        forecast = expected_demand(mu=12, seasonality=0, n=4, period=7)
        margin = 5

        # Using simulate()
        inventory = forecast + margin
        sim_result = simulate(demand, inventory, c_under=1.0, c_over=0.5)

        # Using add_stock()
        df = pd.DataFrame({
            "x": list(range(4)),
            "actual": demand,
            "forecast": forecast,
            "is_future": [False] * 4
        })
        overview_result = add_stock(df, margin=margin, mode="units")

        # Stockout days should match
        sim_stockouts = set(sim_result[sim_result["stockout"]].index)
        overview_stockouts = set(overview_result[overview_result["stockout"]].index)
        assert sim_stockouts == overview_stockouts
