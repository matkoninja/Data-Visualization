from dash import Input, Output, html, dcc
import pandas as pd
import plotly.express as px
from country import alpha2_codes
from math import ceil, floor
import numpy as np
from app import app


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
    return f"{minutes}:{seconds:06.3f}"


def format_lap_time_s(ms):
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    return f"{minutes}:{seconds:02d}"


def get_fastest_lap_times(circuits: pd.DataFrame,
                          races: pd.DataFrame,
                          lap_times: pd.DataFrame) -> pd.DataFrame:
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

    return fastest_per_circuit_year


def get_circuits_data():
    circuits = pd.read_csv(
        "./dataset/circuits.csv",
    )
    races = pd.read_csv(
        "./dataset/races.csv",
    )
    lap_times = pd.read_csv(
        "./dataset/lap_times.csv",
    )
    circuits_extras = pd.read_csv(
        "./dataset/circuits_extra.csv",
    )

    circuits_info = get_circuits_info(circuits, races, circuits_extras)
    fastest_lap_times = get_fastest_lap_times(circuits, races, lap_times)

    return circuits_info, fastest_lap_times


circuits, fastest_lap_times = get_circuits_data()


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


def draw_fastest_lap_times_line_chart(clickData):
    selected_circuit_ = (circuit_from_map_click(clickData)
                         if clickData is not None
                         else circuits.iloc[0])

    circuit_lap_times = fastest_lap_times[fastest_lap_times["circuitRef"]
                                          == selected_circuit_["circuitRef"]]
    times_with_format = circuit_lap_times[
        ["fastest_lap", "fastest_milliseconds"]
    ].sort_values(
        by="fastest_milliseconds",
    )
    fig = px.line(
        circuit_lap_times,
        x="year",
        y="fastest_milliseconds",
        # y="fastest_lap",
        title=f"Fastest Lap Times at {selected_circuit_['name']}",
        labels={
            "year": "Year",
            "fastest_milliseconds": "Fastest Lap Time"
        },
        # range_x=[1950, 2024],
        markers=True,
        category_orders={
            "fastest_lap": times_with_format["fastest_lap"].values.tolist()
        },
    )

    # fig.update_yaxes(autorange="reversed")

    min_time_raw = circuit_lap_times["fastest_milliseconds"].min()
    min_time = (floor(min_time_raw / 1000) * 1000
                if not np.isnan(min_time_raw) else 60_000)

    max_time_raw = circuit_lap_times["fastest_milliseconds"].max()
    max_time = (ceil(max_time_raw / 1000) * 1000
                if not np.isnan(max_time_raw) else 120_000)

    ticks_vals = np.arange(min_time, max_time + 1, 1000)
    ticks_texts = list(map(format_lap_time_s, ticks_vals))

    fig.update_layout(
        yaxis=dict(
            tickmode="array",
            tickvals=ticks_vals,
            ticktext=ticks_texts,
        )
    )

    return fig


app.callback(
    Output("circuits-lap-times", "figure"),
    Input("circuits-map", "clickData"),
)(draw_fastest_lap_times_line_chart)


def draw_circuits_map(clickData):
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
        title="Circuit Locations",
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        uirevision='keep-geo',
    )

    sizes = circuits["race_count"].fillna(0)
    sizeref = 2.0 * max(sizes) / (30 ** 2)

    fig.update_traces(
        hovertemplate=("<b>%{hovertext}</b><br>%{customdata[1]}, "
                       "%{customdata[0]}<br>Race Count: %{customdata[2]}"),
        marker=dict(
            sizemin=5,
            sizeref=sizeref,
            sizemode='area',
        ),
    )

    selected_circuit = circuit_index_from_map_click(clickData)

    if selected_circuit is not None:
        colors = ["#636efa"] * len(circuits)
        colors[selected_circuit] = "red"

        fig.update_traces(marker=dict(color=colors))

    return fig


app.callback(
    Output("circuits-map", "figure"),
    Input("circuits-map", "clickData"),
)(draw_circuits_map)


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
                        html.H2(
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
            }
        ),
        html.Div(
            [
                html.Span(
                    item,
                    style={
                        "color": "#fff",
                    },
                )
                for item
                in grid_items
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": "1fr 1fr",
                "gap": "0.5rem 1rem",
                "border": "1px solid #ccc",
            }
        )
    ]


DEFAULT_CIRCUIT_INFO = [
    "Select a circuit",
    "Click on a circuit on the map to see more information.",
    [],
]


def draw_circuit_info_children(clickData):
    if clickData is None:
        return _draw_circuit_info_children(*DEFAULT_CIRCUIT_INFO)

    row = circuit_from_map_click(clickData)

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
    Input("circuits-map", "clickData"),
)(draw_circuit_info_children)


layout = html.Div(
    [
        html.Div(
            [
                dcc.Graph(
                    figure=draw_circuits_map(None),
                    id="circuits-map",
                    style={
                        "flex": "1 1 0",
                        "border": "1px solid #ccc",
                    },
                ),
                html.Div(
                    None,
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
