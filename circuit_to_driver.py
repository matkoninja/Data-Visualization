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

# dataframe to be used
df_plot = circuit_constructor_driver_counts.copy()

# Calculate total number of values in the dataframe
total_values = df_plot["count"].sum()


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
            dcc.Checklist(
                id="sort-enable",
                options=[{"label": "", "value": 1}],
                value=[],
                style={"margin-right": "10px"}
            ),

            html.Span("Sort all by ", style={"margin-right": "8px"}),
            
            dcc.Dropdown(
                id="sort-by-column",
                options=[
                    {"label": "Circuits", "value": "Circuit"},
                    {"label": "Constructors", "value": "Constructor"},
                    {"label": "Drivers", "value": "Driver"},
                ],
                value="Circuit",
                clearable=False,
                style={"width": "120px", "margin-right": "10px"}
            ),
            
            html.Span(" considering its ", style={"margin-right": "8px"}),

            dcc.Dropdown(
                id="sort-by-parameter",
                options=[
                    {"label": "name", "value": "name"},
                    {"label": "count", "value": "count"},
                ],
                value="name",
                clearable=False,
                style={"width": "120px", "margin-right": "10px"}
            ),

            html.Button(
                "↓",
                id="sort-order",
                n_clicks=0,
                style={"width": "40px"}
            )
        ],
        style={
            "display": "flex",
            "align-items": "center",
            "padding": "10px"
        }
    ),
    
    html.Div(
        [
            # html.Span("Number of records to be shown:", style={"margin-right": "15px"}),
           
            html.Div([
                dcc.Slider(min=1, max=total_values, step=1, value=int(total_values/3), id='count-slider', marks=None, tooltip={"placement": "bottom", "always_visible": True, "template": "First {value} values"})
            ])
        ], 
        # style={
        #     "display": "flex", 
        #     "align-items": "center", 
        #     "margin": "10px"
        # }
    ),

    
    
    dcc.Graph(
        id="parcats-graph",
        style={
            "height": "60vw", 
            "margin": "10px"
        }
    )
])



df_plot["Circuit"] = df_plot["circuitId"].map(circuit_names_for_dropdown)
df_plot["Constructor"] = df_plot["constructorId"].map(constructor_names)
df_plot["Driver"] = df_plot["driverId"].map(driver_names)


# callbacks
@app.callback(
    Output("parcats-graph", "figure"),
    Output("sort-order", "children"),
    Input("circuit-filter", "value"),
    Input("constructor-filter", "value"),
    Input("driver-filter", "value"),
    Input("count-slider", "value"),
    Input("sort-enable", "value"),
    Input("sort-by-column", "value"),
    Input("sort-by-parameter", "value"),
    Input("sort-order", "n_clicks")
)

def update_parcats(selected_circuits, selected_constructors, selected_drivers, number_of_records, do_sort, sorting_column, sorting_type, sort_order_clicks):

    dff = df_plot.copy()
    
    if selected_circuits:
        dff = dff[dff["Circuit"].isin(selected_circuits)]

    if selected_constructors:
        dff = dff[dff["Constructor"].isin(selected_constructors)]

    if selected_drivers:
        dff = dff[dff["Driver"].isin(selected_drivers)]
        
    # Sorting
    sort_ascending = (sort_order_clicks % 2) == 0
    if do_sort:
        if sorting_type == "count": 
            column_order = dff.groupby(sorting_column)["count"].sum().sort_values(ascending=sort_ascending)
            dff[sorting_column] = pd.Categorical(dff[sorting_column], categories=column_order.index, ordered=True)
            dff = dff.sort_values(by=sorting_column)
        else: # sorting_type == "name"
            dff = dff.sort_values(by=sorting_column, ascending=sort_ascending)

    # constrain the dataset to show first number_of_records records
    dff = dff.head(number_of_records)
    
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
    
    # Arrow toggle
    arrow_text = "↑" if sort_order_clicks % 2 else "↓"
    
    return fig, arrow_text


# run the App
if __name__ == "__main__":
    app.run(debug=True)
