#!/usr/bin/env python3
import asyncio
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict
from enum import Enum
import logging
from geopy.distance import geodesic

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


_CURRENT_YEAR = datetime.now().year
_REFERENCE_YEAR = 2024  # décalage pour périodes futures

# Cache local
CACHE = Path(__file__).parent / "cache"
CACHE.mkdir(parents=True, exist_ok=True)
# CSV à côté de ce module, dans meteo/refined
CSV_PATH = Path(__file__).resolve().parents[1] / "meteo" / "refined" / "meteo_data.csv"
print(f"CSV_PATH: {CSV_PATH}")


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
        self.interpolate = interpolate
        self.data_type = data_type

        self.start_time = start_time
        self.end_time = end_time or datetime.now()
        if self.start_time == self.end_time:
            self.end_time = self.start_time + pd.DateOffset(days=1)

        # ajustement pour années futures
        self._timeshift = None
        if self.end_time.year > _CURRENT_YEAR:
            delta_years = self.end_time.year - _REFERENCE_YEAR
            self._timeshift = timedelta(days=365 * delta_years)
            self.start_time -= self._timeshift
            self.end_time -= self._timeshift

        self._granularity = granularity
        self._data = None

        logger.info(
            f"WeatherHelper({self.position} de {self.start_time} à {self.end_time}, granularité={self.granularity})"
        )

    @property
    def granularity(self) -> str:
        return self._granularity.name.lower()

    @property
    def data(self) -> pd.DataFrame:
        if self._data is None:
            raise ValueError("Data not loaded")
        return self._data

    @property
    def _cache_key(self) -> str:
        lat, lon = round(self.position.latitude, 4), round(self.position.longitude, 4)
        t0 = self.start_time.strftime("%Y%m%d")
        t1 = self.end_time.strftime("%Y%m%d")
        return f"{lat}_{lon}_{t0}_{t1}_{self.granularity}_{self.data_type.name.lower()}"

    def test_cache(self) -> bool:
        path = CACHE / f"{self._cache_key}.csv"
        if path.exists():
            logger.info(f"Cache hit {path}")
            return True
        return False

    def load_cache(self) -> pd.DataFrame:
        return pd.read_csv(CACHE / f"{self._cache_key}.csv", index_col=0, parse_dates=True)

    def save_cache(self, df: pd.DataFrame) -> None:
        df.to_csv(CACHE / f"{self._cache_key}.csv", index=True)
        logger.info("Saved cache file")

    def _apply_timeshift(self, df: pd.DataFrame) -> pd.DataFrame:
        if self._timeshift:
            df.index = df.index + self._timeshift
        return df

    async def load(self) -> pd.DataFrame:
        if self._data is not None:
            return self._apply_timeshift(self._data)

        # use cache if available
        if self.test_cache():
            return self._apply_timeshift(self.load_cache())

        # load per-station data
        station_dfs = await self._read_all_stations()
        if not station_dfs:
            raise ValueError(
                f"No station data found between {self.start_time} and {self.end_time}"
            )

        # map to weather schema
        cleaned = {sid: self._to_schema(df) for sid, df in station_dfs.items()}

        # always use nearest station only
        distances = {
            sid: geodesic(
                (self.position.latitude, self.position.longitude),
                (df['latitude'].iloc[0], df['longitude'].iloc[0])
            ).km
            for sid, df in cleaned.items()
        }
        nearest = min(distances, key=distances.get)
        df_final = cleaned[nearest].copy()

        # truncate to requested period
        df_final = df_final.loc[
            (df_final.index >= self.start_time) & (df_final.index <= self.end_time)
        ]

        self._data = df_final
        self.save_cache(df_final)
        return self._apply_timeshift(df_final)

    async def _read_all_stations(self) -> Dict[int, pd.DataFrame]:
        df = pd.read_csv(CSV_PATH, parse_dates=["LOCAL_DATE"], low_memory=False)
        df = df.rename(columns={"LOCAL_DATE": "date", "x": "longitude", "y": "latitude"})
        df = df.set_index("date").sort_index()
        df = df.loc[self.start_time:self.end_time]

        if self._granularity == Granularity.DAILY:
            df = df.groupby('CLIMATE_IDENTIFIER').resample('D').first().reset_index(level=0)

        results = {}
        for sid, grp in df.groupby('CLIMATE_IDENTIFIER'):
            grp = grp[~grp.index.duplicated(keep='first')]
            if self._granularity == Granularity.HOURLY:
                dates = pd.date_range(self.start_time, self.end_time, freq='h')
            else:
                dates = pd.date_range(self.start_time, self.end_time, freq='D')
            tmp = grp.reset_index().set_index('date')
            tmp = tmp[~tmp.index.duplicated(keep='first')]
            tmp = tmp.reindex(dates)
            tmp.index.name = 'date'
            results[sid] = tmp
        return results

    def _to_schema(self, data: pd.DataFrame) -> pd.DataFrame:
        idx = pd.to_datetime(data.index)
        out = pd.DataFrame(index=idx, columns=weather_schema.columns.keys())
        out.index.name = 'tempsdate'

        out['longitude']        = data['longitude']
        out['latitude']         = data['latitude']
        out['precipitation_mm'] = data['PRECIP_AMOUNT']
        out['direction_vent']   = data['WIND_DIRECTION']
        out['vitesse_vent_kmh'] = data['WIND_SPEED']
        out['humidite']         = data['RELATIVE_HUMIDITY']
        out['pression']         = data['STATION_PRESSURE']
        out['point_de_rosee']   = data['DEW_POINT_TEMP']

        if self._granularity == Granularity.HOURLY:
            out['temperature_C'] = data['TEMP']
            out[['max_temperature_C','min_tempature_C',
                 'pluie_mm','neige_cm','neige_accumulee_cm']] = pd.NA
        else:
            out['temperature_C']     = data['TEMP']
            out['max_temperature_C'] = data['TEMP']
            out['min_tempature_C']   = data['TEMP']
            out['pluie_mm']          = data['PRECIP_AMOUNT']
            out['neige_cm']          = pd.NA
            out['neige_accumulee_cm']= pd.NA
        return out


if __name__ == "__main__":
    pos = PositionBase(latitude=45.80944, longitude=-73.43472)
    start_time = datetime(2024, 9, 1)
    end_time = datetime(2024, 9, 4)
    granularity = Granularity.HOURLY

    weather = WeatherHelper(
        pos,
        interpolate=True,
        start_time=start_time,
        end_time=end_time,
        data_type=EnergyType.EOLIEN,
        granularity=granularity,
    )

    print("#-----#-----#-----#-----#")
    print("Running the load method...")
    print("#-----#-----#-----#-----#")
    df = asyncio.run(weather.load())
    print(df.head())
    print("#-----#-----#-----#-----#")
    print("Finished loading data.")
    print("#-----#-----#-----#-----#")
