from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from backend.app.services.charts.distribution_generators import (
    generate_cpu_hours_by_account,
    generate_cpus_per_job,
    generate_gpu_hours_by_account,
    generate_gpus_per_job,
    generate_job_duration_hist,
    generate_job_duration_stacked,
    generate_job_duration_trends,
    generate_jobs_by_account,
    generate_jobs_by_partition,
    generate_jobs_by_state,
    generate_nodes_per_job,
    generate_waiting_times_hist,
    generate_waiting_times_stacked,
    generate_waiting_times_trends,
)
from backend.app.services.charts.timeline_generators import (
    generate_active_users_over_time,
    generate_cpu_usage_over_time,
    generate_gpu_usage_over_time,
    generate_job_duration_over_time,
    generate_jobs_over_time,
    generate_waiting_times_over_time,
)


@pytest.fixture
def sample_dataframe():
    """Create a sample dataframe for testing plot generation."""
    np.random.seed(42)
    n_rows = 1000

    start_dates = pd.date_range(
        start=datetime.now() - timedelta(days=30),
        end=datetime.now(),
        periods=n_rows
    )

    submit_dates = start_dates - pd.to_timedelta(np.random.exponential(1, n_rows), unit='h')

    df = pd.DataFrame({
        'JobID': range(1, n_rows + 1),
        'State': np.random.choice(['COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT'], n_rows),
        'Partition': np.random.choice(['gpu', 'cpu', 'interactive'], n_rows, p=[0.3, 0.6, 0.1]),
        'Account': np.random.choice(['account1', 'account2', 'account3'], n_rows),
        'User': np.random.choice(['user1', 'user2', 'user3', 'user4'], n_rows),
        'QOS': np.random.choice(['normal', 'high', 'low'], n_rows),
        'CPUHours': np.random.exponential(10, n_rows),
        'GPUHours': np.random.exponential(5, n_rows),
        'ElapsedHours': np.random.exponential(3, n_rows),
        'WaitingTimeHours': np.random.exponential(1, n_rows),
        'AllocNodes': np.random.choice([1, 2, 3, 4], n_rows, p=[0.7, 0.2, 0.08, 0.02]),
        'AllocCPUS': np.random.choice([1, 2, 4, 8, 16], n_rows),
        'AllocGPUS': np.random.choice([0, 1, 2, 4], n_rows, p=[0.6, 0.3, 0.08, 0.02]),
        'Start': start_dates,
        'Submit': submit_dates,
        'End': start_dates + pd.to_timedelta(np.random.exponential(3, n_rows), unit='h'),
        # Start-based time columns (for CPU/GPU usage)
        'StartYearMonth': start_dates.to_period('M').astype(str),
        'StartYearWeek': start_dates,  # Timeline generator expects datetime, will normalize to week start
        'StartDay': start_dates.date.astype(str),
        # Submit-based time columns (for jobs, users, waiting times, duration)
        'SubmitYearMonth': pd.to_datetime(submit_dates).to_period('M').astype(str),
        'SubmitYearWeek': pd.to_datetime(submit_dates),
        'SubmitDay': pd.to_datetime(submit_dates).date.astype(str),
    })

    return df


def validate_chart_output(result, min_points=1, chart_type='bar'):
    """Validate that chart output has correct structure.

    Args:
        result: Chart data dictionary
        min_points: Minimum number of data points expected
        chart_type: 'bar' for x/y format, 'pie' for labels/values format, 'stacked' for x/series format, 'trends' for x/stats format
    """
    assert result is not None, "Chart result should not be None"
    assert isinstance(result, dict), "Chart result should be a dictionary"

    if chart_type == 'pie':
        # Pie charts use labels/values
        assert 'labels' in result, "Pie chart result should have 'labels' key"
        assert 'values' in result, "Pie chart result should have 'values' key"
        assert isinstance(result['labels'], list), "labels should be a list"
        assert isinstance(result['values'], list), "values should be a list"
        assert len(result['labels']) >= min_points, f"Chart should have at least {min_points} data point(s)"
        assert len(result['labels']) == len(result['values']), "labels and values should have same length"
    elif chart_type == 'stacked':
        # Stacked charts use x/series
        assert 'x' in result, "Stacked chart result should have 'x' key"
        assert 'series' in result, "Stacked chart result should have 'series' key"
        assert isinstance(result['x'], list), "x values should be a list"
        assert isinstance(result['series'], list), "series should be a list"
        assert len(result['x']) >= min_points, f"Chart should have at least {min_points} data point(s)"
        for series in result['series']:
            assert isinstance(series, dict), "Each series should be a dictionary"
            assert 'name' in series, "Each series should have a 'name' key"
            assert 'data' in series, "Each series should have a 'data' key"
            assert len(series['data']) == len(result['x']), "Series data should match x length"
    elif chart_type == 'trends':
        # Trends charts use x/stats
        assert 'x' in result, "Trends chart result should have 'x' key"
        assert 'stats' in result, "Trends chart result should have 'stats' key"
        assert isinstance(result['x'], list), "x values should be a list"
        assert isinstance(result['stats'], dict), "stats should be a dictionary"
        assert len(result['x']) >= min_points, f"Chart should have at least {min_points} data point(s)"
        for stat_name, stat_values in result['stats'].items():
            assert isinstance(stat_values, list), f"stat '{stat_name}' should be a list"
            assert len(stat_values) == len(result['x']), f"stat '{stat_name}' should match x length"
    else:
        # Bar/line charts use x/y
        assert 'x' in result, "Chart result should have 'x' key"
        assert 'y' in result, "Chart result should have 'y' key"
        assert isinstance(result['x'], list), "x values should be a list"
        assert isinstance(result['y'], list), "y values should be a list"
        assert len(result['x']) >= min_points, f"Chart should have at least {min_points} data point(s)"
        assert len(result['x']) == len(result['y']), "x and y should have same length"
    return True


class TestDistributionPlots:
    """Test all distribution plot generation functions."""

    def test_generate_jobs_by_state(self, sample_dataframe):
        result = generate_jobs_by_state(sample_dataframe)
        assert validate_chart_output(result, chart_type='pie')
        assert all(isinstance(label, str) for label in result['labels']), "State labels should be strings"
        assert all(isinstance(val, (int, float)) for val in result['values']), "Values should be numeric"

    def test_generate_jobs_by_partition(self, sample_dataframe):
        result = generate_jobs_by_partition(sample_dataframe)
        assert validate_chart_output(result)
        assert all(isinstance(x, str) for x in result['x']), "Partition labels should be strings"

    def test_generate_jobs_by_account(self, sample_dataframe):
        result = generate_jobs_by_account(sample_dataframe)
        assert validate_chart_output(result)
        assert all(isinstance(x, str) for x in result['x']), "Account labels should be strings"

    def test_generate_waiting_times_hist(self, sample_dataframe):
        result = generate_waiting_times_hist(sample_dataframe)
        assert validate_chart_output(result, min_points=1)

    def test_generate_job_duration_hist(self, sample_dataframe):
        result = generate_job_duration_hist(sample_dataframe)
        assert validate_chart_output(result, min_points=1)

    def test_generate_nodes_per_job(self, sample_dataframe):
        result = generate_nodes_per_job(sample_dataframe)
        assert validate_chart_output(result)
        assert all(isinstance(x, (int, str)) for x in result['x']), "Node counts should be numeric or string"

    def test_generate_cpus_per_job(self, sample_dataframe):
        result = generate_cpus_per_job(sample_dataframe)
        assert validate_chart_output(result)

    def test_generate_gpus_per_job(self, sample_dataframe):
        result = generate_gpus_per_job(sample_dataframe)
        assert validate_chart_output(result)

    def test_generate_cpu_hours_by_account(self, sample_dataframe):
        result = generate_cpu_hours_by_account(sample_dataframe)
        assert validate_chart_output(result)
        assert all(isinstance(x, str) for x in result['x']), "Account labels should be strings"

    def test_generate_gpu_hours_by_account(self, sample_dataframe):
        result = generate_gpu_hours_by_account(sample_dataframe)
        assert validate_chart_output(result)

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_waiting_times_stacked(self, sample_dataframe, period_type):
        result = generate_waiting_times_stacked(sample_dataframe, period_type)
        assert validate_chart_output(result, min_points=1, chart_type='stacked')

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_job_duration_stacked(self, sample_dataframe, period_type):
        result = generate_job_duration_stacked(sample_dataframe, period_type)
        assert validate_chart_output(result, min_points=1, chart_type='stacked')

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_waiting_times_trends(self, sample_dataframe, period_type):
        result = generate_waiting_times_trends(sample_dataframe, period_type)
        assert validate_chart_output(result, min_points=1, chart_type='trends')

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_job_duration_trends(self, sample_dataframe, period_type):
        result = generate_job_duration_trends(sample_dataframe, period_type)
        assert validate_chart_output(result, min_points=1, chart_type='trends')


class TestTimelinePlots:
    """Test all timeline plot generation functions."""

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_cpu_usage_over_time(self, sample_dataframe, period_type):
        result = generate_cpu_usage_over_time(sample_dataframe, period_type)
        assert validate_chart_output(result)
        assert all(isinstance(y, (int, float)) for y in result['y']), "Values should be numeric"

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_gpu_usage_over_time(self, sample_dataframe, period_type):
        result = generate_gpu_usage_over_time(sample_dataframe, period_type)
        assert validate_chart_output(result)
        assert all(isinstance(y, (int, float)) for y in result['y']), "Values should be numeric"

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_active_users_over_time(self, sample_dataframe, period_type):
        result = generate_active_users_over_time(sample_dataframe, period_type)
        assert validate_chart_output(result)
        assert all(isinstance(y, (int, float)) for y in result['y']), "Values should be numeric"

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_jobs_over_time(self, sample_dataframe, period_type):
        result = generate_jobs_over_time(sample_dataframe, period_type)
        assert validate_chart_output(result)
        assert all(isinstance(y, (int, float)) for y in result['y']), "Values should be numeric"

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_waiting_times_over_time(self, sample_dataframe, period_type):
        result = generate_waiting_times_over_time(sample_dataframe, period_type)
        assert validate_chart_output(result)
        assert all(isinstance(y, (int, float)) for y in result['y']), "Values should be numeric"

    @pytest.mark.parametrize("period_type", ["day", "week", "month"])
    def test_generate_job_duration_over_time(self, sample_dataframe, period_type):
        result = generate_job_duration_over_time(sample_dataframe, period_type)
        assert validate_chart_output(result)
        assert all(isinstance(y, (int, float)) for y in result['y']), "Values should be numeric"


class TestEmptyDataFrame:
    """Test plot generation with empty dataframes."""

    def test_empty_dataframe_jobs_by_state(self):
        empty_df = pd.DataFrame(columns=['State'])
        result = generate_jobs_by_state(empty_df)
        assert result is not None

    def test_empty_dataframe_cpu_usage_over_time(self):
        empty_df = pd.DataFrame(columns=['Start', 'CPUHours'])
        result = generate_cpu_usage_over_time(empty_df, 'day')
        assert result is not None


class TestDataQuality:
    """Test plot generation handles data quality issues."""

    def test_null_values_in_waiting_times(self, sample_dataframe):
        df = sample_dataframe.copy()
        df.loc[:10, 'WaitingTime'] = np.nan
        result = generate_waiting_times_hist(df)
        assert validate_chart_output(result, min_points=1)

    def test_null_values_in_nodes(self, sample_dataframe):
        df = sample_dataframe.copy()
        df.loc[:10, 'AllocNodes'] = np.nan
        result = generate_nodes_per_job(df)
        assert validate_chart_output(result, min_points=1)

    def test_negative_cpu_hours(self, sample_dataframe):
        df = sample_dataframe.copy()
        df.loc[:10, 'CPUHours'] = -1
        result = generate_cpu_hours_by_account(df)
        assert validate_chart_output(result, min_points=1)
