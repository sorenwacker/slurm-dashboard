"""Helper functions for chart generation."""

import pandas as pd


def format_account_name(account: str, max_segments: int | None = None, separator: str = "-") -> str:
    """Format account name by keeping first N segments.

    Args:
        account: Account name to format (e.g., "ewi-insy-prb")
        max_segments: Number of segments to keep (None or 0 = keep all)
        separator: Separator character (default: "-")

    Returns:
        Formatted account name (e.g., "ewi-insy" with max_segments=2)

    Examples:
        >>> format_account_name("ewi-insy-prb", max_segments=2)
        'ewi-insy'
        >>> format_account_name("ewi-insy-prb", max_segments=1)
        'ewi'
        >>> format_account_name("ewi-insy-prb", max_segments=None)
        'ewi-insy-prb'
    """
    if not max_segments or max_segments == 0:
        return account

    if not isinstance(account, str):
        return account

    segments = account.split(separator)
    return separator.join(segments[:max_segments])


def format_accounts_in_df(df: pd.DataFrame, account_segments: int | None = None) -> pd.DataFrame:
    """Apply account formatting to the Account column in a DataFrame.

    Args:
        df: DataFrame with 'Account' column
        account_segments: Number of segments to keep in account names

    Returns:
        DataFrame with formatted account names
    """
    if account_segments and "Account" in df.columns and not df.empty:
        df = df.copy()
        df["Account"] = df["Account"].apply(lambda x: format_account_name(x, account_segments))

    return df
