"""Tests for CSV data loading and validation."""
import pytest
import pandas as pd
import io
from datetime import datetime, timedelta
from newsvendor.data import load_daily_csv, DataFormatError, template_csv


def make_csv_data(start_date_str="2026-01-01", num_rows=30, num_future=0):
    """Helper to generate valid CSV data."""
    csv_data = "date,actual,forecast\n"
    start_date = datetime.fromisoformat(start_date_str)

    for i in range(num_rows):
        date = start_date + timedelta(days=i)
        if i < num_rows - num_future:
            # History row
            csv_data += f"{date.strftime('%Y-%m-%d')},{10+i},{12+i}\n"
        else:
            # Future row
            csv_data += f"{date.strftime('%Y-%m-%d')},,{12+i}\n"

    return csv_data


class TestTemplateCsv:
    """Test template generation."""

    def test_template_is_string(self):
        """Template returns a string."""
        result = template_csv()
        assert isinstance(result, str)

    def test_template_has_header(self):
        """Template has the correct header."""
        result = template_csv()
        assert "date,actual,forecast" in result


class TestLoadDailyCSV:
    """Test CSV loading and splitting."""

    def test_valid_file_with_history_and_future(self):
        """Valid file with history and future rows."""
        csv_data = make_csv_data(num_rows=33, num_future=3)
        buf = io.StringIO(csv_data)
        history, future = load_daily_csv(buf)

        assert len(history) == 30
        assert len(future) == 3

    def test_valid_file_history_only(self):
        """File with only history rows (no future)."""
        csv_data = make_csv_data(num_rows=30, num_future=0)
        buf = io.StringIO(csv_data)
        history, future = load_daily_csv(buf)

        assert len(history) == 30
        assert len(future) == 0

    def test_missing_date_column(self):
        """Missing date column raises error."""
        csv_data = """actual,forecast
10,12
11,13
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="Missing columns"):
            load_daily_csv(buf)

    def test_missing_actual_column(self):
        """Missing actual column raises error."""
        csv_data = """date,forecast
2026-01-01,12
2026-01-02,13
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="Missing columns"):
            load_daily_csv(buf)

    def test_missing_forecast_column(self):
        """Missing forecast column raises error."""
        csv_data = """date,actual
2026-01-01,10
2026-01-02,11
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="Missing columns"):
            load_daily_csv(buf)

    def test_extra_columns_ignored(self):
        """Extra columns are ignored without error."""
        csv_data = "date,actual,forecast,extra\n"
        start_date = datetime(2026, 1, 1)
        for i in range(30):
            date = start_date + timedelta(days=i)
            csv_data += f"{date.strftime('%Y-%m-%d')},10,12,foo\n"

        buf = io.StringIO(csv_data)
        history, future = load_daily_csv(buf)

        assert len(history) == 30
        assert "extra" not in history.columns

    def test_bad_date_format(self):
        """Non-ISO date format raises error."""
        csv_data = """date,actual,forecast
01/01/2026,10,12
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="date format"):
            load_daily_csv(buf)

    def test_unsorted_dates(self):
        """Unsorted dates raise error."""
        csv_data = """date,actual,forecast
2026-01-02,11,13
2026-01-01,10,12
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="sorted"):
            load_daily_csv(buf)

    def test_duplicate_dates(self):
        """Duplicate dates raise error."""
        csv_data = """date,actual,forecast
2026-01-01,10,12
2026-01-01,11,13
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="Duplicate"):
            load_daily_csv(buf)

    def test_date_gap(self):
        """Gap in dates raises error."""
        csv_data = """date,actual,forecast
2026-01-01,10,12
2026-01-03,12,14
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="missing"):
            load_daily_csv(buf)

    def test_blank_actual_mid_series(self):
        """Blank actual in the middle (between non-blank actuals) raises error."""
        csv_data = """date,actual,forecast
2026-01-01,10,12
2026-01-02,,13
2026-01-03,12,14
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="blank actual"):
            load_daily_csv(buf)

    def test_blank_forecast_anywhere(self):
        """Blank forecast raises error."""
        csv_data = """date,actual,forecast
2026-01-01,10,12
2026-01-02,11,
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="forecast"):
            load_daily_csv(buf)

    def test_negative_actual(self):
        """Negative actual raises error."""
        csv_data = """date,actual,forecast
2026-01-01,-10,12
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="non-negative"):
            load_daily_csv(buf)

    def test_negative_forecast(self):
        """Negative forecast raises error."""
        csv_data = """date,actual,forecast
2026-01-01,10,-12
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="non-negative"):
            load_daily_csv(buf)

    def test_non_numeric_actual(self):
        """Non-numeric actual raises error."""
        csv_data = """date,actual,forecast
2026-01-01,abc,12
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="numeric"):
            load_daily_csv(buf)

    def test_non_numeric_forecast(self):
        """Non-numeric forecast raises error."""
        csv_data = """date,actual,forecast
2026-01-01,10,xyz
"""
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="numeric"):
            load_daily_csv(buf)

    def test_fewer_than_30_history_rows(self):
        """Fewer than 30 history rows raises error."""
        csv_data = make_csv_data(num_rows=25, num_future=0)
        buf = io.StringIO(csv_data)
        with pytest.raises(DataFormatError, match="30.*history"):
            load_daily_csv(buf)

    def test_exactly_30_history_rows(self):
        """Exactly 30 history rows is allowed."""
        csv_data = make_csv_data(num_rows=30, num_future=0)
        buf = io.StringIO(csv_data)
        history, future = load_daily_csv(buf)

        assert len(history) == 30

    def test_more_than_30_history_rows(self):
        """More than 30 history rows is allowed."""
        csv_data = make_csv_data(num_rows=40, num_future=0)
        buf = io.StringIO(csv_data)
        history, future = load_daily_csv(buf)

        assert len(history) == 40

    def test_data_types(self):
        """Check that returned DataFrames have correct dtypes."""
        csv_data = "date,actual,forecast\n"
        start_date = datetime(2026, 1, 1)
        for i in range(30):
            date = start_date + timedelta(days=i)
            csv_data += f"{date.strftime('%Y-%m-%d')},{10+i},{12+i}.5\n"

        buf = io.StringIO(csv_data)
        history, future = load_daily_csv(buf)

        assert pd.api.types.is_datetime64_any_dtype(history["date"])
        assert pd.api.types.is_numeric_dtype(history["actual"])
        assert pd.api.types.is_numeric_dtype(history["forecast"])
