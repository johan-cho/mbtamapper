"""File to hold the Calendar class and its associated methods."""
from shapely.geometry import Point
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .gtfs_base import GTFSBase


class ShapePoint(GTFSBase):
    """Shape"""

    __tablename__ = "shape_points"
    __filename__ = "shapes.txt"

    shape_id = Column(
        String,
        ForeignKey("shapes.shape_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    shape_pt_lat = Column(Float)
    shape_pt_lon = Column(Float)
    shape_pt_sequence = Column(Integer, primary_key=True)
    shape_dist_traveled = Column(Float)

    shape = relationship("Shape", back_populates="shape_points")

    def as_point(self) -> Point:
        """Returns a shapely Point object of the shape point"""
        return Point(self.shape_pt_lon, self.shape_pt_lat)
