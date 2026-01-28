from dash import html, dcc, Input, Output
import dash_daq as daq
import pandas as pd
import plotly.graph_objects as go

from app import app
from source import (
    circuit_names_wrapped,
    circuit_names,
    constructor_names,
    driver_names,
    results_df,
    races_df,
)
from teams import map_team, team_colors
from utils import rgba


"""
================================================================================
                Create circuit-constructor-driver finalists dataframe,
                grouped by count
================================================================================
"""
# ========= 1. circuit-constructor-driver dataframe ============


def get_parcats_data():
    # Use only Finalists
    results_finalists_df = results_df[results_df["position"] == 1].copy()

    # race -> circuits
    race_circuit = races_df[["raceId", "circuitId"]].copy().dropna()

    # race -> constructors, drivers
    race_constructor_driver = \
        results_finalists_df[["raceId",
                              "constructorId",
                              "driverId"]].copy().dropna().astype({
                                  "raceId": int,
                                  "constructorId": int,
                                  "driverId": int
                              })

    # Merge dataframes through races
    # to get circuit-constructor-driver relationships
    df_plot = pd.merge(
        race_constructor_driver,
        race_circuit,
        on="raceId",
        how="inner",
    ).dropna(subset=["circuitId", "constructorId", "driverId"]).astype({
        "circuitId": int,
        "constructorId": int,
        "driverId": int
    })

    # Calculate total number of values in the dataframe
    total_values = len(df_plot)

    # Add labels
    df_plot["Circuit"] = df_plot["circuitId"].map(circuit_names)
    df_plot["Circuit_labels"] = df_plot["circuitId"].map(circuit_names_wrapped)
    df_plot["Constructor"] = df_plot["constructorId"].map(constructor_names)
    df_plot["Driver"] = df_plot["driverId"].map(driver_names)
    df_plot["team_group"] = df_plot["Constructor"].apply(map_team)
    df_plot["color"] = df_plot["team_group"].map(team_colors)

    return df_plot, total_values


df_plot, total_values = get_parcats_data()


"""
================================================================================
                Dash Layout
================================================================================
"""

MAIN_DROPDOWN_STYLE = {
    "flex": "1",
}

layout = html.Div([
    html.H2(
        "Circuits → Constructors → Drivers (Winners Only)",
        style={"padding": "10px"}
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
                    "gap": "10px"
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
            "flex": "1",
            "margin": "10px"
        }
    )
],
    id="app-root",
    style={
        "height": "100vh",
        "display": "flex",
        "flex-direction": "column",
        "padding-top": "20px",
        "box-sizing": "border-box",
},
    **{"data-theme": "light"}
)

"""
================================================================================
                Callbacks + Updates
================================================================================
"""


COLOR_ALPHA = 0.6


def update_parcats(selected_circuits,
                   selected_constructors,
                   selected_drivers,
                   number_of_records,
                   do_sort,
                   sorting_column,
                   sorting_type,
                   sort_order_clicks):
    dff = df_plot.copy()

    # ---- FILTERING ----
    if selected_circuits:
        dff = dff[dff["Circuit"].isin(selected_circuits)]

    if selected_constructors:
        dff = dff[dff["Constructor"].isin(selected_constructors)]

    if selected_drivers:
        dff = dff[dff["driverId"].isin(selected_drivers)]

    # ---- SORTING ----
    sort_ascending = (sort_order_clicks % 2) == 0
    arrow_text = "↓" if sort_ascending else "↑"

    if do_sort:
        if sorting_type == "count":
            column_order = dff.groupby(sorting_column)[
                "count"].sum().sort_values(ascending=sort_ascending)
            dff[sorting_column] = pd.Categorical(
                dff[sorting_column],
                categories=column_order.index,
                ordered=True,
            )
            dff = dff.sort_values(by=sorting_column)
        else:
            dff = dff.sort_values(by=sorting_column, ascending=sort_ascending)

    dff["count"] = 1

    # ---- FIRST number_of_records RECORDS ----
    dff = dff.head(number_of_records)

    # =========================================================
    # SANKEY PREP
    # =========================================================

    # Aggregate flows
    c_to_c = (
        dff.groupby(["Circuit", "Constructor"])["count"]
        .sum()
        .reset_index()
    )

    c_to_d = (
        dff.groupby(["Constructor", "Driver"])["count"]
        .sum()
        .reset_index()
    )

    # Create node list
    nodes = pd.Index(
        pd.concat([
            c_to_c["Circuit"],
            c_to_c["Constructor"],
            c_to_d["Driver"],
        ]).unique()
    )

    node_index = {name: i for i, name in enumerate(nodes)}

    node_colors = (["#B0B0B0"
                    for _
                    in range(len(c_to_c["Circuit"].unique()))]
                   + [team_colors.get(map_team(name), "#B0B0B0")
                      for name
                      in c_to_c["Constructor"].unique()
                      ]
                   + ["#E0E0E0"
                      for _
                      in range(len(c_to_d["Driver"].unique()))])

    # Build links
    sources = []
    targets = []
    values = []
    hover = []
    line_colors = []

    # Circuit → Constructor
    for _, r in c_to_c.iterrows():
        sources.append(node_index[r["Circuit"]])
        targets.append(node_index[r["Constructor"]])
        values.append(r["count"])
        hover.append(f"<b>{r['Constructor']}</b> at <b>{r['Circuit']}</b>"
                     f"<br><b>{r['count']}</b> wins")
        color = team_colors.get(map_team(r["Constructor"]), "#B0B0B0")
        line_colors.append(rgba(color, COLOR_ALPHA))

    # Constructor → Driver
    for _, r in c_to_d.iterrows():
        sources.append(node_index[r["Constructor"]])
        targets.append(node_index[r["Driver"]])
        values.append(r["count"])
        hover.append(f"<b>{r['Driver']}</b> at <b>{r['Constructor']}</b>"
                     f"<br><b>{r['count']}</b> wins")
        color = team_colors.get(map_team(r["Constructor"]), "#B0B0B0")
        line_colors.append(rgba(color, COLOR_ALPHA))

    # =========================================================
    # SANKEY FIGURE
    # =========================================================

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                label=nodes.tolist(),
                pad=15,
                thickness=15,
                color=node_colors,
                line=dict(color="#15151E", width=0.5),
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "<b>%{value:d}</b> wins<extra></extra>"
                ),
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover,
                color=line_colors,
            ),
        )
    )

    fig.update_layout(
        margin=dict(t=50, l=50, r=50, b=50),
    )

    return fig, arrow_text


app.callback(
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
)(update_parcats)
