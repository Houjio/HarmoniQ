# -*- coding: utf-8 -*-
"""
Created on Fri Feb  28 10:31:19 2025

@author: Jing Bo Zhang
"""

import pandas as pd
import math

def calculate_substations(length_km):
    """
    @brief Calculates the number of substations for a given line length.
    
    @param length_km The length of the transmission line in kilometers.
    
    @return The number of substations (minimum 1, calculated as floor(Length_km / 150)).
    """
    return max(1, math.floor(length_km / 150))

def calculate_annual_cost(row):
    """
    @brief Calculates the annual cost of a transmission line project.
    
    @param row A Pandas DataFrame row containing the required cost parameters.
    
    @return The total annual cost (construction cost split over years of operation).
    """
    construction_cost = (row["Num_Substations"] * row["Cost_Per_Substation"]) + row["Other_Costs"]
    return (construction_cost / row["Years_of_Operation"]) + row["Maintenance_Cost_Per_Year"]

def process_cost_data(input_csv, output_csv):
    """
    @brief Processes transmission line cost data and saves the results to a CSV file.

    @param input_csv The input CSV file containing transmission line data.
    @param output_csv The output CSV file to store calculated results.

    @return None
    """
    # Load CSV file
    df = pd.read_csv(input_csv)

    # Calculate number of substations
    df["Num_Substations"] = df["Length_km"].apply(calculate_substations)

    # Calculate annual cost
    df["Annual_Cost"] = df.apply(calculate_annual_cost, axis=1)

    # Select only necessary columns for the output CSV
    output_df = df[["Length_km", "Line_Type", "Num_Substations", "Annual_Cost"]]

    # Save the results to a new CSV file
    output_df.to_csv(output_csv, index=False)

    print(f"Output saved as {output_csv}")

# Run the function with specified file names
process_cost_data("cost_parameters.csv", "cost_results.csv")
