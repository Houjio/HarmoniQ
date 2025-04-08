import pandas as pd
import math
from collections import defaultdict

def calculate_substations(length_km, line_type, cost_params):
    if line_type not in cost_params:
        raise ValueError(f"Line type '{line_type}' not found in cost parameters.")
    km_per_substation = cost_params[line_type].get("Km_Per_Substation", None)
    if km_per_substation is None or pd.isna(km_per_substation):
        raise ValueError(f"Km_Per_Substation is missing or invalid for line type '{line_type}'.")
    return max(1, math.floor(length_km / km_per_substation))

def calculate_annual_cost(row, cost_params):
    construction_cost = (
        row["Num_Substations"] * cost_params[row["Line_Type"]]["Cost_Per_Substation"] +
        cost_params[row["Line_Type"]]["Other_Costs"]
    )
    return (construction_cost / cost_params[row["Line_Type"]]["Years_of_Operation"]) + \
           cost_params[row["Line_Type"]]["Maintenance_Cost_Per_Year"]

def group_line_segments(df):
    segment_graph = defaultdict(list)
    line_type_map = {}

    for _, row in df.iterrows():
        start = row['network_node_name_starting']
        end = row['network_node_name_ending']
        ltype = row['Line_Type']
        segment_graph[start].append((end, ltype))
        segment_graph[end].append((start, ltype))
        line_type_map[(start, end)] = ltype
        line_type_map[(end, start)] = ltype

    junctions = {node for node, connections in segment_graph.items() if len(connections) > 2}
    visited = set()
    line_groups = []

    def dfs(node, group, current_type):
        if node in visited or node in junctions:
            return
        visited.add(node)
        for neighbor, neighbor_type in segment_graph[node]:
            if neighbor not in visited and neighbor not in junctions:
                if neighbor_type != current_type:
                    group.append("Substation")
                group.append(neighbor)
                dfs(neighbor, group, neighbor_type)

    for start in df['network_node_name_starting']:
        if start not in visited:
            group = [start]
            first_type = df[df['network_node_name_starting'] == start]['Line_Type'].values[0]
            dfs(start, group, first_type)
            line_groups.append(group)

    return line_groups

def process_cost_data(segment_csv, cost_csv, output_csv):
    df_segments = pd.read_csv(segment_csv)
    df_costs = pd.read_csv(cost_csv)

    required_segment_cols = [
        "network_node_name_starting", "network_node_name_ending", 
        "line_segment_length_km", "current_type", "voltage"
    ]
    required_cost_cols = [
        "Line_Type", "Cost_Per_Substation", "Other_Costs", 
        "Years_of_Operation", "Maintenance_Cost_Per_Year", "Km_Per_Substation"
    ]

    if not all(col in df_segments.columns for col in required_segment_cols):
        print("Error: Missing required columns in segment CSV.")
        return
    if not all(col in df_costs.columns for col in required_cost_cols):
        print("Error: Missing required columns in cost parameter CSV.")
        return

    # Create a normalized Line_Type column for matching with cost_params
    df_segments["Line_Type"] = df_segments.apply(
        lambda row: f"{row['current_type'].upper()}{int(row['voltage'])}", axis=1
    )

    cost_params = df_costs.set_index("Line_Type").to_dict(orient="index")

    line_groups = group_line_segments(df_segments)

    results = []
    for group in line_groups:
        group_df = df_segments[
            df_segments['network_node_name_starting'].isin(group) |
            df_segments['network_node_name_ending'].isin(group)
        ]
        total_length = group_df['line_segment_length_km'].sum()
        first_type = group_df.iloc[0]["Line_Type"]
        num_substations = calculate_substations(total_length, first_type, cost_params)
        num_substations += group.count("Substation")

        if len(group_df["Line_Type"].unique()) > 1:
            print(f"Info: Multiple line types in group {group_df['Line_Type'].unique()}")

        results.append({
            "Line_ID": hash(frozenset(group)),
            "Total_Length_km": total_length,
            "Line_Type": first_type,
            "Num_Substations": num_substations,
            "Annual_Cost": calculate_annual_cost({
                "Num_Substations": num_substations,
                "Line_Type": first_type
            }, cost_params)
        })

    output_df = pd.DataFrame(results)
    output_df.to_csv(output_csv, index=False)
    print(f"Output saved as {output_csv}")

# Example usage
process_cost_data("lignes_quebec.csv", "cost_parameters.csv", "cost_results.csv")
