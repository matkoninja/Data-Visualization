from dash import html
import pandas as pd
import plotly.graph_objects as go
import os

"""
================================================================================
                Module loading and data import
================================================================================
"""

# Load CSVs from the local `dataset/` folder.
here = os.path.dirname(__file__)
data_dir = os.path.join(here, "dataset")

# Toggle simplified view: when True, naively limit nodes to `max_nodes`
showSimple = False
max_nodes = 50

# New switch to limit values for better fit
showSmallDf = True
valuesLimit = 100

# Read datasets used to build the diagram
circuits_df = pd.read_csv(os.path.join(data_dir, "circuits.csv"), low_memory=False)
constructors_df = pd.read_csv(os.path.join(data_dir, "constructors.csv"), low_memory=False)
drivers_df = pd.read_csv(os.path.join(data_dir, "drivers.csv"), low_memory=False, nrows=1000)  # Limit rows for performance
races_df = pd.read_csv(os.path.join(data_dir, "races.csv"), low_memory=False)
results_df = pd.read_csv(os.path.join(data_dir, "results.csv"), low_memory=False, na_values=["\\N"])

# View first 5 rows of each DataFrame
# print("Circuits DataFrame:")
# print(circuits_df.head())
# print("\nConstructors DataFrame:")
# print(constructors_df.head())
# print("\nDrivers DataFrame:")
# print(drivers_df.head())
# print("\nRaces DataFrame:")
# print(races_df.head())
# print("\nResults DataFrame:")
# print(results_df.head())


"""
================================================================================
                Variable preprocessing
                
1. Labels + Labels count
2. Node index offsets
3. Indices mappings
================================================================================
"""

"""
1. Labels for each group and their count
"""
# circuits
circuits_labels = circuits_df["name"].fillna(circuits_df.get("circuitRef", "")).astype(str).tolist()
# constructors
constructors_labels = constructors_df["name"].fillna(constructors_df.get("constructorRef", "")).astype(str).tolist()
# drivers (if columns are missing, use empty Series of correct length)
if "forename" in drivers_df.columns:
    forenames = drivers_df["forename"]
else:
    forenames = pd.Series([""] * len(drivers_df))

if "surname" in drivers_df.columns:
    surnames = drivers_df["surname"]
else:
    surnames = pd.Series([""] * len(drivers_df))
drivers_labels = (forenames.fillna("") + " " + surnames.fillna("")).str.strip().replace(r"\s+", " ", regex=True).tolist()
# print(circuits_labels, constructors_labels, drivers_labels)

# count of circuits, constructors and drivers
circuits_count = len(circuits_labels)
constructors_count = len(constructors_labels)
drivers_count = len(drivers_labels)

"""
2. Offset node indices (in the parallel diagram)
"""


offset_circuits = 0
offset_constructors = circuits_count
offset_drivers = offset_constructors + drivers_count

"""
3. create a mappings between dataframe IDs and their corresponding node indices
"""
circuit_id_to_index = {}
for position, circuitId in enumerate(circuits_df.get("circuitId", pd.Series())):
    if pd.notna(circuitId):
        circuit_id_to_index[int(circuitId)] = offset_circuits + position

constructor_id_to_index = {}
for position, constructorId in enumerate(constructors_df.get("constructorId", pd.Series())):
    if pd.notna(constructorId):
        constructor_id_to_index[int(constructorId)] = offset_constructors + position

driver_id_to_index = {}
for position, driverId in enumerate(drivers_df.get("driverId", pd.Series())):
    if pd.notna(driverId):
        driver_id_to_index[int(driverId)] = offset_drivers + position


"""
================================================================================
                Building connections between categories

1. circuits -> constructors
2. constructors -> drivers
================================================================================
"""

# Prepare data for parallel categories diagram
dimensions = []

""" 
1. circuits -> constructors 
"""
# prepare dataframe (circuit_constructor_values):
race_circuit = races_df[["raceId", "circuitId"]].dropna() # race-circuit mappings from races_df
race_constructor = results_df[["raceId", "constructorId"]].dropna() # race-constructor mappings from results_df
circuit_constructor = pd.merge(race_constructor, race_circuit, on="raceId", how="left") # Joins these two datasets on raceId to connect circuits directly to constructors
circuit_constructor = circuit_constructor.dropna(subset=["circuitId", "constructorId"]).astype({"circuitId": int, "constructorId": int})
circuit_constructor_counts = circuit_constructor.groupby(["circuitId", "constructorId"]).size().reset_index(name="count") # Groups by circuit-constructor pairs and counts occurrences (how many times each constructor raced at each circuit)
# print(circuit_constructor_counts.head())

# Create mapping for circuit names
circuit_names = {}
for _, row in circuits_df.iterrows():
    circuit_names[int(row["circuitId"])] = row["name"]

# Create mapping for constructor names
constructor_names = {}
for _, row in constructors_df.iterrows():
    constructor_names[int(row["constructorId"])] = row["name"]

# Prepare data for parallel categories diagram
circuit_list = []
constructor_list = []
count_list = []

for _, row in circuit_constructor_counts.iterrows():
    circuit_id = int(row["circuitId"])
    constructor_id = int(row["constructorId"])
    count = int(row["count"])
    
    if circuit_id in circuit_names and constructor_id in constructor_names:
        circuit_list.append(circuit_names[circuit_id])
        constructor_list.append(constructor_names[constructor_id])
        count_list.append(count)

""" 
2. constructors -> drivers
"""
# prepare dataframe ()
constructor_driver = results_df[["constructorId", "driverId"]].dropna().astype({"constructorId": int, "driverId": int}) # Extracts constructor-driver pairs directly from results_df
constructor_driver_counts = constructor_driver.groupby(["constructorId", "driverId"]).size().reset_index(name="count") # Groups by constructor-driver pairs and counts occurrences (how many times each driver raced for each constructor)
print(constructor_driver_counts.head())

# Create mapping for driver names
driver_names = {}
for _, row in drivers_df.iterrows():
    if pd.notna(row["driverId"]):
        driver_id = int(row["driverId"])
        if "forename" in row and "surname" in row:
            driver_names[driver_id] = f"{row['forename']} {row['surname']}"
        else:
            driver_names[driver_id] = str(driver_id)

# Extend data for parallel categories diagram
constructor_list_extended = []
driver_list = []
count_list_extended = []

# For simplicity, we'll create a separate diagram for constructors -> drivers
# In a full implementation, we would link these together

for _, row in constructor_driver_counts.iterrows():
    constructor_id = int(row["constructorId"])
    driver_id = int(row["driverId"])
    count = int(row["count"])
    
    if constructor_id in constructor_names and driver_id in driver_names:
        constructor_list_extended.append(constructor_names[constructor_id])
        driver_list.append(driver_names[driver_id])
        count_list_extended.append(count)

"""
================================================================================
                Parallel Categories visualization

Preparation of dimensions for `go.Parcats`.
================================================================================
"""

# Create a combined dataset that links all three categories
# We need to find connections that go from circuits -> constructors -> drivers
# But only for race winners (position = 1)

# First, let's create a combined dataframe that links races to circuits, constructors, and drivers
# But only for winners (position = 1)
race_circuit = races_df[["raceId", "circuitId"]].dropna()
race_constructor_driver = results_df[["raceId", "constructorId", "driverId", "position"]].dropna().astype({
    "raceId": int, 
    "constructorId": int, 
    "driverId": int,
    "position": int
})

# Filter only for race winners (position = 1)
race_constructor_driver_winners = race_constructor_driver[race_constructor_driver["position"] == 1]

# Merge to get circuit-constructor-driver relationships through races for winners only
circuit_constructor_driver = pd.merge(race_circuit, race_constructor_driver_winners, on="raceId", how="inner")
circuit_constructor_driver = circuit_constructor_driver.dropna(subset=["circuitId", "constructorId", "driverId"]).astype({
    "circuitId": int, 
    "constructorId": int, 
    "driverId": int
})

# Count occurrences of each circuit-constructor-driver combination (winners only)
circuit_constructor_driver_counts = circuit_constructor_driver.groupby(["circuitId", "constructorId", "driverId"]).size().reset_index(name="count")

# Prepare lists for the combined diagram
combined_circuit_list = []
combined_constructor_list = []
combined_driver_list = []
combined_count_list = []

# Populate the lists with names instead of IDs
for _, row in circuit_constructor_driver_counts.iterrows():
    circuit_id = int(row["circuitId"])
    constructor_id = int(row["constructorId"])
    driver_id = int(row["driverId"])
    count = int(row["count"])
    
    # Only add to lists if all IDs exist in our mappings
    if (circuit_id in circuit_names and 
        constructor_id in constructor_names and 
        driver_id in driver_names):
        combined_circuit_list.append(circuit_names[circuit_id])
        combined_constructor_list.append(constructor_names[constructor_id])
        combined_driver_list.append(driver_names[driver_id])
        combined_count_list.append(count)

# Apply limit if showSmallDf is True
if showSmallDf:
    # Limit the number of entries for each category
    combined_circuit_list = combined_circuit_list[:valuesLimit]
    combined_constructor_list = combined_constructor_list[:valuesLimit]
    combined_driver_list = combined_driver_list[:valuesLimit]
    combined_count_list = combined_count_list[:valuesLimit]

# Create the combined parallel categories diagram with all three categories
# Using the basic structure with counts and curved lines as requested
fig_combined = go.Figure(go.Parcats(
    dimensions=[
        {'label': 'Circuits', 'values': combined_circuit_list},
        {'label': 'Constructors', 'values': combined_constructor_list},
        {'label': 'Drivers', 'values': combined_driver_list}
    ],
    counts=combined_count_list,
    line={'shape': 'hspline'}  # Add curved lines between nodes
))

fig_combined.update_layout(
    title_text="Circuits → Constructors → Drivers Combined Parallel Categories Diagram (Winners Only)", 
    font_size=12,
    height=None,  # Reduced height since we're limiting values
    width=None,   # Reduced width since we're limiting values
    margin=dict(t=50, b=50, l=100, r=100)  # Adjusted margins
)

fig_combined.show()
