import pandas as pd
import os
from policing_data_expl import *

config = { # reprocessed officer id
    "grouping_keys": ['driver_first_name', 'driver_last_name', 'DOB'],
    "descript": "_mod_officer_id",
    "raw_data_csv": 'path-to-raw-csv', # replace with path to raw csv
    "hispanic_white_drivers_only_csv_name": 'csv/co_hispanic_white_drivers_only_mod.csv'
}

# Create the folder for the csv files if it doesn't exist
if not os.path.exists('csv/'):
    os.makedirs('csv/')
    print('Folder for csv files created successfully.')
else:
    print('Folder for csv files already exists.')

# Load data
filepath = config['raw_data_csv']
dtypes_dict = {k:str for k in config['grouping_keys']}
co_data = standardize_cols('CO', pd.read_csv(filepath, dtype=dtypes_dict))

# Construct filtered multiply-stopped dataset, and write the complete data to csv along with the filtered dataset
grouped_co = group_df_by(co_data, config['grouping_keys'], csv_filename='csv/co_raw_with_driver_id' + config['descript'] + '.csv')

def co_cond(name, entries):
    """
    Only keep drivers 
    - with at least 2 entries (=at least 2 stops but no more than 10 stops)
    - non-null + custom logic for driver_first_name, driver_last_name, DOB (=valid unique identifying features)
    """
    f, l, dob = name
    return len(entries) >= 2 and len(entries) <= 10 and \
        (l != "NOT OBTAINED" and l != "--" and len(f) > 1 and len(l) > 1)
        
csv_name = 'csv/co_grouped' + config['descript'] + '.csv'
check_cond(grouped_co, co_cond, csv_name)

cogrouped_csv = pd.read_csv(csv_name)
co_grouped = cogrouped_csv.groupby(config['grouping_keys'])

# Generate the race_str column
person_race_dict = generate_person_race_dict(co_grouped)
# make the grouping_keys into a tuple so it can be used as a key per person in person_race_dict
tuple_lst = [tuple(keys) for keys in cogrouped_csv[config['grouping_keys']].values.tolist()]
race_str_col = [person_race_dict[(keys)] for keys in tuple_lst]

# call this new column race_str
cogrouped_with_race_str = cogrouped_csv.copy()
if ('race_str' not in cogrouped_with_race_str.columns):
    cogrouped_with_race_str.insert(2, "race_str", race_str_col, False)

# Filter down to inconsistently-perceived drivers, and write to csv
race_str_cond = cogrouped_with_race_str['race_str'].map(lambda x:x in {"Hispanic_White"})
hispanic_white_drivers = cogrouped_with_race_str.loc[race_str_cond]
write_to_csv(hispanic_white_drivers, config['hispanic_white_drivers_only_csv_name'])