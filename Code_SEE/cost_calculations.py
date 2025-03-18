import pandas as pd
import math
from collections import defaultdict

def calculate_substations(length_km):
    """
    @brief Calculates the number of substations needed for a given transmission line length.
    
    @param length_km The total length of the transmission line in kilometers.
    @return int The number of substations (minimum 1, calculated as floor(length_km / 150)).
    """
    return max(1, math.floor(length_km / 150))

def calculate_annual_cost(row, cost_params):
    """
    @brief Calculates the annual cost of a transmission line project.

    @param row A dictionary containing calculated transmission line data.
    @param cost_params A dictionary mapping line types to cost parameters.
    @return float The total annual cost (construction cost divided by years of operation plus maintenance cost per year).
    """
    construction_cost = (row["Num_Substations"] * cost_params[row["Line_Type"]]["Cost_Per_Substation"]) + cost_params[row["Line_Type"]]["Other_Costs"]
    return (construction_cost / cost_params[row["Line_Type"]]["Years_of_Operation"]) + cost_params[row["Line_Type"]]["Maintenance_Cost_Per_Year"]

def group_line_segments(df):
    """
    @brief Groups connected line segments into single transmission lines unless a junction or a line type change occurs.

    @param df A Pandas DataFrame containing segment data with start and end coordinates.
    @return list A list of grouped line segments, each representing a single transmission line.
    """
    segment_graph = defaultdict(list)
    line_type_map = {}

    for _, row in df.iterrows():
        segment_graph[row['Start_Coordinates']].append((row['End_Coordinates'], row['Line_Type']))
        segment_graph[row['End_Coordinates']].append((row['Start_Coordinates'], row['Line_Type']))
        line_type_map[(row['Start_Coordinates'], row['End_Coordinates'])] = row['Line_Type']
        line_type_map[(row['End_Coordinates'], row['Start_Coordinates'])] = row['Line_Type']

    junctions = {node for node, connections in segment_graph.items() if len(connections) > 2}

    visited = set()
    line_groups = []

    def dfs(node, group, current_type):
        """
        @brief Depth-first search to traverse the connected segments while considering line type changes.

        @param node The current node being visited.
        @param group The current group of connected nodes.
        @param current_type The type of the transmission line currently being traversed.
        """
        if node in visited or node in junctions:
            return
        visited.add(node)
        for neighbor, neighbor_type in segment_graph[node]:
            if neighbor not in visited and neighbor not in junctions:
                if neighbor_type != current_type:
                    group.append("Substation")
                group.append(neighbor)
                dfs(neighbor, group, neighbor_type)

    for start in df['Start_Coordinates']:
        if start not in visited:
            group = [start]
            first_type = df[df['Start_Coordinates'] == start]['Line_Type'].values[0]
            dfs(start, group, first_type)
            line_groups.append(group)

    return line_groups

def process_cost_data(segment_csv, cost_csv, output_csv):
    """
    @brief Processes transmission line cost data by grouping connected segments and calculating costs.

    @param segment_csv The input CSV file containing transmission line segment data.
    @param cost_csv The input CSV file containing cost parameters for different line types.
    @param output_csv The output CSV file where the calculated results will be saved.
    
    @return None
    """
    df_segments = pd.read_csv(segment_csv)
    df_costs = pd.read_csv(cost_csv)

    required_segment_cols = ["Start_Coordinates", "End_Coordinates", "Length_km", "Line_Type"]
    required_cost_cols = ["Line_Type", "Cost_Per_Substation", "Other_Costs", "Years_of_Operation", "Maintenance_Cost_Per_Year"]

    if not all(col in df_segments.columns for col in required_segment_cols):
        print("Error: Missing required columns in segment CSV.")
        return
    if not all(col in df_costs.columns for col in required_cost_cols):
        print("Error: Missing required columns in cost parameter CSV.")
        return

    df_segments['Start_Coordinates'] = df_segments['Start_Coordinates'].astype(str)
    df_segments['End_Coordinates'] = df_segments['End_Coordinates'].astype(str)

    cost_params = df_costs.set_index("Line_Type").to_dict(orient="index")
    
    line_groups = group_line_segments(df_segments)

    results = []
    for group in line_groups:
        group_df = df_segments[df_segments['Start_Coordinates'].isin(group) | df_segments['End_Coordinates'].isin(group)]
        total_length = group_df['Length_km'].sum()
        num_substations = calculate_substations(total_length)
        num_substations += group.count("Substation")

        line_types = group_df['Line_Type'].unique()
        if len(line_types) > 1:
            print(f"Info: Multiple line types detected in a group {line_types}. Added substations between them.")
        
        sample_row = group_df.iloc[0]

        results.append({
            "Line_ID": hash(frozenset(group)),
            "Total_Length_km": total_length,
            "Line_Type": sample_row["Line_Type"],
            "Num_Substations": num_substations,
            "Annual_Cost": calculate_annual_cost({
                "Num_Substations": num_substations,
                "Line_Type": sample_row["Line_Type"]
            }, cost_params)
        })

    output_df = pd.DataFrame(results)
    output_df.to_csv(output_csv, index=False)
    print(f"Output saved as {output_csv}")

# Example usage
process_cost_data("line_segments.csv", "cost_parameters.csv", "cost_results.csv")
