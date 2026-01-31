from dash import Input, Output, State, callback_context, html, dcc, no_update
import pandas as pd
import plotly.express as px
from country import alpha2_codes
from math import ceil, floor
import numpy as np
from app import app
from source import (
    circuits_df,
    circuits_extras_df,
    lap_times_df,
    races_df,
    rule_changes_df,
)
from utils import Colors

def get_circuits_info(circuits, races, circuits_extras) -> pd.DataFrame:
    # Count number of races per circuitId
    races_by_circuit = races.groupby("circuitId")
    race_counts = races_by_circuit["raceId"].count().reset_index()
    race_counts.rename(columns={"raceId": "race_count"}, inplace=True)

    year_stats = races_by_circuit["year"].agg(min_year="min", max_year="max")

    # Merge into circuits dataframe
    circuits_with_counts = circuits.merge(race_counts,
                                          on="circuitId",
                                          how="left")
    circuits_with_counts = circuits_with_counts.merge(circuits_extras,
                                                      on="circuitId",
                                                      how="left")
    circuits_with_counts = circuits_with_counts.merge(year_stats,
                                                      on="circuitId",
                                                      how="left")

    # If you want missing circuits to show 0 instead of NaN:
    circuits_with_counts["race_count"] = \
        circuits_with_counts["race_count"].fillna(0).astype(int)

    seasons = \
        circuits_with_counts.apply(
            lambda row: ("0"
                         if (pd.isna(row["min_year"])
                             or pd.isna(row["max_year"]))
                         else f'{row["race_count"]} ({row["min_year"]})'
                         if row["min_year"] == row["max_year"]
                         else (f'{row["race_count"]} ({row["min_year"]} - '
                               + f'{row["max_year"]})')),
            axis=1
        )
    circuits_with_counts["seasons"] = seasons

    circuits_with_counts.set_index("circuitId", inplace=True)

    return circuits_with_counts


def format_lap_time_ms(ms):
    minutes = ms // 60000
    seconds = (ms % 60000) / 1000
    return f"{minutes:.0f}:{seconds:06.3f}"


def format_lap_time_s(ms):
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    return f"{minutes}:{seconds:02d}"


def get_fastest_lap_times(circuits: pd.DataFrame,
                          races: pd.DataFrame,
                          lap_times: pd.DataFrame,
                          rule_changes: pd.DataFrame) -> pd.DataFrame:
    # Merge circuits with races to attach circuit info to each race
    races_with_circuits = races.merge(
        circuits,
        on="circuitId",
        how="left",
        suffixes=("", "_circuit")
    )

    # Merge in the lap times
    full = lap_times.merge(
        races_with_circuits,
        on="raceId",
        how="left"
    )

    # Compute the fastest lap per circuit per season
    fastest_per_circuit_year = (
        full.groupby(["year", "circuitId", "circuitRef",
                     "name_circuit"], as_index=False)
        .agg(
            fastest_milliseconds=("milliseconds", "min")
        )
        .sort_values(["year", "circuitId"])
    )

    fastest_per_circuit_year["fastest_lap"] = \
        fastest_per_circuit_year["fastest_milliseconds"].apply(
            format_lap_time_ms
    )

    fastest_per_circuit_year = fastest_per_circuit_year.merge(
        rule_changes[["year", "impact", "label"]],
        on="year",
        how="left"
    )

    fastest_per_circuit_year["hovertext"] = fastest_per_circuit_year.apply(
        lambda row: (
            (f"({row['impact']}) {row['label']}<br />"
             f"<b>{row['fastest_lap']}</b>")
            if pd.notna(row["label"]) and pd.notna(row["impact"])
            else f"<b>{row['fastest_lap']}</b>"),
        axis=1,
    )

    return fastest_per_circuit_year


def transform_rule_changes(rule_changes: pd.DataFrame) -> pd.DataFrame:
    rule_changes["impact"] = rule_changes["impact"].apply(
        lambda x: x.capitalize() if pd.notna(x) else x
    )
    rule_changes = rule_changes[rule_changes["impact"] != "Low"]
    return rule_changes


def get_circuits_data():
    rule_changes = transform_rule_changes(rule_changes_df)
    circuits_info = get_circuits_info(circuits_df,
                                      races_df,
                                      circuits_extras_df)
    fastest_lap_times = get_fastest_lap_times(circuits_df,
                                              races_df,
                                              lap_times_df,
                                              rule_changes)

    return circuits_info, fastest_lap_times, rule_changes


circuits, fastest_lap_times, rule_changes = get_circuits_data()


selected_circuit = None


def circuit_index_from_map_click(clickData):
    if clickData is None:
        return None

    point = clickData["points"][0]
    row = circuits[circuits["name"] == point["hovertext"]].iloc[0]
    index = circuits.index.get_loc(row.name)
    return index


def circuit_from_map_click(clickData):
    index = circuit_index_from_map_click(clickData)
    if index is None:
        return None
    return circuits.iloc[index]


def draw_fastest_lap_times_line_chart(filterValue, season_filter=None):
    if (filterValue is None or len(filterValue) == 0):
        filterValue = []

    selected_circuits = (circuits[circuits["name"].isin(filterValue)]
                         if filterValue is not None and len(filterValue) > 0
                         else pd.DataFrame(columns=circuits.columns))
    if len(selected_circuits) == 0:
        if season_filter:
            circuit_lap_times = fastest_lap_times[
                (fastest_lap_times["year"] >= season_filter[0])
                & (fastest_lap_times["year"] <= season_filter[1])
            ]
        else:
            circuit_lap_times = fastest_lap_times

        circuit_lap_times = (circuit_lap_times
                             .groupby("year", as_index=False)
                             .agg(fastest_milliseconds=("fastest_milliseconds",
                                                        "mean"))
                             .sort_values("year"))
        circuit_lap_times["fastest_lap"] = \
            circuit_lap_times["fastest_milliseconds"].apply(
                format_lap_time_ms
        )

        circuit_lap_times = circuit_lap_times.merge(
            rule_changes[["year", "impact", "label"]],
            on="year",
            how="left"
        )

        circuit_lap_times["hovertext"] = circuit_lap_times.apply(
            lambda row: (
                (f"({row['impact']}) {row['label']}<br />"
                 f"<b>{row['fastest_lap']}</b>")
                if pd.notna(row["label"]) and pd.notna(row["impact"])
                else f"<b>{row['fastest_lap']}</b>"),
            axis=1,
        )
        first_circuit = None
    else:
        first_circuit = selected_circuits.iloc[0]["circuitRef"]

        lap_times_mask = (fastest_lap_times["circuitRef"]
                          .isin(selected_circuits["circuitRef"]))
        circuit_lap_times = fastest_lap_times[lap_times_mask]
        if season_filter:
            circuit_lap_times = circuit_lap_times[
                (circuit_lap_times["year"] >= season_filter[0])
                & (circuit_lap_times["year"] <= season_filter[1])
            ]

    times_with_format = circuit_lap_times[
        ["fastest_lap", "fastest_milliseconds"]
    ].sort_values(
        by="fastest_milliseconds",
    )
    fig = px.line(
        circuit_lap_times,
        x="year",
        y="fastest_milliseconds",
        color=("circuitRef" if len(selected_circuits) > 0 else None),
        title=("Fastest Lap Times at selected circuits"
               if len(selected_circuits) > 0
               else "Average Fastest Lap Times Across All Circuits"),
        labels={
            "year": "Year",
            "fastest_milliseconds": "Fastest Lap Time",
            "circuitRef": "Circuit",
        },
        markers=True,
        category_orders={
            "fastest_lap": times_with_format["fastest_lap"].values.tolist()
        },
        range_x=[circuit_lap_times["year"].min() - 1,
                 circuit_lap_times["year"].max() + 1],
        custom_data=["fastest_lap", "hovertext"],
    )

    min_time_raw = circuit_lap_times["fastest_milliseconds"].min()
    min_time = (floor(min_time_raw / 1000) * 1000
                if not np.isnan(min_time_raw) else 60_000)

    max_time_raw = circuit_lap_times["fastest_milliseconds"].max()
    max_time = (ceil(max_time_raw / 1000) * 1000
                if not np.isnan(max_time_raw) else 120_000)

    # Change the step value here (currently 1000 for 1 second)
    step_ms = 4000  # For 2-second intervals
    ticks_vals = np.arange(min_time, max_time + 1, step_ms)
    ticks_texts = list(map(format_lap_time_s, ticks_vals))

    for _, rule_change in rule_changes.iterrows():
        fig.add_vline(
            x=rule_change["year"],
            line_dash="dash",
            line_color=Colors.SECONDARY,
        )
    fig.update_layout(
        xaxis=dict(
            dtick=2,
            tick0=circuit_lap_times["year"].min()
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=ticks_vals,
            ticktext=ticks_texts,
        ),
        hovermode="x unified",
        font_family="Poppins",
        plot_bgcolor="#FFFFFF",
        title_font_color=Colors.BLACK,
        xaxis_title_font_color=Colors.SECONDARY,
        yaxis_title_font_color=Colors.SECONDARY,
        yaxis_tickfont_color=Colors.SECONDARY,
        xaxis_tickfont_color=Colors.SECONDARY,
        legend_font_color=Colors.SECONDARY,
        legend_title_font_color=Colors.BLACK,
        hoverlabel_font_color=Colors.SECONDARY,
    )
    
    if len(selected_circuits) == 0:
        fig.update_traces(line_color=Colors.BLACK)
        
    fig.update_traces(
        hovertemplate="%{customdata[1]}<br><extra></extra>",
    )

    if first_circuit is None:
        return fig

    fig.for_each_trace(
        lambda trace: trace.update(
            hovertemplate=("<b>%{customdata[0]}</b><br><extra></extra>"
                           if trace.name != first_circuit
                           else "%{customdata[1]}<br><extra></extra>"),
            name=selected_circuits[
                selected_circuits["circuitRef"] == trace.name
            ]["name"].values[0],
        )
    )

    return fig


app.callback(
    Output("circuits-lap-times", "figure"),
    Input("circuit-filter", "value"),
    Input("year-range-slider", "value")
)(draw_fastest_lap_times_line_chart)


def draw_circuits_map(clickData=None, filterValue=None, inContext=False):
    fig = px.scatter_geo(
        circuits,
        lat="lat",
        lon="lng",
        size="race_count",
        hover_name="name",
        hover_data={"country": False, "location": False,
                    "lat": False, "lng": False, "race_count": False,
                    "seasons": False},
        projection="natural earth",
        custom_data=["country", "location", "race_count"]
    )

    fig.update_geos(showcountries=True,
                    visible=False)

    fig.update_layout(
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        uirevision='keep-geo',
        font_family="Poppins",
    )

    sizes = circuits["race_count"].fillna(0)
    sizeref = 2.0 * max(sizes) / (30 ** 2)

    fig.update_traces(
        hovertemplate=("<b>%{hovertext}</b><br>%{customdata[1]}, "
                       "%{customdata[0]}<br>Race Count: %{customdata[2]}"),
        marker=dict(
            color=Colors.BLACK,
            sizemin=5,
            sizeref=sizeref,
            sizemode='area',
        ),
    )

    fig.update_geos(
        projection_scale=1,
        center=dict(lat=20, lon=0),
    )

    if not inContext:
        return fig

    ctx = callback_context
    if not ctx.triggered:
        return fig
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    colors = [Colors.BLACK] * len(circuits)

    if trigger == "circuits-map":
        selected_idx = circuit_index_from_map_click(clickData)
        if selected_idx is not None:
            colors[selected_idx] = Colors.PRIMARY
    elif (trigger == "circuit-filter"
          and filterValue is not None
          and len(filterValue) > 0):
        for value in filterValue:
            row = circuits[circuits["name"] == value].iloc[0]
            selected_idx = circuits.index.get_loc(row.name)
            if selected_idx is not None:
                colors[selected_idx] = Colors.PRIMARY
    else:
        return fig

    fig.update_traces(marker=dict(color=colors))

    return fig


app.callback(
    Output("circuits-map", "figure"),
    Input("circuit-filter", "value"),
)(lambda filterValue: draw_circuits_map(filterValue=filterValue,
                                        inContext=True))


def select_circuit_filter_from_map(clickData, filterValue):
    row = circuit_from_map_click(clickData)
    if row is None:
        return no_update

    circuit_name = row["name"]
    if filterValue is None:
        filterValue = []

    if circuit_name in filterValue:
        filterValue.remove(circuit_name)
        return filterValue
    return filterValue + [circuit_name]


app.callback(
    Output("circuit-filter", "value"),
    Input("circuits-map", "clickData"),
    State("circuit-filter", "value"),
)(select_circuit_filter_from_map)


def _draw_circuit_info_children(title: str,
                                subtitle: str,
                                info_items: list[tuple[str, str]],
                                country_code: str | None = None) -> list:
    grid_items = []
    for label, value in info_items:
        grid_items.append(label)
        grid_items.append(value)

    return [
        html.Div(
            [
                html.Div(
                    [
                        html.H3(
                            title,
                            className="circuit-info_title",

                        ),
                        html.Span(
                            subtitle,
                            className="circuit-info_subtitle",
                        ),
                    ],
                    className="circuit-info_header",
                ),
                *([] if country_code is None else [
                    html.Img(
                        src=("https://flagsapi.com"
                             + f"/{country_code.upper()}"
                             + "/flat/64.png"),
                        className="circuit-info_flag",
                    )])
            ],
            className="circuit-info_top",
            style={
                "justifyContent": ("space-between"
                                   if country_code
                                   else "flex-start"),
                
                "color": "var(--text-secondary)",
            }
        ),
        html.Div(
            [
                html.Span(
                    item,
                    className="circuit-info_text"
                )
                for item
                in grid_items
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "0.5rem 1rem",
            }
        )
    ]


DEFAULT_CIRCUIT_INFO = [
    "Select a circuit",
    "Click on a circuit on the map to see more information.",
    [],
]


def draw_circuit_info_children(filterValue):
    row = (None
           if filterValue is None or len(filterValue) == 0
           else circuits[circuits["name"] == filterValue[-1]].iloc[0])

    if row is None:
        return _draw_circuit_info_children(*DEFAULT_CIRCUIT_INFO)
    return _draw_circuit_info_children(
        row["name"],
        f"{row['location']}, {row['country']}",
        [
            ("Length", f"{row['length']} km"),
            ("# of Laps", f"{row['laps']}"),
            ("Race Distance", f"{row['distance']} km"),
            ("# of Turns", f"{row['turns']}"),
            ("# of DRS Zones", f"{row['drs']}"),
            ("Fastest Lap", f"{row['fastest_lap']}"),
            ("Fastest Race Lap", f"{row['fastest_race_lap']}"),
            ("Seasons", f"{row['seasons']}"),
        ],
        alpha2_codes.get(row["country"])
    )


app.callback(
    Output("circuit-info", "children"),
    Input("circuit-filter", "value"),
)(draw_circuit_info_children)


layout = html.Div(
    [   
        html.H1("Circuit Locations"),
        html.Div(
            [
                dcc.Graph(
                    figure=draw_circuits_map(),
                    id="circuits-map",
                    className="circuits-map",
                    style={"width": "100%", "height": "100%"},
                    config={"responsive": True},
                ),
                html.Div(
                    _draw_circuit_info_children(*DEFAULT_CIRCUIT_INFO),
                    id="circuit-info",
                    className="circuit-info_container",
                ),
            ],
            className="circuits-map-info_container",
        ),
        dcc.Graph(
            figure=draw_fastest_lap_times_line_chart(None),
            id="circuits-lap-times",
        )
    ],
    className="circuits-lap-times-container",
)
