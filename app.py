# Libraries
import os
import math
import numpy as np
import pandas as pd
import geopandas as gpd
import pathlib
import time

# Dash App
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash import dash_table as dt
from dash.dependencies import Input, Output, State

# Data Visualization
import plotly.express as px
import plotly.graph_objects as go

# Import local modules
from styling import *
from data_processing import *
from load_data import *
from make_components import *

# ----------------------------------------------------------------------------
# Build components
# ----------------------------------------------------------------------------

overview_msg = html.Div([html.H5(id='overview_msg')])

dds_orgs = html.Div([
    make_dropdown(
        f'dd-org-{k}',
        org_filter_dict_checked[k]['options'][0],
        org_filter_dict_checked[k]['display_name']) for k in ORG_FILTER_LIST_checked
])

dashboard = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='map')
        ], width=12, xl=6),
        dbc.Col([
            dcc.Graph(id='top_right'),
            dcc.Dropdown(
                id='dd-barchart-top-right',
                options=[{'label': bar_dropdown_dict[0][c], 'value': c}
                         for c in bar_dropdown_dict[0]],
                value=list(bar_dropdown_dict[0].keys())[0]
            ),
        ], width=12, xl=6),
    ],
        style={'padding': '20px'}
    ),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='chart_theme'),
            dcc.Dropdown(
                id='dd-barchart',
                options=[{'label': bar_dropdown_dict[0][c], 'value': c}
                         for c in bar_dropdown_dict[0]],
                value=list(bar_dropdown_dict[0].keys())[1]
            ),
        ], width=12, xl=6),
        dbc.Col([
            dcc.Graph(id='chart_sector'),
            dcc.Dropdown(
                id='dd-pie',
                options=[{'label': pie_dropdown_dict[0][c], 'value': c}
                         for c in pie_dropdown_dict[0]],
                value=list(pie_dropdown_dict[0].keys())[0]
            ),
        ], width=12, xl=6),
        html.Div(id='chart_test'),
    ])
])

# ----------------------------------------------------------------------------
# Layout
# ----------------------------------------------------------------------------

sidebar = html.Div([
    html.H2(page_title),
    # html.Img(src='/assets/NAAEE_Wisconsin_Logo.png', style={'height': '120px', 'width': '100%', 'padding-bottom': '10px'}),
    html.H4(sub_title),
    html.H5(filter_category_1),
    dds_orgs,
    html.Div(id='div-overview_msg'),
    html.H6(['Powered by ',
                 html.A('Gen:Thrive ',
                        href='https://genthrive.org/', target='blank', style={'text-decoration':'none'}),html.Img(src='/assets/Generation-Thrive-ICON-Color-High-Res.png', style={'height':'15%', 'width':'15%'})], style={'padding-top':'1rem', 'padding-left':'10px', 'padding-right':'10px'}),
], style=SIDEBAR_STYLE)

content = html.Div([
    html.Div(id='test_div'),
    dcc.Store(id='store-data'),
    dcc.Store(id='store-filtered-ids'),
    html.Div(id="out-all-types"),
    html.Div([
        dcc.Tabs(id='tabs', value='tab-dashboard', children=[
            dcc.Tab(label='Dashboard', value='tab-dashboard', id='tab-dashboard', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
            dcc.Tab(id='tab-org', value='tab-org', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        ]),
        dbc.Spinner(
            color="primary",
            size='md',
            delay_hide=5,
            children=[html.Div(id='tab-content', className='delay')]
        ),
    ])
], id="page-content", style=CONTENT_STYLE)

# ----------------------------------------------------------------------------
# Build App
# ----------------------------------------------------------------------------

external_stylesheets = [dbc.themes.LITERA]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
app.title = app_title
app.config.suppress_callback_exceptions = True

app.layout = html.Div([sidebar, content])

# ----------------------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------------------

@app.callback(
    Output('store-data', 'data'),
    Output('tab-org', 'label'),
    [Input(f'dd-org-{dd}', "value") for dd in org_filter_dict_checked]
)
def store_data(*vals):
    # Split organization filters
    input_organization_filters = vals

    # Load main data tables from global
    org_df = orgs

    # Check for Org filters
    if any(input_organization_filters):
        input_org_col_to_selected = {
            col_name: selected_terms
            for col_name, selected_terms
            in zip(ORG_FILTER_LIST_checked, input_organization_filters)
        }

        multiterm_org_columns = dp.multiterm_columns(directory_df, "Organizations")

        # Apply filters
        for col_name, selected_terms in input_org_col_to_selected.items():
            if selected_terms:
                org_df = org_df.dropna(subset=[col_name])

                if col_name in multiterm_org_columns:
                    selected_set = set(selected_terms)
                    is_overlapping = org_df[col_name].apply(lambda x: bool(set(x) & selected_set))
                    org_df = org_df.loc[is_overlapping]
                else:
                    org_df = org_df.loc[org_df[col_name].isin(selected_terms)]

    # Store filtered data frame in data store
    store_dict = {
        'Organizations': {
            'count': len(org_df),
            'id_list': list(org_df.orgID),
            'columns': list(org_df.columns),
            'data': org_df.to_dict('records')
        }
    }

    tab_orgs_label = 'Organization Records (' + str(len(org_df)) + ')'
    return store_dict, tab_orgs_label


@app.callback(
    Output('tab-content', 'children'),
    Input('tabs', 'value'),
    Input('store-data', 'data')
)
def render_content(tab, data):
    if tab == 'tab-dashboard':
        return html.Div([dashboard])
    elif tab == 'tab-org':
        org_id_list = data['Organizations']['id_list']
        if len(org_id_list) > 0:
            df = orgs_directory[orgs_directory.orgID.isin(org_id_list)]
            return html.Div([
                build_directory_table('table-orgs', df, directory_df, 'Organizations')
            ], style={'width': '100%'})
        else:
            return html.Div('There are no records that match this search query. Please change the filters.')


@app.callback(
    Output('map', 'figure'),
    Input('store-data', 'data')
)
def build_map(data):
    orgs_map = pd.DataFrame(data['Organizations']['data'])
    esc_count_df = pd.DataFrame(orgs_map['Education_Service_Center'].value_counts())
    esc_count_df = esc_count_df.reset_index().rename(columns={"index": "ESC", "Education_Service_Center": "Organizations"})
    
    if orgs_map.empty:
        return no_data_fig()
    else:
        return make_map(
            orgs_map, 'Latitude', 'Longitude', tx_esc, geojson_featureidkey, state_name, esc_count_df,
            'ESC', 'Organizations', map_center_lat, map_center_lon, map_zoom=map_zoom
        )


@app.callback(
    Output('top_right', 'figure'),
    Input('store-data', 'data'),
    Input('dd-barchart-top-right', 'value')
)
def build_barchart(data, input_barchart):
    df_for_chart = pd.DataFrame(data['Organizations']['data'])
    id_col = 'orgID'

    bar_data = get_chart_data(df_for_chart, id_col, input_barchart, controlled_terms_df, 'Organizations')
    bar_data = bar_data.groupby(bar_data.columns[3]).agg({'Count': 'sum'}).reset_index()

    bar_title = "<b>{}</b>".format(bar_data.columns[0])
    return make_bar(bar_data, 0, 1, layout_direction='v', marker_color=eco_color, title=bar_title, ascending=False)


@app.callback(
    Output('chart_sector', 'figure'),
    Input('store-data', 'data'),
    Input('dd-pie', 'value')
)
def build_piechart(data, input_piechart):
    df_for_chart = pd.DataFrame(data['Organizations']['data'])
    id_col = 'orgID'

    pie_data = get_chart_data(df_for_chart, id_col, input_piechart, controlled_terms_df, 'Organizations')
    pie_data = pie_data.groupby(pie_data.columns[3]).agg({'Count': 'sum'}).reset_index()

    pie_title = "<b>{}</b>".format(pie_data.columns[0])
    return make_pie_chart(pie_data, pie_data.columns[0], pie_data.columns[1], title=pie_title, color_scale=eco_color, showlegend=True)


@app.callback(
    Output('chart_theme', 'figure'),
    Input('store-data', 'data'),
    Input('dd-barchart', 'value')
)
def build_barchart(data, input_barchart):
    df_for_chart = pd.DataFrame(data['Organizations']['data'])
    id_col = 'orgID'

    bar_data = get_chart_data(df_for_chart, id_col, input_barchart, controlled_terms_df, 'Organizations')
    bar_data = bar_data.groupby(bar_data.columns[3]).agg({'Count': 'sum'}).reset_index()

    bar_title = "<b>{}</b>".format(bar_data.columns[0])
    return make_bar(bar_data, 0, 1, layout_direction='h', marker_color=eco_color, title=bar_title, ascending=False)

# ----------------------------------------------------------------------------
# Run App
# ----------------------------------------------------------------------------

if __name__ == '__main__':
    app.run_server(debug=False)
