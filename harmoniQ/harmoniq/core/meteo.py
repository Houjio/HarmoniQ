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

from harmoniq.db.schemas import PositionBase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class Granularity(Enum):
    DAILY = 1
    HOURLY = 2


class Type(Enum):
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
        data_type: Type = Type.NONE,
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

            if not self._validate_type(sub_data, self.data_type):
                logger.info(f"Data not of right type")
                continue

            sub_data = self._clean_data(sub_data)

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
    def _validate_type(data: pd.DataFrame, data_type: Type) -> List[str]:
        ...
        print(f"Data type: {data_type}")
        return True  # TODO: Implement

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if "Date/Time (LST)" in df.keys():
            df["Date/Time"] = pd.to_datetime(df["Date/Time (LST)"])

        df["Date/Time"] = pd.to_datetime(df["Date/Time"])
        df.set_index("Date/Time", inplace=True)
        print(df.keys())
        if self._granularity == Granularity.HOURLY:
            keys = [
                "Longitude (x)",
                "Latitude (y)",
                "Station Name",
                "Climate ID",
                "Max Temp (°C)",
                "Min Temp (°C)",
                "Mean Temp (°C)",
                "Total Rain (mm)",
                "Total Snow (cm)",
                "Total Precip (mm)",
                "Snow on Grnd (cm)",
                "Dir of Max Gust (10s deg)",
                "Spd of Max Gust (km/h)",
            ]
        elif self._granularity == Granularity.DAILY:
            keys = [
                "Longitude (x)",
                "Latitude (y)",
                "Station Name",
                "Climate ID",
                "Temp (°C)",
                "Dew Point Temp (°C)",
                "Rel Hum (%)",
                "Precip. Amount (mm)",
                "Wind Dir (10s deg)",
                "Wind Spd (km/h)",
                "Hmdx",
                "Wind Chill",
            ]

        df = df[keys]
        for key in df.keys():
            df.loc[:, key] = pd.to_numeric(df.loc[:, key], errors="coerce")

        return df

    def _interpolate_data(self, list_of_df: List[pd.DataFrame]) -> pd.DataFrame:

        latlon = [
            i[["Latitude (y)", "Longitude (x)"]].iloc[0].values for i in list_of_df
        ]

        dist = [
            geodesic([self.position.latitude, self.position.longitude], i).km
            for i in latlon
        ]
        dist = np.array(dist)

        weights = 1 / dist
        new_data = pd.DataFrame(index=list_of_df[0].index)
        for keys in list_of_df[0].keys():
            if keys == "Date/Time":
                continue
            if keys == "Latitude (y)":
                new_data["Latitude (y)"] = self.position.latitude
            elif keys == "Longitude (x)":
                new_data["Longitude (x)"] = self.position.longitude
            elif keys == "Station Name":
                new_data["Station Name"] = "Interpolated"
            elif keys == "Climate ID":
                new_data["Climate ID"] = "Interpolated"
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
            station_id, timeframe=1, year=year, month=month
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

    weather = WeatherHelper(pos, True, start_time, end_time, Type.NONE, granularity)
    weather.load()
