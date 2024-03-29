"""File to hold the Calendar class and its associated methods."""
from datetime import datetime

import pytz
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import reconstructor, relationship

from .gtfs_base import GTFSBase


class Calendar(GTFSBase):
    """Calendar"""

    __tablename__ = "calendars"
    __filename__ = "calendar.txt"

    service_id = Column(String, primary_key=True)
    monday = Column(Integer)
    tuesday = Column(Integer)
    wednesday = Column(Integer)
    thursday = Column(Integer)
    friday = Column(Integer)
    saturday = Column(Integer)
    sunday = Column(Integer)
    start_date = Column(String)
    end_date = Column(String)

    calendar_dates = relationship(
        "CalendarDate", back_populates="calendar", passive_deletes=True
    )
    calendar_attributes = relationship(
        "CalendarAttribute", back_populates="calendar", passive_deletes=True
    )
    trips = relationship("Trip", back_populates="calendar", passive_deletes=True)

    @reconstructor
    def _init_on_load_(self) -> None:
        """Initialize the calendar object on load"""
        # pylint: disable=attribute-defined-outside-init

        self.start_datetime = pytz.timezone("America/New_York").localize(
            datetime.strptime(self.start_date, "%Y%m%d")
        )

        self.end_datetime = pytz.timezone("America/New_York").localize(
            datetime.strptime(self.end_date, "%Y%m%d")
        )

    def operates_on_date(self, date: datetime) -> bool:
        """Returns true if the calendar operates on the date

        Args:
            date (datetime): The date to check
        Returns:
            bool: True if the calendar operates on the date
        """
        exception = next(
            (s for s in self.calendar_dates if s.date == date.strftime("%Y%m%d")), None
        )

        return bool(
            self.start_datetime.date() <= date.date() <= self.end_datetime.date()
            and getattr(self, date.strftime("%A").lower())
            and not (exception and exception.exception_type == "2")
        ) or (exception and exception.exception_type == "1")
