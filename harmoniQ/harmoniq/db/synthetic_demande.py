"""
Synthetic demand data when demande.db is not available.

Generates a duck-curve profile (double peak with midday dip) over the year
with a sinusoidal seasonal modulation (higher in winter, lower in summer, Québec-style).
All values in kWh for compatibility with existing load_demand_data (which divides by 1000 to get MW).
"""

from typing import Optional

import numpy as np
import pandas as pd

from harmoniq.db.schemas import Scenario

# Base annual energy (TWh) for scaling; ~200 TWh typical for Québec
BASE_ANNUAL_ENERGY_TWH = 200.0
# Sector names for Sankey
SYNTHETIC_SECTORS = ["Résidentiel", "Commercial", "Industriel", "Transport", "Autre"]
# Proportional split (must sum to 1)
SECTOR_WEIGHTS = np.array([0.35, 0.28, 0.22, 0.08, 0.07])


def _hour_of_day_rad(t: pd.DatetimeIndex) -> np.ndarray:
    """Hour of day as angle [0, 2*pi)."""
    h = t.hour + t.minute / 60.0 + t.second / 3600.0
    return 2 * np.pi * h / 24.0


def _day_of_year_rad(t: pd.DatetimeIndex) -> np.ndarray:
    """Day of year as angle [0, 2*pi). Peak in winter (day ~355)."""
    doy = t.dayofyear
    return 2 * np.pi * (doy - 355) / 365.0


def _duck_curve_profile(t: pd.DatetimeIndex) -> np.ndarray:
    """
    Duck curve: high morning (7–9), dip midday (11–15), high evening (17–21).
    Returns a multiplier (positive, ~1 on average).
    """
    h = _hour_of_day_rad(t)
    # Morning peak ~7h, evening peak ~19h, midday dip ~13h
    morning = 0.35 * np.cos(h - 2 * np.pi * 7 / 24)
    evening = 0.40 * np.cos(h - 2 * np.pi * 19 / 24)
    midday_dip = -0.30 * np.exp(-((t.hour - 13) ** 2) / 8.0)
    return 1.0 + morning + evening + midday_dip


def _seasonal_profile(t: pd.DatetimeIndex) -> np.ndarray:
    """
    Seasonal variation: higher in winter, lower in summer (Québec).
    Returns multiplier (positive, ~1 on average).
    """
    theta = _day_of_year_rad(t)
    return 1.0 + 0.25 * np.cos(theta)


def generate_synthetic_temporal(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    """
    Returns DataFrame with DatetimeIndex and columns total_electricity, total_gaz (kWh).
    One row per hour (or per day if pas_de_temps is daily).
    """
    start = pd.Timestamp(scenario.date_de_debut)
    end = pd.Timestamp(scenario.date_de_fin)
    pt = getattr(scenario, "pas_de_temps", None)
    if pt is not None and getattr(pt, "total_seconds", None):
        freq_sec = int(pt.total_seconds())
    else:
        freq_sec = 3600
    if freq_sec >= 86400:
        time_index = pd.date_range(start=start, end=end, freq="D")
    else:
        time_index = pd.date_range(start=start, end=end, freq="h")

    duck = np.maximum(_duck_curve_profile(time_index), 0.1)
    seasonal = _seasonal_profile(time_index)
    # Scale so annual sum ≈ BASE_ANNUAL_ENERGY_TWH (TWh) -> kWh
    raw = duck * seasonal
    total_kwh = raw.sum()
    target_kwh = BASE_ANNUAL_ENERGY_TWH * 1e9  # TWh -> kWh
    scale = target_kwh / max(total_kwh, 1.0)
    # ~70% electricity, ~30% gaz in total
    electricity = raw * scale * 0.70
    gaz = raw * scale * 0.30

    df = pd.DataFrame(
        index=time_index,
        data={
            "total_electricity": electricity,
            "total_gaz": gaz,
        },
    )
    df.index.name = "date"
    return df


def generate_synthetic_sankey(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    """
    Returns DataFrame with columns sector, total_electricity, total_gaz (kWh).
    """
    temporal = generate_synthetic_temporal(scenario, CUID)
    total_elec = temporal["total_electricity"].sum()
    total_gaz = temporal["total_gaz"].sum()
    elec_per_sector = total_elec * SECTOR_WEIGHTS
    gaz_per_sector = total_gaz * SECTOR_WEIGHTS
    return pd.DataFrame({
        "sector": SYNTHETIC_SECTORS,
        "total_electricity": elec_per_sector,
        "total_gaz": gaz_per_sector,
    })


def generate_synthetic_demande_data(
    scenario: Scenario,
    CUID: Optional[int] = None,
) -> pd.DataFrame:
    """
    Returns DataFrame with columns date, electricity, gaz, sector (kWh).
    One row per (date, sector) for compatibility with read_demande_data and load_demand_data.
    """
    temporal = generate_synthetic_temporal(scenario, CUID)
    rows = []
    for date, row in temporal.iterrows():
        for i, sector in enumerate(SYNTHETIC_SECTORS):
            w = SECTOR_WEIGHTS[i]
            rows.append({
                "date": date,
                "electricity": row["total_electricity"] * w,
                "gaz": row["total_gaz"] * w,
                "sector": sector,
            })
    return pd.DataFrame(rows)
