"""
Utility functions for week calculation in the Line Homeroom Bot.
This module provides shared utilities used by both main.py and scheduler_service.py.
"""

from datetime import datetime, timedelta


def calculate_effective_weeks(start_date, target_date, skip_weeks):
    """
    Calculate the effective number of weeks between start_date and target_date,
    excluding date ranges specified in skip_weeks.
    
    Args:
        start_date: The cycle start date (date object)
        target_date: The target date to calculate weeks for (date object)
        skip_weeks: List of dicts with 'start' and 'end' dates to skip
    
    Returns:
        Number of effective weeks (int)
    """
    # Fast path when there are no skip periods configured
    if not skip_weeks:
        return (target_date - start_date).days // 7

    total_days = (target_date - start_date).days

    def _iter_effective_skip_periods():
        """
        Yield (effective_start, effective_end) date tuples for each valid
        skip period that overlaps [start_date, target_date].
        """
        for raw_period in skip_weeks:
            try:
                raw_start = raw_period["start"]
                raw_end = raw_period["end"]
                skip_start = datetime.strptime(raw_start, "%Y-%m-%d").date()
                skip_end = datetime.strptime(raw_end, "%Y-%m-%d").date()
            except (KeyError, ValueError, TypeError):
                # Skip invalid entries
                continue

            # Ignore logically invalid ranges
            if skip_end < skip_start:
                continue

            # Ignore periods that are completely outside our window
            if skip_end < start_date or skip_start > target_date:
                continue

            # Clamp the period to [start_date, target_date]
            effective_start = max(skip_start, start_date)
            effective_end = min(skip_end, target_date)
            yield effective_start, effective_end

    # Use a set to track unique skipped days (handles overlapping periods)
    skipped_days_set = set()
    for effective_start, effective_end in _iter_effective_skip_periods():
        # Add each day in this period to the set to avoid counting overlapping days twice
        current_day = effective_start
        while current_day <= effective_end:
            skipped_days_set.add(current_day)
            current_day += timedelta(days=1)
    
    effective_days = total_days - len(skipped_days_set)
    return max(0, effective_days) // 7
