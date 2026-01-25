import dash
from dash import Dash, html, dcc, Input, Output
import dash_daq as daq
import pandas as pd
import plotly.graph_objects as go
import os
import textwrap
import plotly.io as pio

# """
# ================================================================================
#                 Setting colors
# ================================================================================
# """

pio.templates["dash_theme"] = go.layout.Template(
    layout=dict(
        paper_bgcolor="var(--bg-main)",
        plot_bgcolor="var(--bg-main)",
        font=dict(color="var(--text-primary)"),
        colorway=[
            "var(--primary)",     # first trace
            "var(--secondary)"
        ]
    )
)

pio.templates.default = "dash_theme"

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


MAIN_DROPDOWN_STYLE = {
    "flex": "1",
}

# Layout
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
                    tooltip={"placement": "bottom", "always_visible": True, "template": "First {value} values"})
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
    **{"data-theme": "light"}  # 👈 THIS LINE
)



df_plot["Circuit"] = df_plot["circuitId"].map(circuit_names_for_dropdown)
df_plot["Circuit_labels"] = df_plot["circuitId"].map(circuit_names)
df_plot["Constructor"] = df_plot["constructorId"].map(constructor_names)
df_plot["Driver"] = df_plot["driverId"].map(driver_names)


# callbacks
@app.callback(
    Output("parcats-graph", "figure"),
    Output("sort-order", "children"),
    Input("parcats-graph", "clickData"),
    Input("circuit-filter", "value"),
    Input("constructor-filter", "value"),
    Input("driver-filter", "value"),
    Input("count-slider", "value"),
    Input("sort-enable", "on"),
    Input("sort-by-column", "value"),
    Input("sort-by-parameter", "value"),
    Input("sort-order", "n_clicks")
)

def update_parcats(clickData, selected_circuits, selected_constructors, selected_drivers, number_of_records, do_sort, sorting_column, sorting_type, sort_order_clicks):

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

    # Build dimensions
    dimensions = []
    dimensions.append({
            "label": "Circuits",
            "values": dff["Circuit_labels"]
        })
    for attr in ["Constructors", "Drivers"]:
        dimensions.append({
            "label": attr,
            "values": dff[attr[:-1]]
        })

    # Build Parcats figure
    # Normalize counts to 0–1 for the colorscale
    # line_color = (dff["count"] - dff["count"].min()) / (dff["count"].max() - dff["count"].min())
    # line_color = line_color.fillna(0)  # just in case
    # colorscale = [
    #     [0, "#15151E"],  # low count → dark
    #     [1, "#FF1E00"]   # high count → red
    # ]

    fig = go.Figure(go.Parcats(
        dimensions=dimensions,
        arrangement="freeform",
        counts=dff["count"],
        line=dict(
            shape="hspline",
            color="#C4C4C4"  # 👈 REQUIRED
        )
    ))

    fig.update_traces(
        labelfont=dict(size=13),
        tickfont=dict(size=11)
    )

    fig.update_layout(
        # paper_bgcolor="#0F1117",  # outer area
        # plot_bgcolor="#0F1117",   # plotting area
        # font_color="#EAEAEA",
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    # Arrow toggle
    arrow_text = "↑" if sort_order_clicks % 2 else "↓"
    
    return fig, arrow_text


# run the App
if __name__ == "__main__":
    app.run(debug=True)
