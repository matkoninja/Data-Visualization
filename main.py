from dash import Dash, dcc, html, Input, Output
from circuit_map import (draw_circuit_info_children,
                         draw_circuits_map, draw_fastest_lap_times_line_chart)


app = Dash(__name__)


app.layout = html.Div(
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


if __name__ == "__main__":
    app.run(debug=True)
