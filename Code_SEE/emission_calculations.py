# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 10:31:19 2025

@author: Jing Bo Zhang
"""

# Total energy consumed in kWh
total_consumed_energy = 213301000000

# Installed capacities for each energy type (in kWh)
capacities = {
    "hydroelectricity": 35125000,  # Capacity of hydroelectricity
    "thermal": 704000,             # Capacity of thermal energy
    "other": 8063000               # Capacity of other energy sources
}

# CO2 emission factors for each energy type (in kg CO2 per kWh)
co2_factors = {
    "hydroelectricity": 0.017,  # CO2 factor for hydroelectricity
    "thermal": 0.8,             # CO2 factor for thermal energy
    "other": 0.005              # CO2 factor for other energy sources
}

def total_emission_per_energy_type(total_consumed_energy, capacities, co2_factors, energy_type):
    # Calculate the total capacity by summing all energy types' capacities
    total_capacity = sum(capacities.values())
    
    # Return the CO2 emissions for the specified energy type
    return total_consumed_energy * (capacities[energy_type] / total_capacity) * co2_factors[energy_type]

# CO2 emissions per type (in kg)
# Create a dictionary of CO2 emissions for each energy type by calling the function
energy_co2 = {energy_type: total_emission_per_energy_type(total_consumed_energy, capacities, co2_factors, energy_type)
              for energy_type in capacities.keys()}

# Print the table header
print(f"{'Energy Type':<15} {'CO2 Emission (kg)':<20}")
print("-" * 35)

# Print each row of the table
for energy_type, co2_emission in energy_co2.items():
    print(f"{energy_type:<15} {co2_emission:<20,.2f}")  # format to 2 decimal places

# Calculate total CO2 emissions for all energy
total_emission_all_energy = sum(energy_co2.values())
print(f"\nTotal CO2 Emission for All Energy: {total_emission_all_energy:,.2f} kg")

# The resulting 'energy_co2' dictionary contains the CO2 emissions for each energy type

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
    energy_types = ["hydroelectricity", "thermal", "other"]  # Use only the available energy types
    percent_transport = 0.08  # 8% for transport
    length_km_total_qc = 33911  # Total length of all transportation line in Quebec (in km)
    percent_distribution = 0.05  # 5% for distribution
    kwh_total_qc = total_consumed_energy  # Total kWh per year distributed in Quebec (in kWh)

    # Calculate emissions
    transport_emissions = calculate_transport_emissions(energy_types, percent_transport, length_km_total_qc)
    distribution_emissions = calculate_distribution_emissions(energy_types, percent_distribution, kwh_total_qc)

    # Print emissions for transport and distribution
    print(f"CO2 emissions for transport (kg/km): {transport_emissions:.10f}")
    print(f"CO2 emissions for distribution (kg/kWh): {distribution_emissions:.10f}")

    # Print total CO2 emissions for transport and distribution
    total_transport_distribution_emissions = transport_emissions + distribution_emissions
    print(f"Total CO2 Emission for Transport and Distribution: {total_transport_distribution_emissions:,.2f} kg")

# Call the main function to run the program
if __name__ == "__main__":
    main()
