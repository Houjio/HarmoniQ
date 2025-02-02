import pandas as pd
import numpy as np

# Number of hours in a year (365 days)
num_hours = 8760

# EPW file header
header = [
    "LOCATION,FakeCity,QC,CAN,45.5,-73.6,-5.0,20",
    "DESIGN CONDITIONS,1,Climate Design Data 2009 ASHRAE Handbook,,Heating,,-15,,Cooling,,30",
    "TYPICAL/EXTREME PERIODS,1,Summer Week,Summer,7/1,7/7",
    "GROUND TEMPERATURES,3,.5,,10.0,2.0,,10.5,4.0,,11.0",
    "HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0",
    "COMMENTS 1,Generated weather file for testing",
    "COMMENTS 2,No real data",
    "DATA PERIODS,1,1,Data,Sunday,1/1,12/31"
]

# Generate realistic mock data
# Create month and day arrays that properly correspond to calendar
months = []
days = []
for month in range(1, 13):
    days_in_month = pd.Period(f'2024-{month}').days_in_month
    months.extend([month] * (24 * days_in_month))
    for day in range(1, days_in_month + 1):
        days.extend([day] * 24)

data = {
    "Year": [2024] * num_hours,
    "Month": months[:num_hours],
    "Day": days[:num_hours],
    "Hour": list(range(1, 25)) * 365,
    "Minute": [0] * num_hours,
    "Data Source": [1] * num_hours,  # Added required field
    "Dry Bulb Temperature": np.random.uniform(-20, 35, num_hours),  # in °C
    "Dew Point Temperature": np.random.uniform(-25, 25, num_hours),  # in °C
    "Relative Humidity": np.random.uniform(10, 90, num_hours),
    "Atmospheric Pressure": np.random.uniform(98000, 102000, num_hours),
    "Horizontal Radiation": np.random.uniform(0, 800, num_hours),
    "Direct Normal Radiation": np.random.uniform(0, 900, num_hours),
    "Diffuse Horizontal Radiation": np.random.uniform(0, 400, num_hours),
    "Wind Speed": np.random.uniform(0, 10, num_hours),
    "Wind Direction": np.random.uniform(0, 360, num_hours),
    "Total Sky Cover": np.random.randint(0, 10, num_hours),
    "Opaque Sky Cover": np.random.randint(0, 10, num_hours),
    "Visibility": np.random.uniform(0, 20000, num_hours),
    "Ceiling Height": np.random.uniform(0, 3000, num_hours),
    "Present Weather Observation": [0] * num_hours,
    "Present Weather Codes": [0] * num_hours,
    "Precipitable Water": np.random.uniform(0, 50, num_hours),
    "Aerosol Optical Depth": np.random.uniform(0, 0.2, num_hours),
    "Snow Depth": [0] * num_hours,
    "Days Since Last Snowfall": [0] * num_hours,
    "Albedo": np.random.uniform(0.1, 0.9, num_hours),
    "Liquid Precipitation Depth": np.random.uniform(0, 10, num_hours),
    "Liquid Precipitation Quantity": np.random.uniform(0, 1, num_hours),
}

# Create DataFrame
df = pd.DataFrame(data)

# Format data for EPW - round numbers and convert to strings
def format_row(row):
    formatted = []
    for value in row:
        if isinstance(value, (int, np.integer)):
            formatted.append(f"{value}")
        elif isinstance(value, (float, np.floating)):
            formatted.append(f"{value:.3f}")
        else:
            formatted.append(str(value))
    return ",".join(formatted)

# Combine header and data
epw_data = header + [format_row(row) for _, row in df.iterrows()]

# Save EPW file
with open("fake_weather.epw", "w", encoding="utf-8") as f:
    f.write("\n".join(epw_data))

print("EPW file generated: fake_weather.epw")