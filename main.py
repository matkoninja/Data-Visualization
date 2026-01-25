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


app.layout = html.Div([
    # Top row: Map + Circuit Info
    circuit_map_layout,

    # Middle row: Driver careers scatter plot + driver card
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
        html.Div([
            dcc.Graph(
                figure=create_career_plot(),
                id="driver-careers-chart",
                className="main-chart"
            ),
            html.Div(
                id="driver-card",
                className="driver-card"
            )
        ], className="chart-card-wrapper")
    ], className="bottom-container"),

    # Bottom row: Career timeline chart (initially hidden)
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
    Output("driver-careers-chart", "figure"),
    Input("career-mode", "value")
)
def update_chart(mode):
    return create_career_plot(mode=mode).update_layout()


@app.callback(
    Output("career-timeline-chart", "figure"),
    Output("career-timeline-chart", "style"),
    Output("timeline-instruction", "style"),
    Input("show-career-timeline", "n_clicks"),
    State("driver-id-storage", "children"),
    prevent_initial_call=True
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


@app.callback(
    Output("driver-card", "children"),
    Input("driver-careers-chart", "clickData")
)
def display_driver_card(clickData):
    if not clickData:
        return html.Div("Click on a driver point to view details",
                        className="card-placeholder")
    try:
        point = clickData['points'][0]
        driver_id = point['customdata'][0]
        driver_data = career[career['driverId'] == driver_id].iloc[0]
        tmp_driver_data = get_driver_data(driver_id)
        driver_url = (tmp_driver_data['url']
                      if not tmp_driver_data.empty
                      else "")
        return create_driver_card(driver_data, driver_url)
    except (IndexError, KeyError, AttributeError):
        return html.Div("Driver data not found", className="card-error")


if __name__ == "__main__":
    app.run(debug=True)
