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
    # School Days Logic (Base-5)
    # 1. Iterate through all days from start_date to target_date
    # 2. Count "potentially valid school days" (Mon-Fri)
    # 3. Subtract days that fall within skip periods
    # 4. Divide by 5 to get weeks
    
    current_day = start_date
    effective_school_days = 0
    
    # Pre-process skip periods into a set of skipped dates for O(1) lookup
    skipped_dates = set()
    if skip_weeks:
        for raw_period in skip_weeks:
            try:
                s_start = datetime.strptime(raw_period["start"], "%Y-%m-%d").date()
                s_end = datetime.strptime(raw_period["end"], "%Y-%m-%d").date()
                if s_end < s_start: continue
                
                # Expand range
                curr = s_start
                while curr <= s_end:
                    skipped_dates.add(curr)
                    curr += timedelta(days=1)
            except (KeyError, ValueError, TypeError):
                continue

    while current_day <= target_date:
        # Check if it's a school day (Mon=0, Fri=4)
        if current_day.weekday() < 5:
            # Check if it's NOT skipped
            if current_day not in skipped_dates:
                effective_school_days += 1
        
        current_day += timedelta(days=1)
        
    # Each "week" is 5 school days
    # We subtract 1 before dividing because the start day itself counts as day 1
    # Actually, simplest is pure division if we start counting from 0?
    # No, let's treat "0-4 days passed" as Week 1 (passed=0)
    # The original logic was (target - start).days // 7
    # 0 days diff = 0 weeks passed.
    
    # Correction: The calculation is usually "weeks *passed*".
    # On day 0 (start date): 0 effective days ? 
    # If using iteration `current_day <= target_date`, we count the target date too if it is valid.
    # The original logic `(target - start).days` measures generic time delta (exclusive of end? no, days diff).
    # 1 day diff means 1 day passed.
    # If start=Mon, target=Mon -> 7 days diff -> 1 week passed.
    # Here: Start=Mon, target=Next Mon. 
    # Mon-Fri (5 days) + Next Mon (1 day) = 6 days?
    # Logic: effective_school_days count includes start and target if they are valid.
    # We want "Difference in school days". 
    # So we should iterate `current_day < target_date` (exclusive of target).
    
    # Let's adjust loop to be `< target_date` to match `(target-start).days` semantics.
    
    current_day = start_date
    effective_school_days = 0
    
    while current_day < target_date:
        if current_day.weekday() < 5 and current_day not in skipped_dates:
            effective_school_days += 1
        current_day += timedelta(days=1)

    return max(0, effective_school_days) // 5
