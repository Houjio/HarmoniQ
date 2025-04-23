import pytest
import aiohttp
from datetime import datetime
from harmoniq.core.meteo import WeatherHelper, Granularity
from harmoniq.db.schemas import PositionBase

@pytest.fixture(autouse=True)
def disable_ssl(monkeypatch):
    """
    Globally disable SSL certification verification in aiohttp connectors for all tests.
    """
    original = aiohttp.TCPConnector
    class InsecureConnector(original):
        def __init__(self, *args, **kwargs):
            # Force ssl=False to bypass certificate verification
            kwargs['ssl'] = False
            super().__init__(*args, **kwargs)
    monkeypatch.setattr(aiohttp, 'TCPConnector', InsecureConnector)


@pytest.fixture
def position():
    return PositionBase(latitude=49.049334, longitude=-66.750423)

@pytest.fixture
def start_time():
    return datetime(2021, 1, 1)

@pytest.fixture
def end_time():
    return datetime(2021, 3, 31)

@pytest.mark.asyncio
async def test_weather_helper_load_data(position, start_time, end_time):
    """
    Test that load() fetches and stores data without errors.
    """
    helper = WeatherHelper(
        position,
        True,
        start_time,
        end_time,
        Granularity.HOURLY
    )
    await helper.load()
    df = helper.data
    assert df is not None
    assert not df.empty

@pytest.mark.asyncio
async def test_weather_helper_interpolation(position, start_time, end_time):
    """
    Test that interpolation runs and produces continuous data.
    """
    helper = WeatherHelper(
        position,
        True,
        start_time,
        end_time,
        Granularity.HOURLY
    )
    await helper.load()
    df = helper.data
    expected_count = int((end_time - start_time).total_seconds() // 3600) + 1
    assert len(df) == expected_count

@pytest.mark.asyncio
async def test_weather_helper_nearest_station_ssl_bypass(monkeypatch, position, start_time, end_time):
    """
    Test that _get_nearest_station populates nearby stations list
    even when SSL certificate verification would fail.
    """
    original_connector = aiohttp.TCPConnector
    class InsecureConnector(original_connector):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, ssl=False, **kwargs)
    monkeypatch.setattr(aiohttp, 'TCPConnector', InsecureConnector)

    helper = WeatherHelper(
        position,
        False,
        start_time,
        end_time,
        Granularity.HOURLY
    )
    stations = await helper._get_nearest_station()
    assert stations is not None
    if hasattr(stations, 'empty'):
        assert not stations.empty
    else:
        assert isinstance(stations, list)
        assert len(stations) > 0
