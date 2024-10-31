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

#Regex execption escaping
import re

# import local modules
import data_processing as dp

# ----------------------------------------------------------------------------
# DATA LOADING
# ----------------------------------------------------------------------------

## Load data
data_filepath = pathlib.Path(__file__).parent.absolute()
data_dictionary_filepath = os.path.join(data_filepath,'data','data_dictionary.xls')
data_records_filepath = os.path.join(data_filepath,'data','data_records.xls')
us_states_geojson = os.path.join(data_filepath,'data','us_state_geojson.txt')
tx_esc_geojson = os.path.join(data_filepath,'data','tx_esc.geojson')

# LOAD FILES
# geojson file
with open(tx_esc_geojson) as tx:
    tx_esc = json.load(tx)

with open(us_states_geojson) as response:
    states = json.load(response)

# Data Records
orgs = pd.read_excel(data_records_filepath, sheet_name ='Organizations')
programs = pd.read_excel(data_records_filepath, sheet_name = 'Programs')

# Since the bracket columns are generated from a formula to the end of the sheet, drop columns without an Organization or Program name
orgs['Organization'] = orgs['Organization'].replace('',np.nan)
orgs.dropna(subset=['Organization'])

programs['Program'] = programs['Program'].replace('',np.nan)
programs.dropna(subset=['Program'])

# load dictionary terms
directory_df = pd.read_excel(data_dictionary_filepath, sheet_name = 'columns_dictionary')
directory_df_cols_keep = ['table_name', 'column_name', 'display_name', 'multiple_values',
       'directory_column_order', 'directory_download', 'directory_display',
       'dashboard_filter', 'dashboard_pie_dropdown', 'pie_format', 'dashboard_bar_dropdown']
directory_df = directory_df[directory_df_cols_keep]
directory_df['directory_column_order'] = pd.to_numeric(directory_df['directory_column_order'])

controlled_terms_df = pd.read_excel(data_dictionary_filepath, sheet_name = 'terms_dictionary')
controlled_terms_df_cols_keep = ['table_name', 'column_name', 'term', 'display_term',
       'term_order']
controlled_terms_df = controlled_terms_df[controlled_terms_df_cols_keep]


# ----------------------------------------------------------------------------
# Special handling to create unique ids
# ----------------------------------------------------------------------------
orgs['orgID'] = orgs.index + 1
programs['programID'] = programs.index + 1

# Add OrgID column to Programs, merging on Organization
org_cols = ['Organization', 'orgID', 'State']
programs_org = orgs[org_cols]
programs = programs.merge(programs_org, how='left', on='Organization')

# ----------------------------------------------------------------------------
# Get geospatial point data
# ----------------------------------------------------------------------------
orgs.rename(columns={'Latitude ': 'Latitude', 'Longitude ': 'Longitude'}, inplace=True)

# ----------------------------------------------------------------------------
# Drop the columns that are to be excluded (column order = 0)
# ----------------------------------------------------------------------------
# Get list of columns to keep
orgs_cols_keep = ['orgID'] + list(directory_df[(directory_df.table_name == 'Organizations') & (directory_df.directory_column_order > 0)]['column_name'])
pg_cols_keep = ['programID','orgID','State'] + list(directory_df[(directory_df.table_name == 'Programs') & (directory_df.directory_column_order > 0)]['column_name'])

# subset the data
orgs_geo = orgs[['orgID', 'Latitude', 'Longitude']]
orgs = orgs[orgs_cols_keep]
programs = programs[pg_cols_keep]

# save copy of data with string values as strings for directory
orgs_directory = orgs.copy()
programs_directory = programs.copy()

# # Drop columms from directory using data dictionary logic
# # Get list of columns to keep
# orgs_directory_cols_keep = list(directory_df[(directory_df.table_name == 'Organizations') & (directory_df.directory_download =='Yes')]['column_name']) + ['orgID']
# orgs_directory_cols_keep_checked = [x for x in orgs_directory_cols_keep if x in set(orgs.columns)]
# programs_directory_cols_keep = list(directory_df[(directory_df.table_name == 'Programs') & (directory_df.directory_download =='Yes')]['column_name']) +  ['programID','orgID']
# programs_directory_cols_keep_checked = [x for x in programs_directory_cols_keep if x in set(programs.columns)]

# # subset the data
# orgs_directory = orgs_directory[orgs_directory_cols_keep_checked]
# programs_directory = programs_directory[programs_directory_cols_keep_checked]
# ----------------------------------------------------------------------------
# Modify data dictionary information
# ----------------------------------------------------------------------------

#Check and only keep portions of dictionary where fields are named to match incoming data
controlled_terms_df_orgs = controlled_terms_df[(controlled_terms_df['table_name'] == 'Organizations') &
             (controlled_terms_df['column_name'].isin(orgs.columns)) ]
controlled_terms_df_programs = controlled_terms_df[(controlled_terms_df['table_name'] == 'Programs') &
             (controlled_terms_df['column_name'].isin(programs.columns)) ]
controlled_terms_df = pd.concat([controlled_terms_df_orgs,controlled_terms_df_programs])


#Check and only keep portions of dictionary where fields are named to match incoming data
directory_df_orgs = directory_df[(directory_df['table_name'] == 'Organizations') & (directory_df['column_name'].isin(orgs.columns)) ].sort_values(by=['directory_column_order'])
directory_df_programs = directory_df[(directory_df['table_name'] == 'Programs') & (directory_df['column_name'].isin(programs.columns)) ].sort_values(by=['directory_column_order'])
directory_df = pd.concat([directory_df_orgs,directory_df_programs])

# Merge column display names back into controlled terms directory
controlled_terms_df = controlled_terms_df.merge(directory_df[['table_name','column_name','display_name']], how='left',on=['table_name','column_name'])

# ----------------------------------------------------------------------------
# LConvert string delimited fields into lists
# ----------------------------------------------------------------------------
multiterm_org_columns = dp.multiterm_columns(directory_df, "Organizations")
# Turn multiterm strings into lists
for col in multiterm_org_columns:
    orgs.loc[:,col] = orgs[col].astype(str)
    orgs.loc[:,col] = orgs[col].str.split(', ')

multiterm_prog_columns = dp.multiterm_columns(directory_df, "Programs")
# Turn multiterm strings into lists
for col in multiterm_prog_columns:
    programs.loc[:,col] = programs[col].astype(str)
    programs.loc[:,col] = programs[col].str.split(', ')

# ----------------------------------------------------------------------------
# generate data dictionary for data store
# ----------------------------------------------------------------------------

data_dict = {}
data_dict['Organizations'] = orgs.to_dict('records')
data_dict['Programs'] = programs.to_dict('records')

# ----------------------------------------------------------------------------
# Build data components for page
# ----------------------------------------------------------------------------

# Create dictionary of filter options {tablename:{columnname:{'display_name':display_name,'options'{data_column:display_name}}}}
filter_dict = {}
for org_or_prog in directory_df['table_name'].unique():
    col_to_display_map_df = directory_df[directory_df['table_name'] == org_or_prog][['column_name', 'display_name']].drop_duplicates()
    col_to_display_map_df = col_to_display_map_df.set_index('column_name')
    col_to_display_map_dict = col_to_display_map_df.to_dict('index')
    filter_dict[org_or_prog] = col_to_display_map_dict
    for k in filter_dict[org_or_prog].keys():
        term_to_display_map_df = controlled_terms_df[(controlled_terms_df['table_name'] == org_or_prog) & (controlled_terms_df['column_name'] == k)][['term', 'display_term']].drop_duplicates()
        tk_dict = term_to_display_map_df.set_index('term').T.to_dict('records')
        filter_dict[org_or_prog][k]['options'] = tk_dict

# COMPONENTS
#FILTERS
# Get dictionaries to use for Org and Program filter lists
# Limit the Organizations and Programs filters to those  flagged as 'Yes' in the directory_fields_dictionary file
# ALSO limit to columns that have controlled terms
filter_df = directory_df[directory_df['dashboard_filter']=='Yes'].sort_values(by=['table_name','directory_column_order'])
filter_criteria_df = filter_df[['table_name','column_name']].merge(controlled_terms_df[['table_name','column_name']].drop_duplicates(), how='inner', on=['table_name','column_name'])

ORG_FILTER_LIST = list(filter_criteria_df[filter_criteria_df.table_name == 'Organizations'].column_name)
ORG_FILTER_LIST_checked = [x for x in ORG_FILTER_LIST if x in set(orgs.columns)]
org_filter_dict_checked = {k: filter_dict['Organizations'].get(k, None) for k in (ORG_FILTER_LIST_checked)}

PROG_FILTER_LIST = list(filter_criteria_df[filter_criteria_df.table_name == 'Programs'].column_name)
PROG_FILTER_LIST_checked = list(set(PROG_FILTER_LIST) & set(programs.columns))
pg_filter_dict_checked = {k: filter_dict['Programs'].get(k, None) for k in (PROG_FILTER_LIST_checked)}


# Get dropdown options for pie chart and bar chart, i.e. the columns that are flagged as 'Yes' in the directory_fields_dictionary file
# PIE CHART OPTIONS
pie_dropdown_df = directory_df[directory_df['dashboard_pie_dropdown'] > 0].sort_values(by=['dashboard_pie_dropdown']).reset_index(drop=True)
pie_dropdown_dict = pie_dropdown_df[['column_name','display_name']].set_index('column_name').T.to_dict('records')

# BAR CHART OPTIONS
bar_dropdown_df = directory_df[directory_df['dashboard_bar_dropdown'] > 0 ].sort_values(by=['dashboard_bar_dropdown']).reset_index(drop=True)
bar_dropdown_dict = bar_dropdown_df[['column_name','display_name']].set_index('column_name').T.to_dict('records')

#make this dam file reboot!!!
