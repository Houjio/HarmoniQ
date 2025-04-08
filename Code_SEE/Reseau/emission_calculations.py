# -*- coding: utf-8 -*-
"""
Created on Fri Feb  28 10:31:19 2025

@author: Jing Bo Zhang
"""

import pandas as pd
import csv

def load_energy_data(csv_file):
    """
    Load energy capacity and CO2 emission factors from a CSV file.

    :param csv_file: Path to the CSV file containing energy data.
    :type csv_file: str
    :return: Tuple of two dictionaries - energy capacities and CO2 emission factors.
    :rtype: tuple(dict, dict)
    """
    df = pd.read_csv(csv_file)
    energy_capacities = dict(zip(df["energy_source"], df["energy_capacities"]))
    co2_emission_factors = dict(zip(df["energy_source"], df["co2_emission_factors"]))
    return energy_capacities, co2_emission_factors

def load_parameters(csv_file):
    """
    Load global energy parameters from a CSV file.

    :param csv_file: Path to the CSV file containing parameters.
    :type csv_file: str
    :return: A tuple containing total energy consumed, length of power lines, transport percentage, and distribution percentage.
    :rtype: tuple(float, float, float, float)
    """
    df = pd.read_csv(csv_file)
    params = df.set_index("parameter")["value"].to_dict()
    return float(params["total_energy_consumed"]), float(params["length_km_total_qc"]), float(params["percent_transport"]), float(params["percent_distribution"])

def calculate_emission_for_energy_type(total_energy_consumed, energy_capacities, co2_emission_factors, target_energy_type):
    """
    Calculate CO2 emissions for a specific energy type.

    :param total_energy_consumed: Total energy consumption.
    :type total_energy_consumed: float
    :param energy_capacities: Dictionary mapping energy sources to their capacities.
    :type energy_capacities: dict
    :param co2_emission_factors: Dictionary mapping energy sources to their CO2 emission factors.
    :type co2_emission_factors: dict
    :param target_energy_type: The energy type to calculate emissions for.
    :type target_energy_type: str
    :return: CO2 emissions for the specified energy type.
    :rtype: float
    """
    total_capacity = sum(energy_capacities.values())
    energy_type_proportion = energy_capacities[target_energy_type] / total_capacity
    return total_energy_consumed * energy_type_proportion * co2_emission_factors[target_energy_type]

def calculate_transport_emissions(energy_co2, percent_transport, length_km_total_qc):
    """
    Calculate CO2 emissions related to energy transport.

    :param energy_co2: Dictionary of CO2 emissions per energy type.
    :type energy_co2: dict
    :param percent_transport: Percentage of energy-related emissions from transport.
    :type percent_transport: float
    :param length_km_total_qc: Total length of the power grid in kilometers.
    :type length_km_total_qc: float
    :return: CO2 emissions per km.
    :rtype: float
    """
    return sum((co2 * percent_transport) / length_km_total_qc for co2 in energy_co2.values())

def calculate_distribution_emissions(energy_co2, percent_distribution, total_energy_consumed):
    """
    Calculate CO2 emissions related to energy distribution.

    :param energy_co2: Dictionary of CO2 emissions per energy type.
    :type energy_co2: dict
    :param percent_distribution: Percentage of energy-related emissions from distribution.
    :type percent_distribution: float
    :param total_energy_consumed: Total energy consumption.
    :type total_energy_consumed: float
    :return: CO2 emissions per kWh.
    :rtype: float
    """
    return sum((co2 * percent_distribution) / total_energy_consumed for co2 in energy_co2.values())

def main():
    """
    Main function that loads data, calculates emissions, and prints results.
    """
    # Load energy data and parameters
    energy_capacities, co2_emission_factors = load_energy_data("energy_sources_updated.csv")
    total_energy_consumed, length_km_total_qc, percent_transport, percent_distribution = load_parameters("energy_parameters.csv")
    
    # Calculate CO2 emissions for each energy source
    energy_co2 = {et: calculate_emission_for_energy_type(total_energy_consumed, energy_capacities, co2_emission_factors, et) for et in energy_capacities.keys()}
    
    # Compute transport and distribution emissions
    transport_emissions = calculate_transport_emissions(energy_co2, percent_transport, length_km_total_qc)
    distribution_emissions = calculate_distribution_emissions(energy_co2, percent_distribution, total_energy_consumed)
    
    # Prepare output data for CSV without brackets (values as floats, not lists)
    results = {
        "CO2 emissions for transport (kg/km)": transport_emissions,
        "CO2 emissions for distribution (kg/kWh)": distribution_emissions,
        "Total CO2 Emission for Transport and Distribution (kg)": transport_emissions * length_km_total_qc + distribution_emissions * total_energy_consumed
    }
    
    # Print results
    print(f"CO2 emissions for transport (kg/km): {transport_emissions:.10f}")
    print(f"CO2 emissions for distribution (kg/kWh): {distribution_emissions:.10f}")
    print(f"Total CO2 Emission for Transport and Distribution: {transport_emissions * length_km_total_qc + distribution_emissions * total_energy_consumed:,.2f} kg")
    
    # Save the results to CSV
    with open("emissions_results.csv", mode="w", newline='') as file:
        writer = csv.DictWriter(file, fieldnames=results.keys())
        writer.writeheader()
        writer.writerow(results)  # Write a single row without brackets

# Run the script if executed as the main module
if __name__ == "__main__":
    main()
