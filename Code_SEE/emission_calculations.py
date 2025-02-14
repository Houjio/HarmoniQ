# -*- coding: utf-8 -*-
"""
Created on Fri Feb  7 10:31:19 2025

@author: Jing Bo Zhang
"""

# Total energy consumed in kWh for a given year (2012)
total_energy_consumed = 213301000000

# Installed capacities for each energy type (in kWh) for a given year (2012)
energy_capacities = {
    "hydr_res": 35125000+5428000,  
    "hydr_rrun": 0,
    "therm_gaz": 573000,       
    "therm_oil": 131000,
    "biomass": 114000,
    "solar": 0,
    "wind":1349000,
    "other": 1149000+23000
}

# CO2 emission factors for each energy type (in kg CO2 per kWh)
co2_emission_factors = {
    "hydr_res": 0.017,  
    "hydr_rrun": 0.006,
    "therm_gaz": 0.62,           
    "therm_oil": 0.878,
    "biomass": 0.088,
    "solar": 0.064,
    "wind": 0.014,
    "other": 0    
}

def calculate_emission_for_energy_type(total_energy_consumed, energy_capacities, co2_emission_factors, target_energy_type):
    # Step 1: Calculate the total energy capacity by summing up all individual energy type capacities
    total_capacity = sum(energy_capacities.values())
    
    # Step 2: Calculate the proportion of energy consumed by the specific energy type
    energy_type_proportion = energy_capacities[target_energy_type] / total_capacity
    
    # Step 3: Calculate and return the total CO2 emissions for the specified energy type
    emission = total_energy_consumed * energy_type_proportion * co2_emission_factors[target_energy_type]
    
    return emission

# CO2 emissions per type (in kg)
# Create a dictionary of CO2 emissions for each energy type by calling the function
energy_co2 = {energy_type: calculate_emission_for_energy_type(total_energy_consumed, energy_capacities, co2_emission_factors, energy_type)
              for energy_type in energy_capacities.keys()}

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
    # Initialize total CO2 emissions for transport
    total_transport_emissions = 0
    
    # Iterate over each energy type and calculate the emissions for transport per km
    for energy_type in energy_types:
        energy_co2_value = energy_co2.get(energy_type, 0)  # Get CO2 value for the energy type
        transport_emission = (energy_co2_value * percent_transport) / length_km_total_qc
        total_transport_emissions += transport_emission
    
    return total_transport_emissions

def calculate_distribution_emissions(energy_types, percent_distribution, kwh_total_qc):
    # Initialize total CO2 emissions for distribution
    total_distribution_emissions = 0
    
    # Iterate over each energy type and calculate the emissions for distribution per kWh
    for energy_type in energy_types:
        energy_co2_value = energy_co2.get(energy_type, 0)  # Get CO2 value for the energy type
        distribution_emission = (energy_co2_value * percent_distribution) / kwh_total_qc
        total_distribution_emissions += distribution_emission
    
    return total_distribution_emissions

def main():
    # Constants for the calculation
    energy_types = [
        "hydr_res",
        "hydr_rrun",
        "therm_gaz",
        "therm_oil",
        "biomass",
        "solar",
        "wind"
    ]
    percent_transport = 0.008  # 0.8% for transport each kwh
    length_km_total_qc = 33911  # Total length of all transportation line in Quebec (in km)
    percent_distribution = 0.005  # 0.5% for distribution each kwh
    kwh_total_qc = total_energy_consumed  # Total kWh per year distributed in Quebec (in kWh)

    # Calculate emissions
    transport_emissions = calculate_transport_emissions(energy_types, percent_transport, length_km_total_qc)
    distribution_emissions = calculate_distribution_emissions(energy_types, percent_distribution, kwh_total_qc)

    # Print emissions for transport and distribution
    print(f"CO2 emissions for transport (kg/km): {transport_emissions:.10f}")
    print(f"CO2 emissions for distribution (kg/kWh): {distribution_emissions:.10f}")

    # Print total CO2 emissions for transport and distribution
    total_transport_distribution_emissions = transport_emissions*length_km_total_qc + distribution_emissions*total_energy_consumed
    print(f"Total CO2 Emission for Transport and Distribution: {total_transport_distribution_emissions:,.2f} kg")

# Call the main function to run the program
if __name__ == "__main__":
    main()
