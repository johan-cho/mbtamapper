"""File to hold the Shape class and its associated methods."""

from typing import TYPE_CHECKING, Any, override

from geojson import Feature
from shapely.geometry import LineString
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .shape_point import ShapePoint
    from .trip import Trip


class Shape(Base):
    """Shape

    this table isn't in the gtfs spec, but is used to \
        group `ShapePoint`s together

    """

    __tablename__ = "shapes"

    shape_id: Mapped[str] = mapped_column(primary_key=True)

    trips: Mapped[list["Trip"]] = relationship(
        back_populates="shape", passive_deletes=True
    )
    shape_points: Mapped[list["ShapePoint"]] = relationship(
        back_populates="shape", passive_deletes=True
    )

    def as_linestring(self) -> LineString:
        """Return a shapely `LineString` object of the shape

        returns:
            - `LineString`: A shapely LineString object.
        """

        return LineString([sp.as_point() for sp in sorted(self.shape_points)])

    def as_feature(self, *include: str) -> Feature:
        """Returns shape object as a feature.

        args:
            - `*include`: A list of properties to include in the feature object.\n
        Returns:
            - `Feature`: A GeoJSON feature object.
        """

        return Feature(
            id=self.shape_id,
            geometry=self.as_linestring(),
            properties=self.as_json(*include),
        )

    @override
    def as_json(self, *include, **kwargs) -> dict[str, Any]:
        """Returns shape object as a dictionary.

        args:
            - `*include`: A list of properties to include in the dictionary.
            - `**kwargs`: unused\n
        Returns:
            - `dict[str, Any]`: shape as a dictionary.\n
        """

        return super().as_json(*include, **kwargs) | self.trips[0].route.as_json(
            *include
        )
