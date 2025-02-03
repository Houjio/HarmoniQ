import asyncio

from env_canada import ECHistorical, ECWeather
from env_canada.ec_historical import get_historical_stations

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from harmoniq.db.shemas import PositionBase


class Granularity(Enum):
    HOURLY = 1
    DAILY = 2


class WeatherHelper:
    def __init__(
        self,
        position: PositionBase,
        interpolate: bool,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        granularity: Granularity = Granularity.DAILY,
    ):
        self.position = position
        self.elevation: Optional[float] = None
        self.start_time = start_time
        self._start_year = start_time.year
        self._start_month = start_time.month
        self._start_day = start_time.day

        self.end_time = end_time or datetime.now()
        self._end_year = end_time.year if end_time else None
        self._end_month = end_time.month if end_time else None
        self._end_day = end_time.day if end_time else None

        self._granularity = granularity
        self._nearby_stations: Optional[pd.DataFrame] = None
        self._data: Optional[pd.DataFrame] = None

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
        self._nearby_stations = self._get_nearest_station()
        for station in self._nearby_stations.itertuples():
            range = (
                station.hlyRange
                if self._granularity == Granularity.HOURLY
                else station.dlyRange
            )

            if range != "|":
                break

        self._data = self._get_historical_data(
            int(station.id),
            self._granularity.value,
            self._start_year,
            self._start_month,
        )

        self._clean_data(self._data)

    @staticmethod
    def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
        df["Date/Heure (HNL)"] = pd.to_datetime(df["Date/Heure (HNL)"])
        df.set_index("Date/Heure (HNL)", inplace=True)
        df.drop(columns=["Année", "Mois", "Jour", "Heure (HNL)"], inplace=True)
        columns_to_numeric = [
            "Temp (°C)",
            "Point de rosée (°C)",
            "Hum. rel (%)",
            "Hauteur de précip. (mm)",
            "Dir. du vent (10s deg)",
            "Vit. du vent (km/h)",
            "Visibilité (km)",
            "Pression à la station (kPa)",
            "Hmdx",
            "Refroid. éolien",
        ]

        for column in columns_to_numeric:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        return df

    def _get_nearest_station(
        self,
        radius: Optional[int] = 200,
        limit: Optional[int] = 100,
    ) -> pd.DataFrame:
        coordinates = (self.position.latitude, self.position.longitude)

        start_year = self._start_year or 1840
        end_year = self._end_year or datetime.now().year

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
        return stations

    @staticmethod
    def _get_historical_data(
        station_id: int,
        timeframe: int,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> pd.DataFrame:
        if year is None and month is None:
            raise ValueError("year or month must be provided")

        if year is None and month is not None:
            raise ValueError("year must be provided")

        if year is not None and month is None:
            historical = ECHistorical(
                station_id=station_id,
                year=year,
                timeframe=timeframe,
                language="french",
                format="csv",
            )
        else:
            historical = ECHistorical(
                station_id=station_id,
                year=year,
                month=month,
                timeframe=timeframe,
                language="french",
                format="csv",
            )

        asyncio.run(historical.update())
        return pd.read_csv(historical.station_data)

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
    end_time = datetime(2021, 1, 31)
    granularity = Granularity.HOURLY

    weather = WeatherHelper(pos, False, start_time, end_time, granularity)
    weather.load()
