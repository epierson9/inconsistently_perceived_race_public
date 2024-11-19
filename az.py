import pandas as pd
import os
from policing_data_expl import *

config = { # VehicleStyle and Vehicle Year
    "grouping_keys": ['SubjectFirstName', 'SubjectLastName', 'VehicleStyle', 'VehicleYear'],
    "descript": "_Style_Year",
    "raw_data_csv": 'path-to-raw-csv', # replace with path to raw csv
    "hispanic_white_drivers_only_csv_name": "csv/az_hispanic_white_drivers_Style_Year.csv",
    "standardize_format": True
}

# Create the folder for the csv files if it doesn't exist
if not os.path.exists('csv/'):
    os.makedirs('csv/')
    print('Folder for csv files created successfully.')
else:
    print('Folder for csv files already exists.')

# Load data
filepath =  config['raw_data_csv']
dtypes_dict = {k:str for k in config['grouping_keys']}
az_data = standardize_cols('AZ', pd.read_csv(filepath, dtype=dtypes_dict))

# Construct filtered multiply-stopped dataset, and write the complete data to csv along with the filtered dataset
grouped_az = group_df_by(az_data, config['grouping_keys'], csv_filename='csv/az_raw_with_driver_id' + config['descript'] + '.csv')

def az_cond(name, entries):
    """
    Only keep drivers 
    - with at least 2 entries (=at least 2 stops) but no more than 10 stps
    - non-null + custom logic for driver_first_name, driver_last_name, DOB (=valid unique identifying features)
    """
    return len(entries) >= 2 and len(entries) <= 10
        
filtered_csv_name = 'csv/az_grouped' + config['descript'] + '.csv'
check_cond(grouped_az, az_cond, filtered_csv_name)

azgrouped_csv = pd.read_csv(filtered_csv_name)
azgrouped_csv[config['grouping_keys']] = azgrouped_csv[config['grouping_keys']].astype(str)
az_grouped = azgrouped_csv.groupby(config['grouping_keys'])

# Generate the race_str column
person_race_dict = generate_person_race_dict(az_grouped)
# make the grouping_keys into a tuple so it can be used as a key per person in person_race_dict
tuple_lst = [tuple(keys) for keys in azgrouped_csv[config['grouping_keys']].values.tolist()]
race_str_col = [person_race_dict[(keys)] for keys in tuple_lst]

# call this new column race_str
azgrouped_with_race_str = azgrouped_csv.copy()
if ('race_str' not in azgrouped_with_race_str.columns):
    azgrouped_with_race_str.insert(2, "race_str", race_str_col, False)

# Filter down to inconsistently-perceived drivers, and write to csv
race_str_cond = azgrouped_with_race_str['race_str'].map(lambda x:x in {"Hispanic_White"})
hispanic_white_drivers = azgrouped_with_race_str.loc[race_str_cond]
write_to_csv(hispanic_white_drivers, config['hispanic_white_drivers_only_csv_name'])