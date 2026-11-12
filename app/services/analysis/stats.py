"""Percentile ranks and quartiles, done the way Daniel can check them in Excel."""

from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from math import floor


def quantile_inc(values: Sequence[float], q: float) -> float | None:
    """Excel's QUARTILE.INC / PERCENTILE.INC (numpy's default, d3.quantile): linear
    interpolation between the closest ranks. ``values`` must be sorted."""
    if not values:
        return None
    position = (len(values) - 1) * q
    low = floor(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (position - low) * (values[high] - values[low])


def mid_rank(value: float, others: Sequence[float], *, include_self: bool) -> tuple[float, int]:
    """P = (number below + ½ × number equal) / n × 100, and n (BRIEF §8.3, phase-2 brief §4.2).

    ``others`` is the comparison set's values, sorted. When the release itself is not among them
    (a provisional release, ranked as if it were), it is added: one more equal, one more in n.
    """
    below = bisect_left(others, value)
    equal = bisect_right(others, value) - below
    n = len(others)
    if include_self:
        equal += 1
        n += 1
    if n == 0:
        return 0.0, 0
    return (below + equal / 2) / n * 100, n


def whole(value: float) -> int:
    """Round half up, as people (and Excel's ROUND) do, not to even as Python's round does."""
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
