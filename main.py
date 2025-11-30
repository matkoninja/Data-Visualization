from dash import Dash, dcc, html, Input, Output
from circuit_map import (draw_circuit_info_children,
                         draw_circuits_map, draw_fastest_lap_times_line_chart)
from scatter_plot_drivers import create_career_plot, html_render 

app = Dash(__name__)


app.layout = html.Div([
    # Top row: Map + Circuit Info
    html.Div([
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
    className="circuits-lap-times-container"),
    
    html.Div([
        html.Div([
            html.H3('Chart view:', className="driver-name"),
            dcc.RadioItems(
                id='career-mode',
                options=['start', 'end', 'both'],
                value='start',
                className="toggle-switch"
            )
        ], className="sidebar"),
        html.Div([  # Wrap chart and card together
            dcc.Graph(
                figure=create_career_plot(),
                id="driver-careers-chart",
                className="main-chart"
            ),
            html.Div(
                id="driver-card",  # New driver card container
                className="driver-card"
            )
        ], className="chart-card-wrapper")
    ], className="bottom-container")
],className="dashboard-container")


@app.callback(
    Output("circuits-map", "figure"),
    Input("circuits-map", "clickData"),
)
def map_click_render_map(clickData):
    return draw_circuits_map(clickData)


@app.callback(
    Output("circuit-info", "children"),
    Input("circuits-map", "clickData"),
)
def set_circuit_info(clickData):
    return draw_circuit_info_children(clickData)


@app.callback(
    Output("circuits-lap-times", "figure"),
    Input("circuits-map", "clickData"),
)
def map_click_render_line_chart(clickData):
    return draw_fastest_lap_times_line_chart(clickData)

@app.callback(
    Output("driver-careers-chart", "figure"),
    Input("career-mode", "value")
)
def update_chart(mode):
    return create_career_plot(mode=mode).update_layout()


# NEW CALLBACK: Display driver card on point click
@app.callback(
    Output("driver-card", "children"),
    Input("driver-careers-chart", "clickData")
)
def display_driver_card(clickData):
    if not clickData:
        return html.Div("Click on a driver point to view details", className="card-placeholder")
    try:
       return html_render(clickData)
    except (IndexError, KeyError, AttributeError):
        return html.Div("Driver data not found", className="card-error")



if __name__ == "__main__":
    app.run(debug=True)
