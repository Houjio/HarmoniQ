from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional
import pandas as pd
import logging
from harmoniq.db.schemas import PositionBase
import openmeteo_requests
import requests_cache
from retry_requests import retry

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
_REFERENCE_YEAR = 2024


class Meteo:
	
	def __init__(self):
		# Setup the Open-Meteo API client with cache and retry on error
		self.cache_session = requests_cache.CachedSession('.cache', expire_after = -1)
		self.retry_session = retry(self.cache_session, retries = 5, backoff_factor = 0.2)
		self.openmeteo = openmeteo_requests.Client(session = self.retry_session)

	def get_weather_data(self,Latitude,Longitude,start_date,end_date):	 
		# Make sure all required weather variables are listed here
		# The order of variables in hourly or daily is important to assign them correctly below
		url = "https://archive-api.open-meteo.com/v1/archive"
		params = {
			"latitude": Latitude,
			"longitude": Longitude,
			"start_date": start_date,
			"end_date": end_date,
			"hourly": ["temperature_2m", "relative_humidity_2m", "dew_point_2m", "apparent_temperature", "precipitation", "rain", "snowfall", "snow_depth", "soil_temperature_0_to_7cm", "soil_temperature_7_to_28cm", "soil_temperature_28_to_100cm", "soil_temperature_100_to_255cm", "wind_speed_10m", "wind_speed_100m", "wind_direction_10m", "wind_direction_100m", "wind_gusts_10m", "weather_code", "pressure_msl", "surface_pressure", "cloud_cover", "cloud_cover_low", "cloud_cover_mid", "cloud_cover_high", "et0_fao_evapotranspiration", "vapour_pressure_deficit", "soil_moisture_0_to_7cm", "soil_moisture_7_to_28cm", "soil_moisture_28_to_100cm", "soil_moisture_100_to_255cm"],
			"timezone": "America/New_York",
			"wind_speed_unit": "ms"
		}
		responses = self.openmeteo.weather_api(url, params=params)

		# Process first location. Add a for-loop for multiple locations or weather models
		response = responses[0]
		print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
		print(f"Elevation {response.Elevation()} m asl")
		print(f"Timezone {response.Timezone()}{response.TimezoneAbbreviation()}")
		print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

		# Process hourly data. The order of variables needs to be the same as requested.
		hourly = response.Hourly()
		hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
		hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
		hourly_dew_point_2m = hourly.Variables(2).ValuesAsNumpy()
		hourly_apparent_temperature = hourly.Variables(3).ValuesAsNumpy()
		hourly_precipitation = hourly.Variables(4).ValuesAsNumpy()
		hourly_rain = hourly.Variables(5).ValuesAsNumpy()
		hourly_snowfall = hourly.Variables(6).ValuesAsNumpy()
		hourly_snow_depth = hourly.Variables(7).ValuesAsNumpy()
		hourly_soil_temperature_0_to_7cm = hourly.Variables(8).ValuesAsNumpy()
		hourly_soil_temperature_7_to_28cm = hourly.Variables(9).ValuesAsNumpy()
		hourly_soil_temperature_28_to_100cm = hourly.Variables(10).ValuesAsNumpy()
		hourly_soil_temperature_100_to_255cm = hourly.Variables(11).ValuesAsNumpy()
		hourly_wind_speed_10m = hourly.Variables(12).ValuesAsNumpy()
		hourly_wind_speed_100m = hourly.Variables(13).ValuesAsNumpy()
		hourly_wind_direction_10m = hourly.Variables(14).ValuesAsNumpy()
		hourly_wind_direction_100m = hourly.Variables(15).ValuesAsNumpy()
		hourly_wind_gusts_10m = hourly.Variables(16).ValuesAsNumpy()
		hourly_weather_code = hourly.Variables(17).ValuesAsNumpy()
		hourly_pressure_msl = hourly.Variables(18).ValuesAsNumpy()
		hourly_surface_pressure = hourly.Variables(19).ValuesAsNumpy()
		hourly_cloud_cover = hourly.Variables(20).ValuesAsNumpy()
		hourly_cloud_cover_low = hourly.Variables(21).ValuesAsNumpy()
		hourly_cloud_cover_mid = hourly.Variables(22).ValuesAsNumpy()
		hourly_cloud_cover_high = hourly.Variables(23).ValuesAsNumpy()
		hourly_et0_fao_evapotranspiration = hourly.Variables(24).ValuesAsNumpy()
		hourly_vapour_pressure_deficit = hourly.Variables(25).ValuesAsNumpy()
		hourly_soil_moisture_0_to_7cm = hourly.Variables(26).ValuesAsNumpy()
		hourly_soil_moisture_7_to_28cm = hourly.Variables(27).ValuesAsNumpy()
		hourly_soil_moisture_28_to_100cm = hourly.Variables(28).ValuesAsNumpy()
		hourly_soil_moisture_100_to_255cm = hourly.Variables(29).ValuesAsNumpy()

		hourly_data = {"date": pd.date_range(
			start = pd.to_datetime(hourly.Time(), unit = "s", utc = True),
			end = pd.to_datetime(hourly.TimeEnd(), unit = "s", utc = True),
			freq = pd.Timedelta(seconds = hourly.Interval()),
			inclusive = "left"
		)}

		hourly_data["temperature_2m"] = hourly_temperature_2m
		hourly_data["relative_humidity_2m"] = hourly_relative_humidity_2m
		hourly_data["dew_point_2m"] = hourly_dew_point_2m
		hourly_data["apparent_temperature"] = hourly_apparent_temperature
		hourly_data["precipitation"] = hourly_precipitation
		hourly_data["rain"] = hourly_rain
		hourly_data["snowfall"] = hourly_snowfall
		hourly_data["snow_depth"] = hourly_snow_depth
		hourly_data["soil_temperature_0_to_7cm"] = hourly_soil_temperature_0_to_7cm
		hourly_data["soil_temperature_7_to_28cm"] = hourly_soil_temperature_7_to_28cm
		hourly_data["soil_temperature_28_to_100cm"] = hourly_soil_temperature_28_to_100cm
		hourly_data["soil_temperature_100_to_255cm"] = hourly_soil_temperature_100_to_255cm
		hourly_data["wind_speed_10m"] = hourly_wind_speed_10m
		hourly_data["wind_speed_100m"] = hourly_wind_speed_100m
		hourly_data["wind_direction_10m"] = hourly_wind_direction_10m
		hourly_data["wind_direction_100m"] = hourly_wind_direction_100m
		hourly_data["wind_gusts_10m"] = hourly_wind_gusts_10m
		hourly_data["weather_code"] = hourly_weather_code
		hourly_data["pressure_msl"] = hourly_pressure_msl
		hourly_data["surface_pressure"] = hourly_surface_pressure
		hourly_data["cloud_cover"] = hourly_cloud_cover
		hourly_data["cloud_cover_low"] = hourly_cloud_cover_low
		hourly_data["cloud_cover_mid"] = hourly_cloud_cover_mid
		hourly_data["cloud_cover_high"] = hourly_cloud_cover_high
		hourly_data["et0_fao_evapotranspiration"] = hourly_et0_fao_evapotranspiration
		hourly_data["vapour_pressure_deficit"] = hourly_vapour_pressure_deficit
		hourly_data["soil_moisture_0_to_7cm"] = hourly_soil_moisture_0_to_7cm
		hourly_data["soil_moisture_7_to_28cm"] = hourly_soil_moisture_7_to_28cm
		hourly_data["soil_moisture_28_to_100cm"] = hourly_soil_moisture_28_to_100cm
		hourly_data["soil_moisture_100_to_255cm"] = hourly_soil_moisture_100_to_255cm

		hourly_dataframe = pd.DataFrame(data = hourly_data)
		return(hourly_dataframe)


class WeatherHelper:
    def __init__(
        self,
        position: PositionBase,
        interpolate: bool,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        data_type: EnergyType = EnergyType.NONE,
        granularity: Granularity = Granularity.HOURLY,
    ):
        self.position = position
        self.interpolate = interpolate
        self.data_type = data_type

        self.start_time = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_time = (end_time or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        if self.start_time == self.end_time:
            self.end_time += timedelta(days=1)

        self._granularity = granularity
        self._data = None
        self.meteo_client = Meteo()

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

    def load(self) -> pd.DataFrame:
        if self._data is not None:
            return self._data

        print("STARTING TO LOAD METEO DATA")

        original_start = self.start_time
        original_end = self.end_time
        print(f"Original start time: {original_start}")
        print(f"Original end time: {original_end}")

        # Utilise 2024 comme année de fallback si simulation dans le futur
        if self.end_time.year > _CURRENT_YEAR:
            self.start_time = self.start_time.replace(year=2024)
            self.end_time = self.end_time.replace(year=2024)
        print(f"Adjusted start time: {self.start_time}")
        print(f"Adjusted end time: {self.end_time}")

        # Open-Meteo demande un end_date exclusif => ajouter 1 jour
        start_str = self.start_time.strftime("%Y-%m-%d")
        end_str = (self.end_time + timedelta(days=1)).strftime("%Y-%m-%d")

        print(f"Fetching data from {start_str} to {end_str}")

        df = self.meteo_client.get_weather_data(
            Latitude=self.position.latitude,
            Longitude=self.position.longitude,
            start_date=start_str,
            end_date=end_str
        )

        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["date"] = df["date"].dt.tz_convert("America/New_York").dt.tz_localize(None)
        df = df.set_index("date").sort_index()

        # Applique la vraie année de test
        df.index = df.index.map(lambda ts: ts.replace(year=original_start.year))

        expected_range = pd.date_range(
            start=original_start,
            end=original_end,
            freq="h"
        )
        df = df.reindex(expected_range)

        self._data = df
        print(self._data)
        return df







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
    df = weather.load()
    print(df.head())
    print("#-----#-----#-----#-----#")
    print("Finished loading data.")
    print("#-----#-----#-----#-----#")
