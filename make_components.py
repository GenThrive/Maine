# Libraries
# Data
import pandas as pd # Dataframe manipulations
import math

# Dash App
# from jupyter_dash import JupyterDash # for running in a Jupyter Notebook
# import dash_core_components as dcc
from dash import dcc
# import dash_table
from dash import dash_table

# Data Visualization
import plotly.express as px
from styling import *

# ----------------------------------------------------------------------------
# DASHBOARD COMPONENT FUNCTIONS
# ----------------------------------------------------------------------------


# APP Functions
def make_dropdown(i, options, placeholder, multi=True):
    ''' Create a dropdown taking id, option and placeholder values as inputs. '''

    # Handle either list or options as inputs
    if isinstance(options, dict):
        opts = [{'label': options[k], 'value': k}
                            for k in options]
    else:
        opts = [{'label': c, 'value': c}
                            for c in options]

    # Return actual dropdown component
    return dcc.Dropdown(
                id = f"{i}",
                options=opts,
                multi=multi,
                placeholder=placeholder,
                optionHeight=50

                )

# Todo: Figure out which dataframe this function pulls data from when called
# since we split multi-value strings into arrays in the data we process for filters the data will look weird if
# we don't go back and get the original values for this display.
def build_directory_table(table_id, df, directory_dataframe=None, directory_table_name=None):
    ''' Function to create the structure and style elements of both the Organization and Programs tables.

        If the directory_table_name is specified, select columns according to directory file
    '''
    # Checks to add:
#     * input dataframe
#     * display_cols are in list of columsn in dataframe
    if directory_dataframe is not None:
        if directory_table_name is not None:
            directory_dataframe = directory_dataframe[(directory_dataframe.table_name==directory_table_name) & (directory_dataframe.directory_download =='Yes')].sort_values(by=['directory_column_order'])
            col_list = directory_dataframe['column_name'].tolist() # sort dataframe by sort order
            col_list_display = directory_dataframe['display_name'].tolist() # sort dataframe by sort order
            df = df[col_list]
            df.columns = col_list_display

    data_table = dash_table.DataTable(
                    id=table_id,
                    columns=[{"name": i, "id": i} for i in df.columns],
                    data=df.to_dict('records'),
                    sort_action="native",
                    sort_mode="multi",
                    page_action="native",
                    page_current= 0,
                    page_size= 10,
                    css=[{'selector': '.row', 'rule': 'margin: 0; flex-wrap: nowrap'},
                        {'selector':'.export','rule':'position:absolute;left:0px;bottom:-35px'}],
                    fixed_columns={'headers': True, 'data': 1},
                    style_as_list_view=True,
                    style_cell={'padding': '5px',
                        'maxWidth': '300px',
                        'font-family': 'Arial, Helvetica, sans-serif',
                        'textAlign': 'left',
                        'height': 'auto',
                        'whiteSpace': 'normal'
                               },
                    style_header={
                        'backgroundColor': 'rgb(230, 230, 230)',
                        'font-family': 'Arial, Helvetica, sans-serif',
                        'fontWeight': 'bold',
                        'font-size': '15px',
                        'height': '60px'
                    },
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'},
                         'backgroundColor': 'rgb(248, 248, 248)'
                         }
                        ],
                    style_data={'padding-left':'15px'},
                    style_table={'minWidth': '100%', 'maxWidth': 'none !important','overflowX': 'auto'},
                    export_format="xlsx",
                    export_headers="display"
                                    )
    return data_table

# figure Functions
def no_data_fig():
    return {
        "layout": {
            "xaxis": {
                "visible": False
            },
            "yaxis": {
                "visible": False
            },
            "annotations": [
                {
                    "text": "No matching data found",
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {
                        "size": 28
                    }
                }
            ]
        }
    }

def make_groupby_pie_chart(df,col, groupby_column = 'Organization', textinfo = None, color_scale = None, showlegend=False ):
    if df.empty:
        return no_data_fig()
    else:
        # Get display names for column
        df = pd.DataFrame(df.groupby(col)[groupby_column].count())
        df.reset_index(level=0, inplace=True)
        fig = px.pie(df, values=groupby_column, names=col, color_discrete_sequence=color_scale, title="{} grouped by {}s".format(col, groupby_column))
        fig.update_traces(textposition='inside', textinfo=textinfo)
        fig.update_layout(
                          #paper_bgcolor='rgba(190, 142, 146, 1)',
                          showlegend=showlegend,
                          #height=300,
                          #showlegend=False,
                          margin=dict(l=1, r=1, b=0),
                          )
        return fig

def make_pie_chart(df, name_col, value_col, title=None, textinfo = None, color_scale = None, showlegend=False ):
    if df.empty:
        return no_data_fig()
    else:
        fig = px.pie(df, values=value_col, names=name_col, color_discrete_sequence=color_scale, title=title)
        fig.update_traces(textposition='inside', textinfo=textinfo)
        fig.update_layout(
                          #paper_bgcolor='rgba(190, 142, 146, 1)',
                          showlegend=showlegend,
                          #height=300,
                          #showlegend=False,
                          margin=dict(l=1, r=1, b=0),
                          )
        return fig

# APP Functions
def make_bar(df, category_col_index, count_col_index, show_category = True, layout_direction = 'h', ascending=True, title = None, textposition='auto', marker_color="lightskyblue"):
    if df.empty:
        return mc.no_data_fig()
    else:
        if show_category:
            texttemplate='%{text} (%{value})'
            text = df.columns[category_col_index]
        else:
            texttemplate='(%{value})'
            text = None
        df = df.sort_values(by=df.columns[count_col_index], ascending=ascending)
        # make sure marker_color has enough entries
        if len(df) > len(marker_color):
            marker_color = marker_color * math.ceil(len(df)/len(marker_color))
        if layout_direction == 'h':
            x_col_index = count_col_index
            y_col_index = category_col_index
        else:
            x_col_index = category_col_index
            y_col_index = count_col_index
        fig = px.bar(df,
                     x = df.columns[x_col_index],
                     y = df.columns[y_col_index],
                     title = title,
                     text = text)
        fig.update_traces(marker_color=marker_color, texttemplate=texttemplate, textposition='auto')
        fig.update_yaxes(visible=False, showticklabels=False)
        fig.update_xaxes(visible=False, showticklabels=False)
        fig.update_layout(showlegend=False, margin=dict(l=20, r=20, t=30, b=0),
                          paper_bgcolor='rgba(0,0,0,0)',
                          plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig



def make_map(orgdata, lat_col, lon_col, choro_geojson,  featureidkey, state_name, choro_df, choro_df_location, choro_df_value, map_center_lat, map_center_lon, map_zoom = 5, hover_name = "Organization", hover_data = None):
    # Design point layer
    scatter_fig_hover_template = '<b>%{hovertext}</b>'
    scatter_fig = px.scatter_mapbox(orgdata, lat=lat_col, lon=lon_col,
                             hover_name=hover_name, hover_data=hover_data)
    scatter_fig.update_traces(hovertemplate=scatter_fig_hover_template)

    # Build choropleth layer
    fig = px.choropleth_mapbox(choro_df, geojson=choro_geojson,
              featureidkey=featureidkey,
              locations=choro_df_location,
            #   color=choro_df_value,
            #   color_continuous_scale = map_color_scale,
              opacity = 0.25,
               zoom=map_zoom,
              center = {"lat": map_center_lat, "lon": map_center_lon},
              mapbox_style="open-street-map")
    fig.update_traces(hovertemplate=f'<b>%{{{state_name}}}</b>')

    # add pt layer to map
    for item in range(0,len(scatter_fig.data)):
        fig.add_trace(scatter_fig.data[item])
    fig.update_layout(mapbox_style="open-street-map") # Ensure don't need token
    fig.update_layout(
        showlegend=False,
        autosize=True,
        height=350,
        margin=dict(l=20, r=20, t=20, b=0))

    return fig
