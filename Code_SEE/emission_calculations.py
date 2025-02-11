# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 10:31:19 2025

@author: Jing Bo Zhang
"""

# Energy total CO2 emissions per year (in kg)
energy_co2 = {
    "hydroelectricity_river": 5000,
    "hydroelectricity_reservoir": 5000,
    "solar": 500,
    "wind": 500,
    "fossil_fuel": 50000
}

def calculate_transport_emissions(energy_types, percent_transport, length_km_total_qc):
    # Calculate CO2 emissions for transport per km
    return sum(
        (energy_co2.get(energy_type, 0) * percent_transport) / length_km_total_qc
        for energy_type in energy_types
    )

def calculate_distribution_emissions(energy_types, percent_distribution, kwh_total_qc):
    # Calculate CO2 emissions for distribution per kWh
    return sum(
        (energy_co2.get(energy_type, 0) * percent_distribution) / kwh_total_qc
        for energy_type in energy_types
    )

def main():
    # Constants for the calculation
    energy_types = ["hydroelectricity_river", "hydroelectricity_reservoir", "solar", "wind", "fossil_fuel"]
    percent_transport = 0.08  # 8% for transport
    length_km_total_qc = 11422  # Total length of all transportation line in Quebec (in km)
    percent_distribution = 0.05  # 5% for distribution
    kwh_total_qc = 23000  # Total kWh per year distributed in Quebec (in kWh)

    # Calculate emissions
    transport_emissions = calculate_transport_emissions(energy_types, percent_transport, length_km_total_qc)
    distribution_emissions = calculate_distribution_emissions(energy_types, percent_distribution, kwh_total_qc)

    # Print emissions
    print(f"Total yearly CO2 emissions for transport (kg/km): {transport_emissions:.2f}")
    print(f"Total yearly CO2 emissions for distribution (kg/kWh): {distribution_emissions:.2f}")

# Call the main function to run the program
if __name__ == "__main__":
    main()
