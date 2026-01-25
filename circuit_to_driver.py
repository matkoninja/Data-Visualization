import dash
from dash import Dash, html, dcc, Input, Output
import dash_daq as daq
import pandas as pd
import plotly.graph_objects as go
import os
import textwrap


"""
================================================================================
                Data import
================================================================================
"""

# Load CSVs from the local `dataset/` folder.
here = os.path.dirname(__file__)
data_dir = os.path.join(here, "dataset")

# Read datasets used to build the diagram
circuits_df = pd.read_csv(os.path.join(data_dir, "circuits.csv"), low_memory=False)
constructors_df = pd.read_csv(os.path.join(data_dir, "constructors.csv"), low_memory=False)
drivers_df = pd.read_csv(os.path.join(data_dir, "drivers.csv"), low_memory=False)
races_df = pd.read_csv(os.path.join(data_dir, "races.csv"), low_memory=False)
results_df = pd.read_csv(os.path.join(data_dir, "results.csv"), low_memory=False, na_values=["\\N"])


"""
================================================================================
                Create circuit-constructor-driver finalists dataframe, 
                grouped by count
================================================================================
"""
# ========= 1. circuit-constructor-driver dataframe ============

# Use only Finalists
results_finalists_df = results_df[results_df["position"] == 1]

# race -> circuits
race_circuit = races_df[["raceId", "circuitId"]].dropna()

# race -> constructors, drivers
race_constructor_driver = results_finalists_df[["raceId", "constructorId", "driverId"]].dropna().astype({
    "raceId": int,
    "constructorId": int,
    "driverId": int
})

# Merge dataframes through races to get circuit-constructor-driver relationships
circuit_constructor_driver = pd.merge(race_constructor_driver, race_circuit,  on="raceId", how="inner").dropna(subset=["circuitId", "constructorId", "driverId"]).astype({
    "circuitId": int,
    "constructorId": int,
    "driverId": int
})

# Count occurrences of each circuit-constructor-driver combination
circuit_constructor_driver_counts = circuit_constructor_driver.groupby(["circuitId", "constructorId", "driverId"]).size().reset_index(name="count")


"""
================================================================================
                Create sets for the labels
================================================================================
"""
# Set for CIRCUITS
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
    
# Set for CONSTRUCTORS
constructor_names = {}
for _, row in constructors_df[constructors_df["constructorId"].isin(circuit_constructor_driver_counts["constructorId"])].iterrows():
    constructor_names[int(row["constructorId"])] = row["name"]

# Set for DRIVERS
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
                Final dataframe - df_plot
================================================================================
"""

df_plot = circuit_constructor_driver_counts.copy()

# Calculate total number of values in the dataframe
total_values = df_plot["count"].sum()

# Add labels
df_plot["Circuit"] = df_plot["circuitId"].map(circuit_names_for_dropdown)
df_plot["Circuit_labels"] = df_plot["circuitId"].map(circuit_names)
df_plot["Constructor"] = df_plot["constructorId"].map(constructor_names)
df_plot["Driver"] = df_plot["driverId"].map(driver_names)

"""
================================================================================
                Dash Layout
================================================================================
"""

# Create Dash app
app = dash.Dash(__name__)


MAIN_DROPDOWN_STYLE = {
    "flex": "1",
}

app.layout = html.Div([
    html.H2(
        "Circuits → Constructors → Drivers (Winners Only)", 
        style={"padding": "10px"}
    ),

    html.Div(
        id="filter-row",
        children=[
            dcc.Dropdown(
                id="circuit-filter",
                options=[{"label": v, "value": v} for v in sorted(circuit_names_for_dropdown.values())],
                multi=True,
                placeholder="Select Circuits",
                closeOnSelect=False,
                style=MAIN_DROPDOWN_STYLE
            ),
            
            dcc.Dropdown(
                id="constructor-filter",
                options=[{"label": v, "value": v} for v in sorted(constructor_names.values())],
                multi=True,
                placeholder="Select Constructors",
                closeOnSelect=False,
                style=MAIN_DROPDOWN_STYLE
            ),
            
            dcc.Dropdown(
                id="driver-filter",
                options=[{"label": v, "value": v} for v in sorted(driver_names.values())],
                multi=True,
                placeholder="Select Drivers",
                closeOnSelect=False,
                style=MAIN_DROPDOWN_STYLE
            )
        ],
        style={
            "display": "flex",
            "gap":"10px",
            "padding": "10px",
        }
    ),
    
    html.Div(
        children=[
            html.Div(
                [
                daq.BooleanSwitch(
                    id="sort-enable",
                    on=False,
                    color="#FF1E00"
                ),

                html.Span("Sort all records by"),
                
                dcc.Dropdown(
                    id="sort-by-column",
                    options=[
                        {"label": "Circuits", "value": "Circuit"},
                        {"label": "Constructors", "value": "Constructor"},
                        {"label": "Drivers", "value": "Driver"},
                    ],
                    value="Circuit",
                    clearable=False,
                    style={"width": "150px"}
                ),
                
                html.Span("considering its"),

                dcc.Dropdown(
                    id="sort-by-parameter",
                    options=[
                        {"label": "name", "value": "name"},
                        {"label": "count", "value": "count"},
                    ],
                    value="name",
                    clearable=False,
                    style={"width": "150px"}
                ),

                html.Button(
                    "↓",
                    id="sort-order",
                    n_clicks=0,
                    className="control-button"
                )
            ],
            style={
                "flex": "0 0 50%",
                "display": "flex",
                "justify-content": "flex-start",
                "align-items": "center",
                "gap":"10px"
            }
        ),
        
        html.Div(
            [       
                dcc.Slider(
                    id='count-slider',
                    min=1, 
                    max=total_values, 
                    step=1, 
                    value=int(total_values/8), 
                    marks=None, 
                    tooltip={
                        "placement": "bottom", 
                        "always_visible": True, 
                        "template": "First {value} values"})
            ], 
            style={
                "flex": "0 0 50%",
                "width": "100%"}
        ),
        ],
        style={
                "display": "flex",
                "justify-content":  "space-between",
                "align-items": "center",
                "padding": "10px",
            }
    ),    
    
    dcc.Graph(
        id="parcats-graph",
        style={
            "height": "60vw", 
            "margin": "10px"
        }
    )
],
    id="app-root",
    **{"data-theme": "light"}
)

"""
================================================================================
                Callbacks + Updates
================================================================================
"""

@app.callback(
    # OUTPUTS
    Output("parcats-graph", "figure"),
    Output("sort-order", "children"),
    # INPUTS
    Input("circuit-filter", "value"),
    Input("constructor-filter", "value"),
    Input("driver-filter", "value"),
    Input("count-slider", "value"),
    Input("sort-enable", "on"),
    Input("sort-by-column", "value"),
    Input("sort-by-parameter", "value"),
    Input("sort-order", "n_clicks")
)

def update_parcats(selected_circuits, selected_constructors, selected_drivers, number_of_records, do_sort, sorting_column, sorting_type, sort_order_clicks):

    dff = df_plot.copy()
    
    # ---- FILTERING ----
    if selected_circuits:
        dff = dff[dff["Circuit"].isin(selected_circuits)]

    if selected_constructors:
        dff = dff[dff["Constructor"].isin(selected_constructors)]

    if selected_drivers:
        dff = dff[dff["Driver"].isin(selected_drivers)]
        
    # ---- SORTING ----
    sort_ascending = (sort_order_clicks % 2) == 0
    arrow_text = "↓" if sort_ascending else "↑"
        
    if do_sort:
        if sorting_type == "count": 
            column_order = dff.groupby(sorting_column)["count"].sum().sort_values(ascending=sort_ascending)
            dff[sorting_column] = pd.Categorical(dff[sorting_column], categories=column_order.index, ordered=True)
            dff = dff.sort_values(by=sorting_column)
        else:
            dff = dff.sort_values(by=sorting_column, ascending=sort_ascending)

    # ---- FIRST number_of_records RECORDS ----
    dff = dff.head(number_of_records)

    # ---- CREATING DIMENSIONS ----
    dimensions = [
        {
            "label": "Circuits",
            "values": dff["Circuit_labels"]
        },
        {
            "label": "Constructors",
            "values": dff["Constructor"]
        },
        {
            "label": "Drivers",
            "values": dff["Driver"]
        }
    ]

    # ---- CREATING PARALLEL CATEGORIES FIGURE ----
    fig = go.Figure(go.Parcats(
        dimensions=dimensions,
        arrangement="freeform",
        counts=dff["count"],
        line=dict(
            shape="hspline",
            color="#C4C4C4" 
        )
    ))

    fig.update_traces(
        labelfont=dict(size=16, color="#15151E"),
        tickfont=dict(size=11, color="#15151E")
    )

    fig.update_layout(
        margin=dict(t=50, l=50, r=50, b=50),
        
    )

    # ---- OUTPUT FIGURE & UPDATE BUTTON TEXT ----
    return fig, arrow_text


"""
================================================================================
                Run the app
================================================================================
"""

if __name__ == "__main__":
    app.run(debug=True)
