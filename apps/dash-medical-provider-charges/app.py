import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from dash.dependencies import State, Input, Output
from dash.exceptions import PreventUpdate

import pandas as pd
import pathlib

app = dash.Dash(__name__)
server = app.server

app.config["suppress_callback_exceptions"] = True


ASSETS_PATH = pathlib.Path(__file__, "/assets").resolve()
LOGO_PATH = ASSETS_PATH.joinpath("plotly_logo.png").resolve()
DATA_PATH = pathlib.Path(__file__, "/data").resolve()  # /data

# Plotly mapbox token
mapbox_access_token = "pk.eyJ1IjoicGxvdGx5bWFwYm94IiwiYSI6ImNqdnBvNDMyaTAxYzkzeW5ubWdpZ2VjbmMifQ.TXcBE-xg9BFdV2ocecc_7g"

state_list = [
    "AL",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DC",
    "FL",
    "GA",
    "IL",
    "IN",
    "IA",
    "KY",
    "MD",
    "MA",
    "MI",
    "MN",
    "MO",
    "NE",
    "NJ",
    "NY",
    "NC",
    "OH",
    "OK",
    "OR",
    "PA",
    "SC",
    "TN",
    "TX",
    "UT",
    "VA",
    "WA",
    "WI",
    "AK",
    "DE",
    "HI",
    "ID",
    "KS",
    "LA",
    "ME",
    "MS",
    "MT",
    "NV",
    "NH",
    "NM",
    "ND",
    "RI",
    "SD",
    "WV",
    "VT",
    "WY",
]

# Load data
data_dict = {}
for state in state_list:
    f_path = "processed/df_{}_lat_lon.csv".format(state)
    data_path = DATA_PATH.joinpath(f_path)
    state_data = pd.read_csv(str(data_path)[1:])
    data_dict[state] = state_data

df_al = data_dict["AL"]

# Cost Metric
cost_metric = [
    "Average Covered Charges",
    "Average Total Payments",
    "Average Medicare Payments",
]

# Region
region_list = df_al["Hospital Referral Region (HRR) Description"].unique()


def generate_aggregation_upfront(df, metric):
    aggregation = {
        metric[0]: ["min", "mean", "max"],
        metric[1]: ["min", "mean", "max"],
        metric[2]: ["min", "mean", "max"],
    }
    grouped = (
        df.groupby(["Hospital Referral Region (HRR) Description", "Provider Name"])
        .agg(aggregation)
        .reset_index()
    )

    grouped["lat"] = grouped["lon"] = grouped["Provider Street Address"] = grouped[
        "Provider Name"
    ]
    grouped["lat"] = grouped["lat"].apply(lambda x: get_lat_lon_add(df, x)[0])
    grouped["lon"] = grouped["lon"].apply(lambda x: get_lat_lon_add(df, x)[1])
    grouped["Provider Street Address"] = grouped["Provider Street Address"].apply(
        lambda x: get_lat_lon_add(df, x)[2]
    )

    return grouped


def get_lat_lon_add(df, name):
    return [
        df.groupby(["Provider Name"]).get_group(name)["lat"].tolist()[0],
        df.groupby(["Provider Name"]).get_group(name)["lon"].tolist()[0],
        df.groupby(["Provider Name"])
        .get_group(name)["Provider Street Address"]
        .tolist()[0],
    ]


# Generate aggregated data
data = generate_aggregation_upfront(df_al, cost_metric)


def build_banner():
    return html.Div(
        id="banner",
        className="banner",
        children=[html.H6("Dash Clinical Analytics"), html.Img(src=str(LOGO_PATH))],
    )


def build_upper_left_panel():
    return html.Div(
        id="upper-left",
        className="six columns",
        children=[
            html.P(
                className="section-title",
                children="Choose hospital on the map or procedures from the list below to see costs",
            ),
            html.Div(
                id="select-panel",
                children=[
                    html.Div(
                        id="state-select-outer",
                        style={"width": "80%"},
                        children=[
                            html.Label("Select a State"),
                            dcc.Dropdown(
                                id="state-select",
                                options=[{"label": i, "value": i} for i in state_list],
                                value=state_list[0],
                            ),
                        ],
                    ),
                    html.Div(
                        id="select-metric-outer",
                        className="six columns",
                        children=[
                            html.Label("Choose a Cost Metric:"),
                            dcc.Dropdown(
                                id="metric-select",
                                options=[{"label": i, "value": i} for i in cost_metric],
                                value=cost_metric[0],
                            ),
                        ],
                    ),
                    html.Div(
                        id="region-select-outer",
                        className="six columns",
                        children=[
                            html.Label("Pick a Region:"),
                            html.Div(
                                id="checklist-container",
                                children=dcc.Checklist(
                                    id="region-select-all",
                                    options=[
                                        {"label": "Select All Regions", "value": "All"}
                                    ],
                                    values=["All"],
                                ),
                            ),
                            html.Div(
                                id="region-select-dropdown-outer",
                                children=dcc.Dropdown(
                                    id="region-select",
                                    options=[
                                        {"label": i, "value": i} for i in region_list
                                    ],
                                    value=region_list[:4],
                                    multi=True,
                                    searchable=True,
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                id="cost-stats-outer-container",
                style={"marginTop": "20px"},
                children=[
                    html.P("Hospital Charges Summary"),
                    html.Div(id="cost-stats-container"),
                    html.P("Procedure Charges Summary"),
                    html.Div(id="procedure-stats-container"),
                ],
            ),
        ],
    )


def generate_geo_map(geo_data, selected_metric, region_select, procedure_select):
    filtered_data = geo_data[
        geo_data["Hospital Referral Region (HRR) Description"].isin(region_select)
    ]

    colors = ["#21c7ef", "#76f2ff", "#ff6969", "#ff1717"]

    hospitals = []

    lat = filtered_data["lat"].tolist()
    lon = filtered_data["lon"].tolist()
    average_covered_charges_mean = filtered_data[selected_metric]["mean"].tolist()
    regions = filtered_data["Hospital Referral Region (HRR) Description"].tolist()
    provider_name = filtered_data["Provider Name"].tolist()

    # Cost metric mapping from aggregated data

    cost_metric_data = {}
    cost_metric_data["min"] = filtered_data[selected_metric]["mean"].min()
    cost_metric_data["max"] = filtered_data[selected_metric]["mean"].max()
    cost_metric_data["mid"] = (cost_metric_data["min"] + cost_metric_data["max"]) / 2
    cost_metric_data["low_mid"] = (
        cost_metric_data["min"] + cost_metric_data["mid"]
    ) / 2
    cost_metric_data["high_mid"] = (
        cost_metric_data["mid"] + cost_metric_data["max"]
    ) / 2

    for i in range(len(lat)):
        val = average_covered_charges_mean[i]
        region = regions[i]
        provider = provider_name[i]

        if val <= cost_metric_data["low_mid"]:
            color = colors[0]
        elif cost_metric_data["low_mid"] < val <= cost_metric_data["mid"]:
            color = colors[1]
        elif cost_metric_data["mid"] < val <= cost_metric_data["high_mid"]:
            color = colors[2]
        else:
            color = colors[3]

        selected_index = []
        if provider in procedure_select["hospital"]:
            selected_index = [0]

        hospital = go.Scattermapbox(
            lat=[lat[i]],
            lon=[lon[i]],
            mode="markers",
            marker=dict(
                color=color,
                showscale=True,
                colorscale=[
                    [0, "#21c7ef"],
                    [0.33, "#76f2ff"],
                    [0.66, "#ff6969"],
                    [1, "#ff1717"],
                ],
                cmin=cost_metric_data["min"],
                cmax=cost_metric_data["max"],
                size=10
                * (1 + (val + cost_metric_data["min"]) / cost_metric_data["mid"]),
                colorbar=dict(
                    title="Average Cost",
                    titleside="top",
                    tickmode="array",
                    tickvals=[cost_metric_data["min"], cost_metric_data["max"]],
                    ticktext=[
                        "${:,.2f}".format(cost_metric_data["min"]),
                        "${:,.2f}".format(cost_metric_data["max"]),
                    ],
                    ticks="outside",
                ),
            ),
            opacity=0.8,
            selectedpoints=selected_index,
            selected=dict(marker={"color": "#ffff00"}),
            customdata=[(provider, region)],
            hoverinfo="text",
            text=provider
            + "<br>"
            + region
            + "<br>Average Procedure Cost:"
            + " ${:,.2f}".format(val),
        )
        hospitals.append(hospital)

    layout = go.Layout(
        height=700,
        margin=dict(l=10, r=10, t=10, b=10, pad=5),
        plot_bgcolor="#171b26",
        paper_bgcolor="#171b26",
        clickmode="event+select",
        hovermode="closest",
        showlegend=False,
        mapbox=go.layout.Mapbox(
            accesstoken=mapbox_access_token,
            bearing=10,
            center=go.layout.mapbox.Center(
                lat=filtered_data.lat.mean(), lon=filtered_data.lon.mean()
            ),
            pitch=5,
            zoom=7,
            style="mapbox://styles/plotlymapbox/cjvppq1jl1ips1co3j12b9hex",
        ),
    )

    return {"data": hospitals, "layout": layout}


def generate_procedure_plot(raw_data, cost_select, region_select, provider_select):
    procedure_data = raw_data[
        raw_data["Hospital Referral Region (HRR) Description"].isin(region_select)
    ]
    providers = procedure_data["Provider Name"].unique()

    traces = []

    for ind, provider in enumerate(providers):
        hovertemplate = (
            provider + "<br><b>%{y}</b>" + "<br>Average Procedure Cost: %{x:$.2f}"
        )
        dff = procedure_data[procedure_data["Provider Name"] == provider]

        if provider in provider_select:
            selected_index = list(range(len(dff)))
        else:
            selected_index = []  # empty list

        if len(provider_select) == 0:
            selected_index = ""

        provider_trace = go.Scatter(
            y=dff["DRG Definition"],
            x=dff[cost_select],
            name="",
            customdata=dff["Provider Name"],
            hovertemplate=hovertemplate,
            mode="markers",
            selectedpoints=selected_index,
            selected=dict(marker={"color": "#FFFF00", "size": 13}),
            unselected=dict(marker={"opacity": 0.2}),
            marker=dict(
                line=dict(width=1, color="#000000"),
                color="#21c7ef",
                opacity=0.7,
                symbol="square",
                size=12,
            ),
        )

        traces.append(provider_trace)

    layout = go.Layout(
        height=6000,
        showlegend=False,
        hovermode="closest",
        dragmode="select",
        clickmode="event+select",
        xaxis=dict(
            zeroline=False,
            automargin=True,
            showticklabels=True,
            title="Procedure Cost",
            linecolor="white",
            tickfont=dict(color="#737a8d"),
        ),
        yaxis=dict(
            automargin=True,
            showticklabels=True,
            tickfont=dict(color="#737a8d"),
            gridcolor="#171b26",
        ),
        plot_bgcolor="#1f2536",
        paper_bgcolor="#1f2536",
    )
    # x : procedure, y: cost,
    return {"data": traces, "layout": layout}


app.layout = html.Div(
    children=[
        build_banner(),
        html.Div(
            id="upper-container",
            className="row",
            children=[
                build_upper_left_panel(),
                html.Div(
                    id="geo-map-outer",
                    className="six columns",
                    children=[
                        html.P("Medicare Provider Charge Data Alabama State"),
                        dcc.Graph(
                            id="geo-map",
                            figure={
                                "data": [],
                                "layout": dict(
                                    plot_bgcolor="#171b26", paper_bgcolor="#171b26"
                                ),
                            },
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            style={
                "height": "800px",
                "width": "90%",
                "marginLeft": "5%",
                "overflow-y": "scroll",
            },
            children=[
                dcc.Graph(
                    id="procedure-plot",
                    figure=generate_procedure_plot(
                        df_al, cost_metric[0], region_list, []
                    ),
                )
            ],
        ),
    ]
)


@app.callback(
    output=Output("region-select-dropdown-outer", "children"),
    inputs=[Input("state-select", "value")],
)
def update_region_dropdown(state_select):
    state_raw_data = data_dict[state_select]
    regions = state_raw_data["Hospital Referral Region (HRR) Description"].unique()
    return dcc.Dropdown(
        id="region-select",
        options=[{"label": i, "value": i} for i in regions],
        value=regions[:4],
        multi=True,
        searchable=True,
    )


@app.callback(
    output=Output("region-select", "value"),
    inputs=[Input("region-select-all", "values")],
    state=[State("region-select", "options")],
)
def update_region_select(select_all, options):
    if select_all == ["All"]:
        return [i["value"] for i in options]
    raise PreventUpdate()


@app.callback(
    Output("checklist-container", "children"),
    [Input("region-select", "value")],
    [State("region-select", "options"), State("region-select-all", "values")],
)
def update_checklist(selected, select_options, checked):
    if len(selected) < len(select_options) and len(checked) == 0:
        raise PreventUpdate()

    elif len(selected) < len(select_options) and len(checked) == 1:
        return dcc.Checklist(
            id="region-select-all",
            options=[{"label": "Select All Regions", "value": "All"}],
            values=[],
        )

    elif len(selected) == len(select_options) and len(checked) == 1:
        raise PreventUpdate()

    return dcc.Checklist(
        id="region-select-all",
        options=[{"label": "Select All Regions", "value": "All"}],
        values=["All"],
    )


@app.callback(
    output=Output("cost-stats-container", "children"),
    inputs=[
        Input("geo-map", "selectedData"),
        Input("procedure-plot", "selectedData"),
        Input("metric-select", "value"),
        Input("state-select", "value"),
    ],
)
def update_hospital_datatable(geo_select, procedure_select, cost_select, state_select):
    state_agg = generate_aggregation_upfront(data_dict[state_select], cost_metric)
    # make table from geo-select
    geo_data_dict = {
        "Provider Name": [],
        "City": [],
        "Street Address": [],
        "Maximum Cost ($)": [],
        "Minimum Cost ($)": [],
    }

    ctx = dash.callback_context
    if ctx.triggered:
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # make table from procedure-select
    if prop_id == "procedure-plot" and procedure_select is not None:

        for point in procedure_select["points"]:
            provider = point["customdata"]

            dff = state_agg[state_agg["Provider Name"] == provider]

            geo_data_dict["Provider Name"].append(point["customdata"])
            city = dff["Hospital Referral Region (HRR) Description"].tolist()[0]
            geo_data_dict["City"].append(city)

            address = dff["Provider Street Address"].tolist()[0]
            geo_data_dict["Street Address"].append(address)

            geo_data_dict["Maximum Cost ($)"].append(
                dff[cost_select]["max"].tolist()[0]
            )
            geo_data_dict["Minimum Cost ($)"].append(
                dff[cost_select]["min"].tolist()[0]
            )

    if prop_id == "geo-map" and geo_select is not None:

        for point in geo_select["points"]:
            provider = point["customdata"][0]
            dff = state_agg[state_agg["Provider Name"] == provider]

            geo_data_dict["Provider Name"].append(point["customdata"][0])
            geo_data_dict["City"].append(point["customdata"][1].split("- ")[1])

            address = dff["Provider Street Address"].tolist()[0]
            geo_data_dict["Street Address"].append(address)

            geo_data_dict["Maximum Cost ($)"].append(
                dff[cost_select]["max"].tolist()[0]
            )
            geo_data_dict["Minimum Cost ($)"].append(
                dff[cost_select]["min"].tolist()[0]
            )

    geo_data_df = pd.DataFrame(data=geo_data_dict)

    return dash_table.DataTable(
        id="cost-stats-table",
        columns=[{"name": i, "id": i} for i in geo_data_dict.keys()],
        data=geo_data_df.to_dict("rows"),
        filtering=True,
        pagination_mode="fe",
        pagination_settings={"displayed_pages": 1, "current_page": 0, "page_size": 5},
        navigation="page",
        style_cell={"background-color": "#171b26", "color": "#7b7d8d"},
    )


@app.callback(
    output=Output("procedure-stats-container", "children"),
    inputs=[Input("procedure-plot", "selectedData"), Input("geo-map", "selectedData")],
)
def update_procedure_stats(procedure_select, geo_select):
    procedure_dict = {
        "DRG": [],
        "Procedure": [],
        "Provider Name": [],
        "Cost Summary": [],
    }

    ctx = dash.callback_context
    if ctx.triggered:
        prop_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if prop_id == "procedure-plot" and procedure_select is not None:
        for point in procedure_select["points"]:
            procedure_dict["DRG"].append(point["y"].split(" - ")[0])
            procedure_dict["Procedure"].append(point["y"].split(" - ")[1])

            procedure_dict["Provider Name"].append(point["customdata"])
            procedure_dict["Cost Summary"].append(("${:,.2f}".format(point["x"])))

    procedure_data_df = pd.DataFrame(data=procedure_dict)

    return dash_table.DataTable(
        id="procedure-stats-table",
        columns=[{"name": i, "id": i} for i in procedure_dict.keys()],
        data=procedure_data_df.to_dict("rows"),
        filtering=True,
        sorting=True,
        style_cell={
            "textOverflow": "ellipsis",
            "background-color": "#171b26",
            "color": "#7b7d8d",
        },
        sorting_type="multi",
        pagination_mode="fe",
        pagination_settings={"displayed_pages": 1, "current_page": 0, "page_size": 5},
        navigation="page",
    )


@app.callback(
    output=Output("geo-map", "figure"),
    inputs=[
        Input("metric-select", "value"),
        Input("region-select", "value"),
        Input("procedure-plot", "selectedData"),
        Input("state-select", "value"),
    ],
)
def update_geo_map(cost_select, region_select, procedure_select, state_select):
    # generate geo map from state-select, procedure-select
    state_agg_data = generate_aggregation_upfront(data_dict[state_select], cost_metric)

    provider_data = {"procedure": [], "hospital": []}
    if procedure_select is not None:
        for point in procedure_select["points"]:
            provider_data["procedure"].append(point["y"])
            provider_data["hospital"].append(point["customdata"])

    return generate_geo_map(state_agg_data, cost_select, region_select, provider_data)


@app.callback(
    output=Output("procedure-plot", "figure"),
    inputs=[
        Input("metric-select", "value"),
        Input("region-select", "value"),
        Input("geo-map", "selectedData"),
        Input("state-select", "value"),
    ],
)
def update_procedure_plot(cost_select, region_select, geo_select, state_select):
    # generate procedure plot from selected provider
    state_raw_data = data_dict[state_select]

    provider_select = []
    if geo_select is not None:
        for point in geo_select["points"]:
            provider_select.append(point["customdata"][0])
    return generate_procedure_plot(
        state_raw_data, cost_select, region_select, provider_select
    )


if __name__ == "__main__":
    app.run_server(
        dev_tools_hot_reload=False,
        debug=True,
        host="0.0.0.0",
        port=8051,
        use_reloader=False,
    )