import pandas as pd

from utils import wrap_text


__all__ = [
    "circuit_names_wrapped",
    "circuit_names",
    "constructor_names",
    "driver_names",
]


circuits_df = pd.read_csv("./dataset/circuits.csv")
constructors_df = pd.read_csv("./dataset/constructors.csv")
drivers_df = pd.read_csv("./dataset/drivers.csv")
races_df = pd.read_csv("./dataset/races.csv")
results_df = pd.read_csv("./dataset/results.csv")

# Set for CIRCUITS
circuit_names_wrapped = {}
circuit_names = {}
for _, row in circuits_df.iterrows():
    circuit_names_wrapped[int(row["circuitId"])] = wrap_text(row["name"],
                                                             width=15)
    circuit_names[int(row["circuitId"])] = row["name"]

# Set for CONSTRUCTORS
constructor_names = {}
for _, row in constructors_df.iterrows():
    constructor_names[int(row["constructorId"])] = row["name"]

# Set for DRIVERS
driver_names = {}
for _, row in drivers_df.iterrows():
    if pd.notna(row["driverId"]):
        driver_id = int(row["driverId"])
        if "forename" in row and "surname" in row:
            # Format as "Surname, N."
            forename_initial = row['forename'][0] if row['forename'] else ""
            driver_names[driver_id] = (f"{row['surname']}, {forename_initial}."
                                       if forename_initial
                                       else row['surname'])
        else:
            driver_names[driver_id] = str(driver_id)
