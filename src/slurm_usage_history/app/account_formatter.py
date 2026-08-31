# account_formatter.py
from functools import lru_cache


class AccountFormatter:
    """Configurable formatter for cluster account names."""

    def __init__(self, max_segments=3, separator="-"):
        self.max_segments = max_segments
        self.separator = separator
        self.enabled = True

    def format_account(self, account):
        """Format account name by keeping first N segments."""
        if not self.enabled or not isinstance(account, str):
            return account

        # Clear cache if needed
        self._format_account_cached.cache_clear()

        return self._format_account_cached(account)

    @lru_cache(maxsize=1000)  # noqa: B019  (cache on a long-lived singleton is intended)
    def _format_account_cached(self, account):
        """Cached implementation of account formatting."""
        if self.max_segments == 0:  # Keep full account name
            return account

        segments = account.split(self.separator)
        return self.separator.join(segments[: self.max_segments])


formatter = AccountFormatter(max_segments=3)
