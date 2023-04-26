from dataclasses import dataclass
import time
import folium
from PIL import Image, ImageFont
import numpy as np
import pandas as pd
from shared_code import center_text


@dataclass
class Vehicle:

    row: pd.Series = None
    vehicle_icon: Image.Image = None

    def __post_init__(self):

        if self.row["stop_status"] == "IN_TRANSIT_TO":
            status = "In transit to"
        elif self.row["stop_status"] == "STOPPED_AT":
            status = "Stopped at"
        else:
            status = "Unknown"

        self.status = status

    def build_vehicle(self):
        """builds vehicle icon"""

        html = f"""<strong>Vehicle:</strong> {self.row["vehicle_id"]}<br>
               <strong>Trip:</strong> {self.row["trip_short_name"]}<br> 
               <strong>Route:</strong> {self.row["route"]}<br>
               <strong>Status:</strong> {self.row["stop_status"]} <a href="https://www.mbta.com/stops/{self.row["parent_station"]}">{self.row["stop_name"]}</a><br>
               <strong>Time:</strong> {self.row["timestamp"]}<br>
               <strong>Speed:</strong> {self.row["speed"]} mph<br>
               <strong>Heading:</strong> {self.row["bearing"]} degrees<br>"""

        iframe = folium.IFrame(html, width=200, height=200)
        popup = folium.Popup(iframe, max_width=400)

        # don't even think about it

        icon = folium.CustomIcon(self.generate_icon(), icon_size=(50, 50))

        marker = folium.Marker(
            location=[self.row["latitude"], self.row["longitude"]],
            icon=icon,
            popup=popup,
            zIndexOffset=1000,
        )
        return marker

    def generate_icon(self):
        """generates vehicle icon"""

        vehicle_image = self.vehicle_icon.rotate(-1 * self.row["bearing"])

        center_text.center_text(
            vehicle_image,
            ImageFont.truetype("times", 275),
            self.row["trip_short_name"],
            (0, 0, 0),
            (0, -40),
        )

        vehicle_image = np.array(vehicle_image)

        return vehicle_image
