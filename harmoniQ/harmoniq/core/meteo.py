import asyncio

from env_canada import ECHistorical
from env_canada.ec_historical import get_historical_stations

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, List
from enum import Enum
from geopy.distance import geodesic

import logging

from harmoniq.db.schemas import PositionBase, weather_schema

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class Granularity(Enum):
    DAILY = 2
    HOURLY = 1


class EnergyType(Enum):
    NONE = 0
    HYDRO = 1
    SOLAIRE = 2
    EOLIEN = 3


class WeatherHelper:
    def __init__(
        self,
        position: PositionBase,
        interpolate: bool,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        data_type: EnergyType = EnergyType.NONE,
        granularity: Granularity = Granularity.DAILY,
    ):
        self.position = position
        self.elevation: Optional[float] = None
        self.interpolate = interpolate
        self.data_type = data_type

        self.start_time = start_time
        self.end_time = end_time or datetime.now()

        self._granularity = granularity
        self._nearby_stations: Optional[pd.DataFrame] = None
        self._data: Optional[pd.DataFrame] = None

        logger.info(
            f"Created WeatherHelper({self.position} de {self.start_time} à {self.end_time})"
        )

    def __repr__(self):
        return f"WeatherHelper({self.position} de {self.start_time} à {self.end_time})"

    @property
    def granularity(self) -> str:
        return self._granularity.name.lower()

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            raise ValueError("Data not loaded")
        return self._data

    def load(self) -> None:
        if self._data is not None:
            return self._data

        self._nearby_stations = self._get_nearest_station()

        valid_data = 0
        data_list = []
        for station in self._nearby_stations.itertuples():
            logger.info(f"Getting data from {station.Index}")
            range = (
                station.hlyRange
                if self._granularity == Granularity.HOURLY
                else station.dlyRange
            )

            if range == "|":
                logger.info(
                    f"No {'hourly' if self._granularity == Granularity.HOURLY else 'daily'} data available"
                )
                continue

            sub_data = self._get_historical_data_range(int(station.id))

            sub_data = self._to_schema(sub_data)

            if not self._validate_type(sub_data, self.data_type):
                logger.info(f"Data not of right type")
                continue

            if not self.interpolate:
                self._data = sub_data
                return self._data

            valid_data += 1
            logger.info(f"Found valid data from {station.Index}")
            data_list.append(sub_data)

            if valid_data >= 5:
                break

        self._data = self._interpolate_data(data_list)

        if self._data is None:
            raise ValueError("No valid data found")

        # Trim data out of range
        self._data = self._data.loc[
            (self._data.index >= self.start_time) & (self._data.index <= self.end_time)
        ]

        return self._data

    @staticmethod
    def _validate_type(data: pd.DataFrame, energy_type: EnergyType) -> List[str]:
        if energy_type == EnergyType.NONE:
            return True
        elif energy_type == EnergyType.HYDRO:
            if data["precipitation_mm"].isnull().all():
                return False
        elif energy_type == EnergyType.SOLAIRE:
            if data["temperature_C"].isnull().all():
                return False
        elif energy_type == EnergyType.EOLIEN:
            if data["vitesse_vent_kmh"].isnull().all():
                return False
        else:
            raise ValueError("Invalid energy type")

        return True

    def _interpolate_data(self, list_of_df: List[pd.DataFrame]) -> pd.DataFrame:
        latlon = [i[["latitude", "longitude"]].iloc[0].values for i in list_of_df]

        dist = [
            geodesic([self.position.latitude, self.position.longitude], i).km
            for i in latlon
        ]
        dist = np.array(dist)

        weights = 1 / dist
        new_data = pd.DataFrame(index=list_of_df[0].index)
        for keys in list_of_df[0].keys():
            if keys == "tempsdate":
                continue
            if keys == "latitude":
                new_data["latitude"] = self.position.latitude
            elif keys == "longitude":
                new_data["longitude"] = self.position.longitude
            else:
                new_data[keys] = np.average(
                    [i[keys] for i in list_of_df], axis=0, weights=weights
                )

        return new_data

    def _get_nearest_station(
        self,
        radius: Optional[int] = 200,
        limit: Optional[int] = 100,
    ) -> pd.DataFrame:
        if self._nearby_stations is not None:
            return self._nearby_stations

        logger.info(f"Getting nearby stations for {self.position}")
        coordinates = (self.position.latitude, self.position.longitude)

        start_year = self.start_time.year
        end_year = self.end_time.year or datetime.now().year

        stations = pd.DataFrame(
            asyncio.run(
                get_historical_stations(
                    coordinates,
                    start_year=start_year,
                    end_year=end_year,
                    radius=radius,
                    limit=limit,
                )
            )
        ).T

        self._nearby_stations = stations
        return stations

    def _to_schema(self, data: pd.DataFrame) -> pd.DataFrame:
        # Create a empty dataframe with the right columns (and time as index)
        if self._granularity == Granularity.HOURLY:
            time = pd.to_datetime(data["Date/Time (LST)"])
        elif self._granularity == Granularity.DAILY:
            time = pd.to_datetime(data["Date/Time"])

        clean_df = pd.DataFrame(columns=weather_schema.columns.keys(), index=time)
        clean_df.index.name = "tempsdate"

        # Align the index of the old data with the new data
        data.index = time
        data.index.name = "tempsdate"

        # Add the time, longitude and latitude
        clean_df["longitude"] = data["Longitude (x)"]
        clean_df["latitude"] = data["Latitude (y)"]

        if self._granularity == Granularity.HOURLY:
            # Add the data specific to hourly granularity
            clean_df["temperature_C"] = data["Temp (°C)"]
            clean_df["max_temperature_C"] = np.nan
            clean_df["min_tempature_C"] = np.nan
            clean_df["pluie_mm"] = np.nan
            clean_df["neige_cm"] = np.nan
            clean_df["precipitation_mm"] = data["Precip. Amount (mm)"]
            clean_df["neige_accumulee_cm"] = np.nan
            clean_df["direction_vent"] = data["Wind Dir (10s deg)"]
            clean_df["vitesse_vent_kmh"] = data["Wind Spd (km/h)"]
            clean_df["humidite"] = data["Rel Hum (%)"]
            clean_df["pression"] = data["Stn Press (kPa)"]
            clean_df["point_de_rosee"] = data["Dew Point Temp (°C)"]
        elif self._granularity == Granularity.DAILY:
            # Add the data specific to daily granularity
            clean_df["temperature_C"] = data["Mean Temp (°C)"]
            clean_df["max_temperature_C"] = data["Max Temp (°C)"]
            clean_df["min_tempature_C"] = data["Min Temp (°C)"]
            clean_df["pluie_mm"] = data["Total Rain (mm)"]
            clean_df["neige_cm"] = data["Total Snow (cm)"]
            clean_df["precipitation_mm"] = data["Total Precip (mm)"]
            clean_df["neige_accumulee_cm"] = data["Snow on Grnd (cm)"]
            clean_df["direction_vent"] = data["Dir of Max Gust (10s deg)"]
            clean_df["vitesse_vent_kmh"] = data["Spd of Max Gust (km/h)"]
            clean_df["humidite"] = clean_df["pression"] = clean_df["point_de_rosee"] = (
                np.nan
            )

        return clean_df

    @staticmethod
    def _get_historical_data(
        station_id: int,
        granularity: Granularity,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> pd.DataFrame:
        if year is None and month is None:
            raise ValueError("year or month must be provided")

        if year is None and month is not None:
            raise ValueError("year must be provided")

        if granularity == Granularity.DAILY:
            historical = ECHistorical(
                station_id=station_id,
                year=year,
                timeframe=granularity.value,
                language="english",
                format="csv",
            )
        elif granularity == Granularity.HOURLY:
            historical = ECHistorical(
                station_id=int(station_id),
                year=year,
                month=month,
                timeframe=granularity.value,
                language="english",
                format="csv",
            )
        else:
            raise ValueError("Invalid granularity")

        asyncio.run(historical.update())
        return pd.read_csv(historical.station_data)

    def _get_historical_data_range(
        self,
        station_id: int,
    ) -> pd.DataFrame:
        if self._granularity == Granularity.HOURLY:
            date_range = pd.date_range(
                start=self.start_time, end=self.end_time, freq="MS"
            )
        elif self._granularity == Granularity.DAILY:
            date_range = pd.date_range(
                start=self.start_time, end=self.end_time, freq="YS"
            )
        else:
            raise ValueError("Invalid granularity")

        data = pd.DataFrame()
        for date in date_range:
            data_instance = self._get_historical_data(
                station_id, self._granularity, year=date.year, month=date.month
            )

            data = pd.concat([data, data_instance])

        return data

    def _get_historical_data_hourly(
        self,
        station_id: int,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        return self._get_historical_data(
            station_id, granularity=1, year=year, month=month
        )

    def _get_historical_data_daily(
        self,
        station_id: int,
        year: int,
    ) -> pd.DataFrame:
        return self._get_historical_data(station_id, timeframe=2, year=year)


if __name__ == "__main__":
    pos = PositionBase(latitude=49.049334, longitude=-66.750423)
    start_time = datetime(2021, 1, 1)
    end_time = datetime(2021, 3, 31)
    granularity = Granularity.HOURLY

    weather = WeatherHelper(
        pos, True, start_time, end_time, EnergyType.NONE, granularity
    )
    weather.load()
