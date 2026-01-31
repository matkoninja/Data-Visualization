import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from dash import dcc, html, Input, Output, State
from app import app
from circuit_map import layout as circuit_map_layout
from scatter_plot_drivers import (
    create_career_timeline,
    create_career_plot,
    get_career_data,
    get_driver_data,
)
from driver_card import create_driver_card
from circuit_to_driver import layout as circuit_to_driver_layout
from source import circuit_names, constructor_names, driver_names


MAIN_DROPDOWN_STYLE = {
    "flex": "1",
    "background-color": "#f9f9f9",
}


def display_driver_card(clickData):
    if not clickData:
        return html.Div([
            html.Span("Click on a driver point to view details"),
            html.Button(id="show-career-timeline",
                        style={"display": "none"})],
            className="card-placeholder"), None
    try:
        point = clickData['points'][0]
        driver_id = point['customdata'][0]
        driver_data = career[career['driverId'] == driver_id].iloc[0]
        tmp_driver_data = get_driver_data(driver_id)
        driver_url = (tmp_driver_data['url']
                      if not tmp_driver_data.empty
                      else "")
        return create_driver_card(driver_data, driver_url), driver_id
    except (IndexError, KeyError, AttributeError):
        return html.Div("Driver data not found", className="card-error"), None


app.callback(
    Output("driver-card", "children"),
    Output("driver-id-storage", "data"),
    Input("driver-careers-chart", "clickData")
)(display_driver_card)


app.layout = html.Div([
    html.Div(
        [
            # Filters container
            html.Div([
                # Season (Year) range slider
                html.Div([
                    dcc.RangeSlider(min=1950,
                                    max=2025,
                                    step=1,
                                    marks={year: str(year)
                                           for year
                                           in range(1950, 2026, 5)},
                                    tooltip=dict(
                                        placement="bottom",
                                        always_visible=True,
                                        style=dict(
                                            fontSize="16px",
                                        ),
                                    ),
                                    id='year-range-slider'),
                ], style={
                    "width": "100%",
                    "padding": "0 1rem",
                }),

                # Dropdown Filters: Circuit, Constructor, Driver
                html.Div(
                    id="filter-row",
                    children=[
                        # Circuit
                        dcc.Dropdown(
                            id="circuit-filter",
                            options=[{"label": v, "value": v}
                                     for v
                                     in sorted(circuit_names.values())],
                            multi=True,
                            placeholder="Select Circuits",
                            closeOnSelect=False,
                            style=MAIN_DROPDOWN_STYLE
                        ),

                        # Constructor
                        dcc.Dropdown(
                            id="constructor-filter",
                            options=[{"label": v, "value": v}
                                     for v
                                     in sorted(constructor_names.values())],
                            multi=True,
                            placeholder="Select Constructors",
                            closeOnSelect=False,
                            style=MAIN_DROPDOWN_STYLE
                        ),

                        # Driver
                        dcc.Dropdown(
                            id="driver-filter",
                            options=[
                                {"label": v, "value": k}
                                for k, v
                                in sorted(driver_names.items(),
                                          key=lambda item: item[1])
                            ],
                            multi=True,
                            placeholder="Select Drivers",
                            closeOnSelect=False,
                            style=MAIN_DROPDOWN_STYLE
                        )
                    ],
                    style={
                        "display": "flex",
                        "gap": "10px",
                        "padding": "10px",
                        "width": "100%",
                    }
                ),
            ], style={
                "width": "100%",
                "display": "flex",
                "flex-direction": "column",
                "align-items": "center",
                "gap-y": "0.5rem",
            }, id="filters-container"),
            
                # Collapse/Expand button
            html.Div(
                [
                    html.Button(
                        "Collapse",
                        id="filters-button",
                        style={
                            "font-size": "16px",
                            
                            "border-radius": "8px",
                            "border": "0",
                            "background-color": "var(--bg-main)",
                            "cursor": "pointer",
                        },
                    ),
                    dcc.Store(id="filters-collapsed"),
                ],
                style={
                    "height": "2rem",
                    "display": "flex",
                    "align-items": "center",
                    "justify-content": "center",
                },
            ),
        ],
        style={
            "width": "60%",
            "margin": "0 auto",
            "position": "sticky",
            "top": "0",
            "background-color": "white",
            "z-index": "100",
            "border-radius": "0 0 1rem 1rem",
            "border": "1px solid #cccccc",
            "box-shadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
            "display": "flex",
            "flex-direction": "column",
            "align-items": "center",
            "gap-y": "0.5rem",
        },
    ),

    # Top row: Map + Circuit Info
    circuit_map_layout,

    html.Div([
        dcc.Store(id='driver-id-storage'),
        html.Div([
            html.H3('Chart view:', className="driver-name"),
            dcc.RadioItems(
                id='career-mode',
                options=['start', 'end', 'both'],
                value='start',
                className="toggle-switch"
            )
        ], className="sidebar"),
        html.Div([
            dcc.Graph(
                figure=create_career_plot(),
                id="driver-careers-chart",
                className="main-chart"
            ),
            html.Div(
                display_driver_card(None),
                id="driver-card",
                className="driver-card"
            )
        ], className="chart-card-wrapper")
    ], className="bottom-container"),

    html.Div([
        html.Div([
            html.H3("Career Timeline", className="timeline-title"),
            html.P(("Click 'Show Career Timeline' on a driver card "
                    "to view their complete career progression"),
                   className="timeline-instruction",
                   id="timeline-instruction",
                   style={
                       'text-align': 'center',
                       'color': 'gray',
                       'font-style': 'italic',
            }),
            dcc.Graph(
                id="career-timeline-chart",
                style={'display': 'none'},
                className="career-timeline"
            )
        ], className="timeline-container",
            style={
            'margin-top': '30px',
            'display': 'flex',
            'width': '100%',
            'padding': '0 80px 80px 80px',
            'min-height': '50px',
            'flex-direction': 'column'
        })
    ], className="timeline-row"),

    circuit_to_driver_layout,
], className="dashboard-container")


@app.callback(
    Output("filters-collapsed", "data"),
    Output("filters-container", "style"),
    Output("filters-button", "children"),
    Input("filters-button", "n_clicks"),
    State("filters-collapsed", "data"),
    State("filters-container", "style"),
)
def toggle_filters(n_clicks, collapsed, current_style):
    if n_clicks:
        collapsed = not collapsed if collapsed is not None else True
    else:
        collapsed = False

    style = current_style.copy()
    if collapsed:
        style.update({
            "display": "none",
        })
    else:
        style.update({
            "display": "flex",
        })
    return (collapsed,
            style,
            "˅˅" if collapsed else "˄˄")


@app.callback(
    Output("driver-careers-chart", "figure"),
    Input("career-mode", "value"),
    Input("constructor-filter", "value"),
    Input("driver-filter", "value"),
    Input("year-range-slider", "value")
)
def update_chart(mode, constructor_filter, driver_filter, season_filter):
    return create_career_plot(
        mode=mode,
        constructor_filter=constructor_filter,
        driver_filter=driver_filter,
        season_filter=season_filter,
    ).update_layout()


@app.callback(
    Output("career-timeline-chart", "figure"),
    Output("career-timeline-chart", "style"),
    Output("timeline-instruction", "style"),
    Input("show-career-timeline", "n_clicks"),
    State("driver-id-storage", "data"),
)
def show_career_timeline(n_clicks, driver_id):
    if n_clicks and n_clicks > 0 and driver_id:
        fig = create_career_timeline(driver_id)
        return (fig,
                {'display': 'block', 'height': '400px'},
                {'display': 'none'})
    return ({},
            {'display': 'none'},
            {
                'display': 'block',
                'text-align': 'center',
                'color': 'gray',
                'font-style': 'italic',
    })


career = get_career_data()


if __name__ == "__main__":
    app.run(debug=True)
