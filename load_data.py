# Libraries
# Data
import os # Operating system library
import math
import numpy as np
import pandas as pd # Dataframe manipulations
import geopandas as gpd
import pathlib # file paths
# Geojson loading
from urllib.request import urlopen
import json

# Regex exception escaping
import re

# import local modules
import data_processing as dp

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------

# Load data
data_filepath = pathlib.Path(__file__).parent.absolute()
data_dictionary_filepath = os.path.join(data_filepath, 'data', 'data_dictionary.xls')
data_records_filepath = os.path.join(data_filepath, 'data', 'modified_file.xlsx')
us_states_geojson = os.path.join(data_filepath, 'data', 'us_state_geojson.txt')
tx_esc_geojson = os.path.join(data_filepath, 'data', 'tx_esc.geojson')

# Load geojson files
with open(tx_esc_geojson) as tx:
    tx_esc = json.load(tx)

with open(us_states_geojson) as response:
    states = json.load(response)

# Load data records for Organizations
orgs = pd.read_excel(data_records_filepath, sheet_name='Organizations')

# Remove rows without an Organization name
orgs['Organization'] = orgs['Organization'].replace('', np.nan)
orgs.dropna(subset=['Organization'], inplace=True)

# Load dictionary terms
directory_df = pd.read_excel(data_dictionary_filepath, sheet_name='columns_dictionary')
directory_df_cols_keep = ['table_name', 'column_name', 'display_name', 'multiple_values',
                          'directory_column_order', 'directory_download', 'directory_display',
                          'dashboard_filter', 'dashboard_pie_dropdown', 'pie_format', 'dashboard_bar_dropdown']
directory_df = directory_df[directory_df_cols_keep]
directory_df['directory_column_order'] = pd.to_numeric(directory_df['directory_column_order'])

controlled_terms_df = pd.read_excel(data_dictionary_filepath, sheet_name='terms_dictionary')
controlled_terms_df_cols_keep = ['table_name', 'column_name', 'term', 'display_term', 'term_order']
controlled_terms_df = controlled_terms_df[controlled_terms_df_cols_keep]

# ----------------------------------------------------------------------------
# Special handling to create unique ids
# ----------------------------------------------------------------------------
orgs['orgID'] = orgs.index + 1

# ----------------------------------------------------------------------------
# Get geospatial point data
# ----------------------------------------------------------------------------
orgs.rename(columns={'Latitude ': 'Latitude', 'Longitude ': 'Longitude'}, inplace=True)

# ----------------------------------------------------------------------------
# Drop columns that are to be excluded (column order = 0)
# ----------------------------------------------------------------------------
orgs_cols_keep = ['orgID'] + list(directory_df[(directory_df.table_name == 'Organizations') & (directory_df.directory_column_order > 0)]['column_name'])
orgs_geo = orgs[['orgID', 'Latitude', 'Longitude']]
orgs = orgs[orgs_cols_keep]

# save copy of data with string values as strings for directory
orgs_directory = orgs.copy()

# ----------------------------------------------------------------------------
# Modify data dictionary information
# ----------------------------------------------------------------------------

# Check and only keep portions of dictionary where fields are named to match incoming data
controlled_terms_df_orgs = controlled_terms_df[(controlled_terms_df['table_name'] == 'Organizations') &
                                               (controlled_terms_df['column_name'].isin(orgs.columns))]
controlled_terms_df = controlled_terms_df_orgs

directory_df_orgs = directory_df[(directory_df['table_name'] == 'Organizations') & (directory_df['column_name'].isin(orgs.columns))].sort_values(by=['directory_column_order'])
directory_df = directory_df_orgs

# Merge column display names back into controlled terms dictionary
controlled_terms_df = controlled_terms_df.merge(directory_df[['table_name', 'column_name', 'display_name']], how='left', on=['table_name', 'column_name'])

# ----------------------------------------------------------------------------
# Convert string-delimited fields into lists
# ----------------------------------------------------------------------------
multiterm_org_columns = dp.multiterm_columns(directory_df, "Organizations")
for col in multiterm_org_columns:
    orgs[col] = orgs[col].astype(str).str.split(', ')

# ----------------------------------------------------------------------------
# Generate data dictionary for data store
# ----------------------------------------------------------------------------

data_dict = {'Organizations': orgs.to_dict('records')}

# ----------------------------------------------------------------------------
# Build data components for page
# ----------------------------------------------------------------------------

# Create dictionary of filter options {tablename:{columnname:{'display_name':display_name,'options'{data_column:display_name}}}}
filter_dict = {}
col_to_display_map_df = directory_df[['column_name', 'display_name']].drop_duplicates().set_index('column_name')
filter_dict['Organizations'] = col_to_display_map_df.to_dict('index')

for k in filter_dict['Organizations'].keys():
    term_to_display_map_df = controlled_terms_df[(controlled_terms_df['column_name'] == k)][['term', 'display_term']].drop_duplicates()
    tk_dict = term_to_display_map_df.set_index('term').T.to_dict('records')
    filter_dict['Organizations'][k]['options'] = tk_dict

# COMPONENTS
# FILTERS
# Limit the Organizations filters to those flagged as 'Yes' in the directory_fields_dictionary file
filter_df = directory_df[directory_df['dashboard_filter'] == 'Yes'].sort_values(by=['directory_column_order'])
filter_criteria_df = filter_df[['column_name']].merge(controlled_terms_df[['column_name']].drop_duplicates(), how='inner', on=['column_name'])

ORG_FILTER_LIST = list(filter_criteria_df.column_name)
ORG_FILTER_LIST_checked = [x for x in ORG_FILTER_LIST if x in set(orgs.columns)]
org_filter_dict_checked = {k: filter_dict['Organizations'].get(k, None) for k in ORG_FILTER_LIST_checked}

# Dropdown options for pie chart and bar chart
pie_dropdown_df = directory_df[directory_df['dashboard_pie_dropdown'] > 0].sort_values(by=['dashboard_pie_dropdown']).reset_index(drop=True)
pie_dropdown_dict = pie_dropdown_df[['column_name', 'display_name']].set_index('column_name').T.to_dict('records')

bar_dropdown_df = directory_df[directory_df['dashboard_bar_dropdown'] > 0].sort_values(by=['dashboard_bar_dropdown']).reset_index(drop=True)
bar_dropdown_dict = bar_dropdown_df[['column_name', 'display_name']].set_index('column_name').T.to_dict('records')
