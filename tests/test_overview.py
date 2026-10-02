"""Tests for overview (historical vs forecast) plotting."""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from newsvendor.overview import simulated_overview, imported_overview


class TestSimulatedOverview:
    """Test simulated mode overview frame generation."""

    def test_shape_with_horizon(self):
        """Frame has days + horizon rows."""
        demand = np.array([10, 11, 12, 13, 14])
        overview = simulated_overview(demand, mu=12, horizon=3)

        assert len(overview) == 8  # 5 days + 3 horizon
        assert list(overview.columns) == ["x", "actual", "forecast", "is_future"]

    def test_actual_values_history_only(self):
        """Actual values exist only in history, NaN in forecast horizon."""
        demand = np.array([10, 11, 12])
        overview = simulated_overview(demand, mu=12, horizon=2)

        # First 3 rows: actual demand
        assert overview.loc[0, "actual"] == 10
        assert overview.loc[1, "actual"] == 11
        assert overview.loc[2, "actual"] == 12

        # Last 2 rows: NaN (future)
        assert pd.isna(overview.loc[3, "actual"])
        assert pd.isna(overview.loc[4, "actual"])

    def test_forecast_constant_mu(self):
        """Forecast is constant μ across all rows."""
        demand = np.array([10, 11, 12])
        overview = simulated_overview(demand, mu=15, horizon=2)

        for idx in range(len(overview)):
            assert overview.loc[idx, "forecast"] == 15

    def test_is_future_flag(self):
        """is_future flags last horizon rows."""
        demand = np.array([10, 11])
        overview = simulated_overview(demand, mu=12, horizon=2)

        assert overview.loc[0, "is_future"] == False
        assert overview.loc[1, "is_future"] == False
        assert overview.loc[2, "is_future"] == True
        assert overview.loc[3, "is_future"] == True

    def test_zero_horizon(self):
        """Horizon of 0 means no future rows (history only)."""
        demand = np.array([10, 11, 12])
        overview = simulated_overview(demand, mu=12, horizon=0)

        assert len(overview) == 3
        assert overview["is_future"].sum() == 0

    def test_x_is_day_number(self):
        """x column is day number (0-indexed)."""
        demand = np.array([10, 11, 12])
        overview = simulated_overview(demand, mu=12, horizon=1)

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
