from __future__ import annotations

from datetime import timedelta

import pandas as pd


def date_range_for_frames(frames: list[pd.DataFrame]) -> dict[str, str]:
    dates = []
    for df in frames:
        if df is None or df.empty or "date" not in df.columns:
            continue
        parsed = pd.to_datetime(df["date"], errors="coerce").dropna()
        if not parsed.empty:
            dates.append(parsed)
    if not dates:
        return {}
    merged = pd.concat(dates)
    return {
        "start": merged.min().strftime("%Y-%m-%d"),
        "end": merged.max().strftime("%Y-%m-%d"),
    }


def infer_periods(frames: list[pd.DataFrame], days: int = 7) -> tuple[dict[str, str], dict[str, str], bool]:
    """Use the latest *days* as current period and the same length before it as comparison."""
    full = date_range_for_frames(frames)
    if not full:
        return {}, {}, False
    end = pd.to_datetime(full["end"])
    start = max(pd.to_datetime(full["start"]), end - timedelta(days=max(1, days) - 1))
    length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=length - 1)
    comparison = {
        "start": previous_start.strftime("%Y-%m-%d"),
        "end": previous_end.strftime("%Y-%m-%d"),
    }
    current = {"start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d")}
    available_start = pd.to_datetime(full["start"])
    has_comparison = previous_start >= available_start
    return current, comparison, has_comparison


def pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous is None or float(previous) == 0:
        return None
    return (float(current) - float(previous)) / abs(float(previous))


def period_label(period: dict[str, str]) -> str:
    if not period:
        return ""
    return f"{period.get('start', '')} 至 {period.get('end', '')}"

