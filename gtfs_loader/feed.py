"""Feed Object for GTFS Loader"""
import os
import io
import time
import zipfile
import logging
import tempfile
from datetime import datetime
import pytz

import requests
import pandas as pd
from geojson import FeatureCollection, dumps

from sqlalchemy import create_engine, or_, not_, and_, delete, CursorResult, text
from sqlalchemy.sql import selectable, select
from sqlalchemy.orm import sessionmaker, attributes
from sqlalchemy.exc import IntegrityError

from gtfs_schedule import *  # pylint: disable=wildcard-import
from .gtfs_base import GTFSBase  # pylint: disable=relative-beyond-top-level
from .query import Query  # pylint: disable=relative-beyond-top-level
from gtfs_realtime import Prediction, Vehicle, Alert
from poll_mbta_data import predictions, vehicles, alerts
from shared_code.df_unpack import df_unpack  # pylint: disable=relative-beyond-top-level


class Feed:
    """Loads GTFS data into a SQLite database.

    Args:
        url (str): url of GTFS feed
        route_types (comma sep str): route types to load
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, url: str, route_types: str) -> None:
        self.url = url
        self.route_types = route_types.split(",")
        # ------------------------------- Connection/Session Setup ------------------------------- #
        self.temp_dir = tempfile.gettempdir()
        self.gtfs_name = url.rsplit("/", maxsplit=1)[-1].split(".")[0]
        self.db_path = os.path.join(self.temp_dir, f"{self.gtfs_name}_{route_types}.db")
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.session = sessionmaker(self.engine)()
        # ------------------------------- Query Setup ------------------------------- #
        self.queries = Query(route_types)

    def __repr__(self) -> str:
        return f"<Feed(url={self.url}, route_types={self.route_types})>"

    def import_gtfs(self, chunksize: int = 10**5) -> None:
        """Dumps GTFS data into a SQLite database.

        Args:
            chunksize (int): number of rows to insert at a time (default: 10**5)
        """
        # ------------------------------- Create Tables ------------------------------- #
        start = time.time()
        zip_path = os.path.join(self.temp_dir, self.gtfs_name)
        self.download_zip(zip_path)
        GTFSBase.metadata.drop_all(self.engine)
        GTFSBase.metadata.create_all(self.engine)
        # note that the order of these tables matters; avoids foreign key errors
        table_dict = {
            "agency.txt": Agency,
            "stops.txt": Stop,
            "calendar.txt": Calendar,
            "calendar_dates.txt": CalendarDate,
            "calendar_attributes.txt": CalendarAttribute,
            "facilities.txt": Facility,
            "routes.txt": Route,
            "shapes.txt": ShapePoint,
            "trips.txt": Trip,
            "facilities_properties.txt": FacilityProperty,
            "multi_route_trips.txt": MultiRouteTrip,
            "stop_times.txt": StopTime,
            "transfers.txt": Transfer,
        }

        # ------------------------------- Dump Data ------------------------------- #

        for file, orm in table_dict.items():
            with pd.read_csv(
                os.path.join(zip_path, file), chunksize=chunksize, dtype=object
            ) as read:
                for chunk in read:
                    if file == "shapes.txt":
                        try:
                            self.to_sql(chunk["shape_id"].drop_duplicates(), Shape)
                        except IntegrityError:
                            self.to_sql(
                                chunk["shape_id"].drop_duplicates().iloc[1:], Shape
                            )
                    self.to_sql(chunk, orm, file == "transfers.txt")

        logging.info("Loaded %s in %f s", self.gtfs_name, time.time() - start)

    def purge_and_filter(self) -> None:
        """Purges unused data from the database.

        This first deletes calendar dates that aren't active or associated with a trip
        with the specified route type or multi route trips. This cascades to trips and stoptimes. It
        then deletes stops, shapes, facilities, routes based off of the remaining trips/stoptimes.

        This is done to 1) save space and 2) make querying simplier (i.e. no need to filter)
        """

        start = time.time()
        initial_size = os.path.getsize(self.db_path)
        # ------------------------------- Delete Calendars ------------------------------- #
        date = datetime.now(pytz.timezone("America/New_York"))
        cal_stmt_1 = delete(Calendar.__table__).where(
            Calendar.service_id.notin_(
                (
                    select(
                        self.queries.return_all_calendars_query(date).columns.service_id
                    )
                )
            )
        )
        stops_stmt = delete(Stop.__table__).where(
            not_(
                or_(
                    Stop.stop_id.in_(
                        select(self.queries.platform_stops_query.columns.stop_id)
                    ),
                    Stop.stop_id.in_(
                        select(self.queries.parent_stops_query.columns.stop_id),
                    ),
                )
            )
        )
        shapes_stmt = delete(Shape.__table__).where(
            Shape.shape_id.notin_(select(Trip.shape_id))
        )
        routes_stmt = delete(Route.__table__).where(
            Route.route_id.notin_(select(Trip.route_id).distinct())
        )

        cal_stmt_2 = delete(Calendar.__table__).where(
            Calendar.service_id.notin_(
                (
                    select(
                        self.queries.return_active_calendars_query(
                            date
                        ).columns.service_id
                    )
                )
            )
        )

        for stmt in [cal_stmt_1, stops_stmt, shapes_stmt, routes_stmt, cal_stmt_2]:
            res: CursorResult = self.session.execute(stmt)
            self.session.commit()  # seperate commits to avoid giant journal file
            logging.info("Deleted %s rows from %s", res.rowcount, stmt.table.name)

        change = (initial_size - os.path.getsize(self.db_path)) / 1000000
        logging.info("Purged data (%f mb) in %f seconds", change, time.time() - start)

    def download_zip(self, file_path: str = "") -> None:
        """Downloads the gtfs zip file from the url.

        Args:
            file_path (str): path to extract to (default: current directory)

        Note that this function will create a file at file_path if one does not exist.
        """
        source = requests.get(self.url, timeout=10)
        with zipfile.ZipFile(io.BytesIO(source.content)) as zipfile_bytes:
            zipfile_bytes.extractall(file_path)
        logging.info("Downloaded zip from %s to %s", self.url, file_path)

    def download_realtime_data(self) -> None:
        """Downloads realtime data from the mbta api."""

        active_routes = ",".join(
            item[0]
            for item in self.session.execute(select(Route.route_id).distinct()).all()
        )
        for orm in [Prediction, Vehicle, Alert]:
            self.session.execute(delete(orm.__table__))
            self.session.commit()

        for route_type in self.route_types:
            self.to_sql(vehicles.get_vehicles(route_type), Vehicle)
            self.to_sql(alerts.get_alerts(route_type), Alert, True)
        self.to_sql(predictions.get_predictions(active_routes), Prediction)
        print()

    def to_sql(self, data: pd.DataFrame, orm: GTFSBase, index: bool = False) -> None:
        """Helper function to dump dataframe to sql.

        Args:
            data (pd.DataFrame): dataframe to dump
            orm (any): table to dump to
            index (bool, optional): whether to include index in dump. Defaults to False.
        """
        res = data.to_sql(orm.__tablename__, self.engine, None, "append", index)
        logging.info("Added %s rows to %s", res, orm.__tablename__)

    def to_geojson(self, query: selectable.Select) -> str:
        """Converts a table to geojson."""

        return dumps(
            FeatureCollection(
                [
                    i[0].as_feature()
                    for i in self.session.execute(query)
                    if hasattr(i[0], "as_feature")
                ]
            )
        )
