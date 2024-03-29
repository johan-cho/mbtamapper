"""Helper functions for time conversions for gtfs loader"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytz
from dateutil.parser import isoparse, parse


def to_seconds(time: str) -> int:
    """Converts a string in HH:MM:SS format to seconds past midnight

    Args:
        time (str): A string in HH:MM:SS format
    Returns:
        int: The number of seconds past midnight"""

    hours, minutes, seconds = time.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def seconds_to_iso(date: datetime, seconds: int, zone: str = "America/New_York") -> str:
    """Converts a date and seconds to an iso string

    Args:
        date (datetime): The date of the service
        seconds (int): The seconds past midnight
        zone (str, optional): The timezone of the service. Defaults to "America/New_York".
    Returns:
        str: An iso string"""

    date_time = pytz.timezone(zone).localize(date + timedelta(seconds=seconds))
    return date_time.astimezone(pytz.utc).isoformat()


def format_time(time_str: str) -> str:
    """Formats Time, uses current date

    Args:
        time_str (str): Time in HH:MM:SS format
    Returns:
        str: Formatted time in HH:MM:SS AM/PM format"""

    hour, minute, second = time_str.split(":")  # pylint: disable=unused-variable

    int_hour = int(hour)

    if int_hour < 12:
        return f"{hour}:{minute} AM"
    if 12 <= int_hour < 24:
        return f"{return_format_hour(int_hour, 12)}:{minute} PM"
    if int_hour >= 24:
        return f"{return_format_hour(int_hour, 24)}:{minute} AM"
    return ""


def return_format_hour(hour: int, offset: int = 12) -> str:
    """Returns formatted hour

    Args:
        hour (int): Hour
        offset (int, optional): Offset. Defaults to 12.
    Returns:
        str: Formatted hour"""

    return str(hour - offset) if hour - offset else "12"


def get_date(offset: int = 0, zone: str = "America/New_York") -> datetime:
    """Returns the current date in the given timezone

    Args:
        offset (int, optional): The number of hours to offset the date. Defaults to 0.
        zone (str, optional): The timezone to return the date in. Defaults to "America/New_York".
    Returns:
        datetime: The current date in the given timezone"""

    return datetime.now(pytz.timezone(zone)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(hours=offset)


def get_current_time(offset: int = 0, zone: str = "America/New_York") -> datetime:
    """Returns the current time in the given timezone

    Args:
        offset (int, optional): The number of hours to offset the time. Defaults to 0.
        zone (str, optional): The timezone to return the time in. Defaults to "America/New_York".
    Returns:
        datetime: The current time in the given timezone"""

    return datetime.now(pytz.timezone(zone)) + timedelta(hours=offset)


def lazy_convert(time_str: str, zone: str = "America/New_York") -> datetime:
    """Lazily converts a HH:MM:SS time string to a datetime object

    Args:
        time_str (str): A time string
        zone (str, optional): The timezone to return the time in. Defaults to "America/New_York".
    Returns:
        datetime: A datetime object"""
    hour, minute, second = time_str.split(":")
    timezone = pytz.timezone(zone)
    formatted_td = format_timedelta(timezone.utcoffset(datetime.now()))
    if int(hour) >= 24:
        time_str = f"{str(int(hour) - 24).zfill(2)}:{minute}:{second}{formatted_td}"
        if 3.5 < get_current_time(zone=zone).hour < 24:
            return parse(time_str) + timedelta(days=1)
        return parse(time_str)
    return parse(time_str + formatted_td)


def timestamp_col_to_iso(dataframe: pd.DataFrame, col: str) -> pd.Series:
    """Takes a dataframe and a column of timestamps and converts them to iso strings

    Args:
        dataframe (pd.DataFrame): A dataframe
        col (str): The column of timestamps
    Returns:
        pd.Series: A series of iso strings"""

    if col not in dataframe.columns:
        return np.nan

    return dataframe[col].apply(
        lambda x: datetime.fromtimestamp(
            int(x.get("time")) if isinstance(x, dict) else int(x),
            tz=pytz.timezone("America/New_York"),
        ).isoformat()
        if not pd.isna(x)
        else None
    )


def format_timedelta(delta: timedelta) -> str:
    """Formats a timedelta object

    Args:
        delta (timedelta): A timedelta object
    Returns:
        str: A formatted timedelta string"""

    seconds = delta.seconds + delta.days * 86400
    hours, minutes = divmod(seconds, 3600)
    if hours >= 0:
        return f"+{str(hours).zfill(2)}:{str(minutes).zfill(2)}"
    return f"-{str(hours*-1).zfill(2)}:{str(minutes).zfill(2)}"


def is_valid_iso(iso_str: str) -> bool:
    """Checks if a string is a valid iso string

    Args:
        iso_str (str): A string
    Returns:
        bool: Whether the string is a valid iso string"""

    try:
        isoparse(iso_str)
        return True
    except ValueError:
        return False
