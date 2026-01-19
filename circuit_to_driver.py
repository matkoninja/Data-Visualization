import dash
from dash import Dash, html, dcc, Input, Output
import pandas as pd
import plotly.graph_objects as go
import os
import textwrap

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
                Building connections between categories

1. circuits -> constructors
2. constructors -> drivers
================================================================================
"""

# Prepare data for parallel categories diagram
dimensions = []

# Use only Finalists
results_finalists_df = results_df[results_df["position"] == 1]

# Prepare dataframe for circuit-constructor-driver relationships
race_circuit = races_df[["raceId", "circuitId"]].dropna()
race_constructor_driver = results_finalists_df[["raceId", "constructorId", "driverId"]].dropna().astype({
    "raceId": int,
    "constructorId": int,
    "driverId": int
})

# Merge to get circuit-constructor-driver relationships through races
circuit_constructor_driver = pd.merge(race_constructor_driver, race_circuit,  on="raceId", how="inner")
circuit_constructor_driver = circuit_constructor_driver.dropna(subset=["circuitId", "constructorId", "driverId"]).astype({
    "circuitId": int,
    "constructorId": int,
    "driverId": int
})
# print(circuit_constructor_driver.head())

# Count occurrences of each circuit-constructor-driver combination
circuit_constructor_driver_counts = circuit_constructor_driver.groupby(["circuitId", "constructorId", "driverId"]).size().reset_index(name="count")
# print(circuit_constructor_driver_counts.head())
# print("dgdfgdfgdfgdfg")


# ==========

# Create mapping for circuit names
def wrap_text(text, width=15):
    """Wrap text to specified width, breaking on spaces when possible"""
    if pd.isna(text) or not isinstance(text, str):
        return str(text)
    return '<br>'.join(textwrap.wrap(text, width=width)) # Use HTML line breaks for Plotly

circuit_names = {}
circuit_names_for_dropdown = {}
for _, row in circuits_df[circuits_df["circuitId"].isin(circuit_constructor_driver_counts["circuitId"])].iterrows():
    circuit_names[int(row["circuitId"])] = wrap_text(row["name"], width=15)
    circuit_names_for_dropdown[int(row["circuitId"])] = row["name"]
    
# Create mapping for constructor names
constructor_names = {}
for _, row in constructors_df[constructors_df["constructorId"].isin(circuit_constructor_driver_counts["constructorId"])].iterrows():
    constructor_names[int(row["constructorId"])] = row["name"]

# Create mapping for driver names
driver_names = {}
for _, row in drivers_df[drivers_df["driverId"].isin(circuit_constructor_driver_counts["driverId"])].iterrows():
    if pd.notna(row["driverId"]):
        driver_id = int(row["driverId"])
        if "forename" in row and "surname" in row:
            # Format as "Surname, N."
            forename_initial = row['forename'][0] if row['forename'] else ""
            driver_names[driver_id] = f"{row['surname']}, {forename_initial}." if forename_initial else row['surname']
        else:
            driver_names[driver_id] = str(driver_id)



"""
================================================================================
                Dash App

Layout and callbacks
================================================================================
"""

# Create Dash app
app = dash.Dash(__name__)

ITEM_STYLE = {
    "flex": "0 0 33.333%",
    "padding": "10px",
    "boxSizing": "border-box"
}

# Layout
app.layout = html.Div([
    html.H2("Circuits → Constructors → Drivers (Winners Only)"),

    html.Div(
        id="filter-row",
        children=[
            dcc.Dropdown(
                id="circuit-filter",
                options=[{"label": v, "value": v} for v in sorted(circuit_names_for_dropdown.values())],
                multi=True,
                placeholder="Select Circuits",
                closeOnSelect=False,
                style=ITEM_STYLE
            ),
            
            dcc.Dropdown(
                id="constructor-filter",
                options=[{"label": v, "value": v} for v in sorted(constructor_names.values())],
                multi=True,
                placeholder="Select Constructors",
                closeOnSelect=False,
                style=ITEM_STYLE
            ),
            
            dcc.Dropdown(
                id="driver-filter",
                options=[{"label": v, "value": v} for v in sorted(driver_names.values())],
                multi=True,
                placeholder="Select Drivers",
                closeOnSelect=False,
                style=ITEM_STYLE
            ),
            
            html.Div(
                [
                    html.Span("Sorting:", style={"margin-right": "15px"}),
                    dcc.RadioItems(
                        id="sort-toggle-circuits",
                        options=[
                            {"label": "None", "value": 0},
                            {"label": "By Name", "value": 1},
                            {"label": "By Count", "value": 2}
                        ],
                        value=0,  # Default is None
                        inline=True,
                        labelStyle={"padding": "5px"},
                        inputStyle={"margin-right": "5px"}
                    )
                ], 
                style=ITEM_STYLE
            ),

            html.Div(
                [
                    html.Span("Sorting:", style={"margin-right": "15px"}),
                    dcc.RadioItems(
                        id="sort-toggle-constructors",
                        options=[
                            {"label": "None", "value": 0},
                            {"label": "By Name", "value": 1},
                            {"label": "By Count", "value": 2}
                        ],
                        value=0,  # Default is None
                        inline=True,
                        labelStyle={"padding": "5px"},
                        inputStyle={"margin-right": "5px"}
                    )
                ], 
                style=ITEM_STYLE
            ),

            html.Div(
                [
                    html.Span("Sorting:", style={"margin-right": "15px"}),
                    dcc.RadioItems(
                        id="sort-toggle-drivers",
                        options=[
                            {"label": "None", "value": 0},
                            {"label": "By Name", "value": 1},
                            {"label": "By Count", "value": 2}
                        ],
                        value=0,  # Default is None
                        inline=True,
                        labelStyle={"padding": "5px"},
                        inputStyle={"margin-right": "5px"}
                    )
                ], 
                style=ITEM_STYLE
            )
        ],
        style={
            "display": "flex",
            "flexWrap": "wrap",     # allow wrapping
            "width": "100%"
        }
    ),
    
    html.Div(
        [
            html.Span("Maximum number of items per attribute:", style={"margin-right": "15px"}),
            dcc.RadioItems(
                id="limit-items-toggle",
                options=[
                    {"label": "all items", "value": 0},
                    {"label": "50", "value": 50},
                    {"label": "25", "value": 25},
                    {"label": "10", "value": 10},
                    {"label": "5", "value": 5}
                ],
                value=0,  # Default to all items
                inline=True,
                labelStyle={"padding": "5px"},
                inputStyle={"margin-right": "5px"}
            )
        ], 
        style={
            "display": "flex", 
            "align-items": "center", 
            "margin": "10px"
        }
    ),

    
    
    dcc.Graph(
        id="parcats-graph",
        style={
            "height": "60vw", 
            "margin": "10px"
        }
    )
])

df_plot = circuit_constructor_driver_counts.copy()

df_plot["Circuit"] = df_plot["circuitId"].map(circuit_names_for_dropdown)
df_plot["Constructor"] = df_plot["constructorId"].map(constructor_names)
df_plot["Driver"] = df_plot["driverId"].map(driver_names)


# callbacks
@app.callback(
    Output("parcats-graph", "figure"),
    Input("circuit-filter", "value"),
    Input("constructor-filter", "value"),
    Input("driver-filter", "value"),
    Input("limit-items-toggle", "value"),
    Input("sort-toggle-circuits", "value"),
    Input("sort-toggle-constructors", "value"),
    Input("sort-toggle-drivers", "value")
)

def update_parcats(selected_circuits, selected_constructors, selected_drivers, limit_value, sort_circuits, sort_constructors, sort_drivers):

    dff = df_plot.copy()
    
    if selected_circuits:
        dff = dff[dff["Circuit"].isin(selected_circuits)]

    if selected_constructors:
        dff = dff[dff["Constructor"].isin(selected_constructors)]

    if selected_drivers:
        dff = dff[dff["Driver"].isin(selected_drivers)]

    if limit_value:
        # Limit to top N items per category based on radio selection
        top_circuits = dff.groupby("Circuit")["count"].sum().nlargest(limit_value).index
        top_constructors = dff.groupby("Constructor")["count"].sum().nlargest(limit_value).index
        top_drivers = dff.groupby("Driver")["count"].sum().nlargest(limit_value).index

        dff = dff[
            dff["Circuit"].isin(top_circuits) &
            dff["Constructor"].isin(top_constructors) &
            dff["Driver"].isin(top_drivers)
        ]
        
    # Sorting
    if sort_circuits == 1:
        dff = dff.sort_values(by="Circuit")
        
    if sort_circuits == 2:
        circuit_counts = dff.groupby("Circuit")["count"].sum().sort_values(ascending=False)
        dff["Circuit"] = pd.Categorical(dff["Circuit"], categories=circuit_counts.index, ordered=True)
        dff = dff.sort_values("Circuit")
    
    if sort_constructors == 1:
        dff = dff.sort_values(by="Constructor")
        
    if sort_constructors == 2:
        constructor_counts = dff.groupby("Constructor")["count"].sum().sort_values(ascending=False)
        dff["Constructor"] = pd.Categorical(dff["Constructor"], categories=constructor_counts.index, ordered=True)
        dff = dff.sort_values("Constructor")
        
    if sort_drivers == 1:
        dff = dff.sort_values(by="Driver")
        
    if sort_drivers == 2:
        driver_counts = dff.groupby("Driver")["count"].sum().sort_values(ascending=False)
        dff["Driver"] = pd.Categorical(dff["Driver"], categories=driver_counts.index, ordered=True)
        dff = dff.sort_values("Driver")


    dimensions = []
    for attr in ["Circuits", "Constructors", "Drivers"]:
        dimensions.append({
            "label": attr,
            "values": dff[attr[:-1]]  # Circuits → Circuit, etc.
        })
    
    fig = go.Figure(go.Parcats(
        dimensions=dimensions,
        counts=dff["count"],
        line={"shape": "hspline"}
    ))

    fig.update_traces(
        labelfont=dict(size=13),
        tickfont=dict(size=11)
    )

    fig.update_layout(
        font_size=12,
        margin=dict(t=50, l=50, r=50, b=50)
    )
    return fig


# run the App
if __name__ == "__main__":
    app.run(debug=True)
