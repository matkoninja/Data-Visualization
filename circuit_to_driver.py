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

# Read datasets used to build the Sankey
circuits_df = pd.read_csv(os.path.join(data_dir, "circuits.csv"), low_memory=False)
constructors_df = pd.read_csv(os.path.join(data_dir, "constructors.csv"), low_memory=False)
drivers_df = pd.read_csv(os.path.join(data_dir, "drivers.csv"), low_memory=False)
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
2. Offset node indices (in the Sankey diagram)
"""


offset_circuits = 0
offset_constructors = circuits_count
offset_drivers = offset_constructors + drivers_count

"""
3. create a mappings between dataframe IDs and their corresponding node indices
"""
circuit_id_to_sankey_index = {}
for position, circuitId in enumerate(circuits_df.get("circuitId", pd.Series())):
    if pd.notna(circuitId):
        circuit_id_to_sankey_index[int(circuitId)] = offset_circuits + position

constructor_id_to_sankey_index = {}
for position, constructorId in enumerate(constructors_df.get("constructorId", pd.Series())):
    if pd.notna(constructorId):
        constructor_id_to_sankey_index[int(constructorId)] = offset_constructors + position

driver_id_to_sankey_index = {}
for position, driverId in enumerate(drivers_df.get("driverId", pd.Series())):
    if pd.notna(driverId):
        driver_id_to_sankey_index[int(driverId)] = offset_drivers + position


"""
================================================================================
                Building links between nodes

1. circuits -> constructors
2. constructors -> drivers
================================================================================
"""

sources = []
targets = []
values = []

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

# loop over circuit-constructor pair and their count
for _, row in circuit_constructor_counts.iterrows():
    circuit_id = int(row["circuitId"])
    constructor_id = int(row["constructorId"])
    circuit_constructor_count = int(row["count"])
    # Look up the node indices in the Sankey for each circuit and constructor
    src = circuit_id_to_sankey_index.get(circuit_id)
    tgt = constructor_id_to_sankey_index.get(constructor_id)
    if ((src is not None) and (tgt is not None)):
      # Add the source node index, target node index, and count value to the respective arrays
      sources.append(src)
      targets.append(tgt)
      values.append(circuit_constructor_count)


""" 
2. constructors -> drivers
"""
# prepare dataframe ()
constructor_driver = results_df[["constructorId", "driverId"]].dropna().astype({"constructorId": int, "driverId": int}) # Extracts constructor-driver pairs directly from results_df
constructor_driver_counts = constructor_driver.groupby(["constructorId", "driverId"]).size().reset_index(name="count") # Groups by constructor-driver pairs and counts occurrences (how many times each driver raced for each constructor)
print(constructor_driver_counts.head())

# loop over constructor-driver pair and their count
for _, row in constructor_driver_counts.iterrows():
    constructor_id = int(row["constructorId"])
    driver_id = int(row["driverId"])
    constructor_driver_count = int(row["count"])
    # Look up the node indices in the Sankey for each circuit and constructor
    src = constructor_id_to_sankey_index.get(constructor_id)
    tgt = driver_id_to_sankey_index.get(driver_id)
    if ((src is not None) and (tgt is not None)):
      # Add the source node index, target node index, and count value to the respective arrays
      sources.append(src)
      targets.append(tgt)
      values.append(circuit_constructor_count)


"""
================================================================================
                Sankey visualization

Preparation of `node` and `link` dicts and calling `go.Sankey`.
If `showSimple` is True -> keep only the first `max_nodes` encountered in links.
================================================================================
"""

# Combined labels and layout positions
labels = circuits_labels + constructors_labels + drivers_labels

"""
1. Node Positioning
"""
# x positions: circuits=0, constructors=0.5, drivers=1.0
xs = [0.0] * circuits_count + [0.5] * constructors_count + [1.0] * drivers_count

# y positions: distribute nodes vertically within each column
def even_ys(count):
    if count <= 1:
        return [0.5]
    return [i / (count - 1) for i in range(count)]

ys = even_ys(circuits_count) + even_ys(constructors_count) + even_ys(drivers_count)

"""
2. Elements of the Sankey
"""
# Nodes
colors = (["#1f77b4"] * circuits_count) + (["#ff7f0e"] * constructors_count) + (["#2ca02c"] * drivers_count)

node_dict = dict(
  pad=15, 
  thickness=20, 
  line=dict(color="black", width=0.5), 
  label=labels, 
  color=colors,
  align='left')

# Links
link_dict = dict(
  source=sources, 
  target=targets, 
  value=values)

"""
3. rendering the figure
"""
fig = go.Figure(data=[go.Sankey(
  node=node_dict, 
  link=link_dict
  )])

fig.update_layout(title_text="Circuits → Constructors → Drivers Sankey", font_size=10)
fig.show()