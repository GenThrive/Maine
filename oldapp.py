# Libraries
# Data
import os # Operating system library
import math
import numpy as np
import pandas as pd # Dataframe manipulations
import geopandas as gpd
import pathlib # file paths
import time

# Dash App
# from jupyter_dash import JupyterDash # for running in a Jupyter Notebook
import dash
import dash_bootstrap_components as dbc

# import dash_core_components as dcc
from dash import dcc
# import dash_html_components as html
from dash import html
# import dash_table as dt
from dash import dash_table as dt
from dash.dependencies import Input, Output, State, ALL, MATCH

# Data Visualization
import plotly.express as px
import plotly.graph_objects as go

# Geojson loading
from urllib.request import urlopen
import json

#Regex execption escaping
import re

# import local modules
from styling import *
from data_processing import *
from load_data import *
from make_components import *


# ----------------------------------------------------------------------------
# Build components
# ----------------------------------------------------------------------------

overview_msg = html.Div([
    html.H5(id='overview_msg')
])

dds_orgs =  html.Div(
    [make_dropdown(
        f'dd-org-{k}',
        org_filter_dict_checked[k]['options'][0],
        org_filter_dict_checked[k]['display_name']) for k in ORG_FILTER_LIST_checked
    ]
)

dds_programs =  html.Div(
    # [html.P(k) for k in pg_filter_dict_checked]
    [make_dropdown(
        f'dd-pg-{k}',
        pg_filter_dict_checked[k]['options'][0],
        pg_filter_dict_checked[k]['display_name']) for k in pg_filter_dict_checked
     ]
)


dashboard = html.Div([
    dbc.Row([
        dbc.Col([
            dcc.Graph(id = 'map')
        ],width=12, xl=6),
        dbc.Col([
            dcc.Graph(id='top_right'),
            # Drop Down for bar chart expansion
            dcc.Dropdown(
                    id = 'dd-barchart-top-right',
                options = [{'label': bar_dropdown_dict[0][c], 'value': c}
                            for c in bar_dropdown_dict[0]],
                    value = list(bar_dropdown_dict[0].keys())[0]
                    ),
        ],width=12, xl=6),
    ],
    style={'padding': '20px'}  # Adjust the padding value as needed
    ),
    dbc.Row([
        dbc.Col([
            dcc.Graph(id='chart_theme'),
            # Drop Down for bar chart expansion
            dcc.Dropdown(
                    id = 'dd-barchart',
                options = [{'label': bar_dropdown_dict[0][c], 'value': c}
                            for c in bar_dropdown_dict[0]],
                    value = list(bar_dropdown_dict[0].keys())[1]
                    ),
        ],width=12, xl=6),
        dbc.Col([
            dcc.Graph(id='chart_sector'),
            # Todo: Make this behave much more like the filter drop downs using `make_dropdown` to get the diplay terms.
            # should also put the long list of column names in an ALL CAPS constant like "PROG_FILTER_LIST"

            dcc.Dropdown(
                id = 'dd-pie',
                options = [{'label': pie_dropdown_dict[0][c], 'value': c}
                            for c in pie_dropdown_dict[0]],
                value = list(pie_dropdown_dict[0].keys())[0]
                ),
        ],width=12, xl=6),
        html.Div(id='chart_test'),

    ])

])

test_div = html.Div()

# ----------------------------------------------------------------------------
# Layout pieces
# ----------------------------------------------------------------------------

sidebar = html.Div(
    [
        html.H2(page_title),
        html.Img(src='/assets/NAAEE_Wisconsin_Logo.png', style={'height':'120px','width':'100%', 'padding-bottom':'10px'}),
        html.H4(sub_title),
        html.H5(filter_category_1),
        dds_orgs,
        html.H5(filter_category_2, style={'padding-top':'10px'}),
        dds_programs,
        html.Div(id='div-overview_msg'),
         html.H6(['Powered by ',
                 html.A('Gen:Thrive ',
                        href='https://genthrive.org/', target='blank', style={'text-decoration':'none'}),html.Img(src='/assets/Generation-Thrive-ICON-Color-High-Res.png', style={'height':'15%', 'width':'15%'})], style={'padding-top':'1rem', 'padding-left':'10px', 'padding-right':'10px'}),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div([
    html.Div(id = 'test_div'),
    dcc.Store(id='store-data'),
    dcc.Store(id='store-filtered-ids'),
    html.Div(id="out-all-types"),

    html.Div([
        dcc.Tabs(id='tabs', value = 'tab-dashboard', children = [
            dcc.Tab(label='Dashboard', value = 'tab-dashboard', id='tab-dashboard', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
            dcc.Tab(id='tab-org', value = 'tab-org', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
            # dcc.Tab(id='tab-pg',   value = 'tab-pg', style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        ]),
        # dcc.Loading(
        #     id="loading-1",
        #     type="circle",
        #     children=[
        dbc.Spinner(
                color="primary",
                size = 'md',
                delay_hide= 5,
                children=[html.Div(id='tab-content', className='delay')]
                ),
        #     ],
        # ),
    ])
],
    id="page-content", style=CONTENT_STYLE)



# ----------------------------------------------------------------------------
# Build App
# ----------------------------------------------------------------------------

external_stylesheets = [dbc.themes.LITERA]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets) # For Jupyter notebook app = JupyterDash(external_stylesheets=external_stylesheets)
server = app.server
app.title = app_title
app.config.suppress_callback_exceptions = True

app.layout = html.Div([sidebar, content])

# ----------------------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------------------

#TODO: Add a datastore to hold filtered data! Use as state for the figures
@app.callback(Output('store-data', 'data'),
        Output('tab-org','label'), Output('tab-pg','label'),
        Output('test_div','children'),
        [Input(f'dd-org-{dd}', "value") for dd in org_filter_dict_checked]+
        [Input(f'dd-pg-{dd}', "value") for dd in pg_filter_dict_checked]
        )
def store_data(*vals):
    # Split org and prog selected values. This is a dynamically created list of the *vals.
    # The first x values (equal to the length of the org_filter_dict_checked options) are from the Organization Table, while the remainder are from the Programs table
    input_organization_filters = vals[:len(org_filter_dict_checked)]
    input_program_filters = vals[len(org_filter_dict_checked):]

    display_dict = {}
    # display_dict['inputs'] = '{0}'.format(vals)

    # Load main data tables from global
    org_df = orgs
    programs_df = programs

    # Check for Org filters
    if any(input_organization_filters):
        # Build mapping from col_name -> list of selected values
        input_org_col_to_selected = {
            col_name: selected_terms
            for col_name, selected_terms
            in zip(ORG_FILTER_LIST_checked, input_organization_filters)
        }    # Filter data frame

        # Get lists of the elements that are multi term
        multiterm_org_columns = dp.multiterm_columns(directory_df, "Organizations")
        display_dict['multi-org'] = multiterm_org_columns

        # Keep only organizations that fit the filter values chosen in the dashboard
        for col_name, selected_terms in input_org_col_to_selected.items():
            if selected_terms:
                # Drop rows where the select column is empty, because it means
                # it won't match any filtered value anyway.
                org_df = org_df.dropna(subset=[col_name])

                if col_name in multiterm_org_columns:
                    selected_set = set(selected_terms)
                    is_overlapping = org_df[col_name].apply(lambda x: bool(set(x) & selected_set))
                    org_df = org_df.loc[is_overlapping]
                else:
                    org_df = org_df.loc[org_df[col_name].isin(selected_terms)]

        # Filter out Programs that aren't part of these orgs
        programs_df = programs_df[programs_df['orgID'].isin(org_df['orgID'])]

    # Check for Program filters
    if any(input_program_filters):
        # Build mapping from col_name -> list of selected values
        input_prog_col_to_selected = {
            col_name: selected_terms
            for col_name, selected_terms
            in zip(PROG_FILTER_LIST_checked, input_program_filters)
        }

        # Get lists of the elements that are multi term
        multiterm_prog_columns = dp.multiterm_columns(directory_df, "Programs")
        display_dict['multi-pg'] = multiterm_prog_columns

        # Do Program filter
        for col_name, selected_terms in input_prog_col_to_selected.items():
            if selected_terms:
                # Drop rows where the select column is empty, because it means
                # it won't match any filtered value anyway.
                programs_df = programs_df.dropna(subset=[col_name])
                if col_name in multiterm_prog_columns:
                    selected_set = set(selected_terms)
                    is_overlapping = programs_df[col_name].apply(lambda x: bool(set(x) & selected_set))
                    programs_df = programs_df.loc[is_overlapping]
                else:
                    programs_df = programs_df.loc[programs_df[col_name].isin(selected_terms)]

        # Filter organizations to only those with some of these prorgrams
        org_df = org_df[org_df['orgID'].isin(programs_df['orgID'])]

    # Store filtered data frame in data store
    store_dict ={}

    store_dict['Organizations'] = {}
    store_dict['Organizations']['count'] = len(org_df)
    store_dict['Organizations']['id_list'] = list(org_df.orgID)
    store_dict['Organizations']['columns'] = list(org_df.columns)
    store_dict['Organizations']['data'] = org_df.to_dict('records')

    store_dict['Programs'] = {}
    store_dict['Programs']['count'] = len(programs_df)
    store_dict['Programs']['id_list'] = list(programs_df.programID)
    store_dict['Programs']['columns'] = list(programs_df.columns)
    store_dict['Programs']['data'] = programs_df.to_dict('records')

    # Add record count to tab label
    tab_orgs_label = 'Organization Records (' + str(len(org_df)) + ')'
    # tab_orgs_label = 'Organization Records'
    tab_programs_label = 'Program Records ('  + str(len(programs_df)) + ')'
    # tab_programs_label = 'Program Records'

#---------------
    # map_orgs = pd.DataFrame(store_dict['Organizations']['data'])
    test_div = html.Div('i am here')
#---------------
    return store_dict, tab_orgs_label, tab_programs_label, None #, test_div

@app.callback(Output('tab-content', 'children'),
              Input('tabs', 'value'),
              Input('store-data','data'))
def render_content(tab, data):
    if tab == 'tab-dashboard':
        return html.Div([
            dashboard
        ])
    elif tab == 'tab-org':
        org_id_list = data['Organizations']['id_list']
        if len(org_id_list) > 0:
            df = orgs_directory[orgs_directory.orgID.isin(org_id_list)]
            return html.Div([
                build_directory_table('table-orgs', df, directory_df, 'Organizations')
                ],style={'width':'100%'})
        else:
            return html.Div('There are no records that match this search query.  Please change the filters.')
    elif tab == 'tab-pg':
        programs_id_list = data['Programs']['id_list']
        if len(programs_id_list) > 0:
            df = programs_directory[programs_directory.programID.isin(programs_id_list)]
            return html.Div([
                    build_directory_table('table-programs', df, directory_df, 'Programs')
                    ],style={'width':'100%'})
        else:
            return html.Div('There are no records that match this search query.  Please change the filters.')



@app.callback(Output('map', 'figure'),Input('store-data','data'))
def build_map(data):
    # try:
        # build map
        # Get Count of entities per esc
        orgs_map = pd.DataFrame(data['Organizations']['data'])
        esc_count_df = pd.DataFrame(orgs_map['Education_Service_Center'].value_counts())
        esc_count_df = esc_count_df.reset_index().rename(columns={"index": "ESC", "Education_Service_Center": "Organizations"})
        if orgs_map.empty:
            map_fig = no_data_fig()
        else:
            map_fig = make_map(orgs_map, 'Latitude', 'Longitude', tx_esc, geojson_featureidkey, esc_count_df, 'ESC', 'Organizations', map_center_lat, map_center_lon, map_zoom=map_zoom,)
            
        return  map_fig
    # except:
    #     return  no_data_fig()

# @app.callback(Output('treemap', 'figure'),Input('store-data','data')) #Output('treemap_parent', 'children'),
# def build_treemap(data):
#     try:
#         treemap_data_all = pd.DataFrame(data['Programs']['data'])
#         path=['State', 'Audiences','Organization', 'Program'] # 'Themes', 'Services_Resources',
#         treemap_data = treemap_data_all[path + ['orgID']].copy()
#         tree_data = explode_multiple(treemap_data, ['Audiences'])
#         tree_data['count_program'] = 1
#         tree_data = tree_data.dropna()
#
#         if treemap_data.empty:
#             tree_fig = no_data_fig()
#         else:
#             tree_fig = px.treemap(tree_data, path=path, values = 'count_program',
#                                color_discrete_sequence=eco_color,
#                                maxdepth=2)
#         return tree_fig
#     except:
#         return  no_data_fig()

@app.callback(Output('top_right', 'figure'),Input('store-data','data'),Input('dd-barchart-top-right', 'value'))
def build_barchart(data, input_barchart):
    try:
        if input_barchart in data['Organizations']['columns']:
            df_for_chart = pd.DataFrame(data['Organizations']['data'])
            id_col = 'orgID'
            table_name = 'Organizations'
            title_group='Organization'
        else:
            df_for_chart = pd.DataFrame(data['Programs']['data'])
            id_col = 'programID'
            table_name = 'Programs'
            title_group='Program'
    # Build Bar chart
        bar_data = get_chart_data(df_for_chart, id_col, input_barchart, controlled_terms_df, table_name)
        bar_data = bar_data.groupby(bar_data.columns[3]).agg({'Count': 'sum'}).reset_index()
        cols = list(bar_data.columns)
        bar_data.columns = [col.replace('_y','') for col in cols]
        # bar_title = "{} (grouped by {})".format(bar_data.columns[0], title_group)
        bar_title = "<b>{}</b>".format(bar_data.columns[0], title_group)
        bar_chart = make_bar(bar_data, 0, 1, layout_direction = 'v', marker_color=eco_color, title = bar_title, ascending=False)
        return  bar_chart
    except:
        return  no_data_fig()


@app.callback(Output('chart_sector', 'figure'),Input('store-data','data'),Input('dd-pie', 'value'))
def build_piechart(data, input_piechart):
    # try:
        # This is a hack. get the code working!
        # Build pie chart
        # Choose df for pie chart
        if input_piechart in (data['Organizations']['columns']):
            df_for_chart = pd.DataFrame(data['Organizations']['data'])
            id_col = 'orgID'
            table_name = 'Organizations'
            title_group='Organization'
        else:
            df_for_chart = pd.DataFrame(data['Programs']['data'])
            id_col = 'programID'
            table_name = 'Programs'
            title_group='Program'

        pie_data = get_chart_data(df_for_chart, id_col, input_piechart, controlled_terms_df, table_name)
        pie_data = pie_data.groupby(pie_data.columns[3]).agg({'Count': 'sum'}).reset_index()
        cols = list(pie_data.columns)
        pie_data.columns = [col.replace('_y','') for col in cols]
        name_col, value_col = pie_data.columns[0], pie_data.columns[1]
        # pie_title = "{} (grouped by {})".format(name_col, title_group)
        pie_title = "<b>{}</b>".format(name_col)

        # Set label type from pie_chart
        # use try / except to use the value from pie_format if it works, else just use the textinfo = None
        try:
            pie_format = directory_df.loc[(directory_df['table_name']==table_name) & (directory_df['column_name']==input_piechart) ]['pie_format'].values[0]
            pie_chart = make_pie_chart(pie_data, name_col, value_col, title = pie_title, color_scale = eco_color, showlegend=True, textinfo=pie_format)
        except:
            pie_chart = make_pie_chart(pie_data, name_col, value_col, title = pie_title, color_scale = eco_color, showlegend=True)

        return  pie_chart
    # except:
    #     return  no_data_fig()


@app.callback(Output('chart_theme', 'figure'),Input('store-data','data'),Input('dd-barchart', 'value'))
def build_barchart(data, input_barchart):
    try:
        if input_barchart in data['Organizations']['columns']:
            df_for_chart = pd.DataFrame(data['Organizations']['data'])
            id_col = 'orgID'
            table_name = 'Organizations'
            title_group='Organization'
        else:
            df_for_chart = pd.DataFrame(data['Programs']['data'])
            id_col = 'programID'
            table_name = 'Programs'
            title_group='Program'
    # Build Bar chart
        bar_data = get_chart_data(df_for_chart, id_col, input_barchart, controlled_terms_df, table_name)
        bar_data = bar_data.groupby(bar_data.columns[3]).agg({'Count': 'sum'}).reset_index()
        cols = list(bar_data.columns)
        bar_data.columns = [col.replace('_y','') for col in cols]
        # bar_title = "{} ed by {})".format(bar_data.columns[0], title_group)
        bar_title = "<b>{}</b>".format(bar_data.columns[0], title_group)
        bar_chart = make_bar(bar_data, 0, 1, layout_direction = 'h', marker_color=eco_color, title = bar_title, ascending=True)
        return  bar_chart
    except:
        return  no_data_fig()



## TO DO
## Add themes once the data processing is worked out
## Output: Output('chart_theme', 'figure'),

# RUN app
if __name__ == "__main__":

    # Starting flask server
    app.run_server(debug=True, port=8040)
