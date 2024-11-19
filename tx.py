import pandas as pd
import os
from policing_data_expl import *

config = { # 2016-2017 data only
    "grouping_keys": ['HA_N_FIRST_DRVR', 'HA_N_LAST_DRVR', 'HA_A_ADDRESS_DRVR', 'HA_A_CITY_DRVR', 'HA_A_STATE_DRVR', 'HA_A_ZIP_DRVR'],
    "descript": 'driver_race',
    "raw_data_csv": 'path-to-raw-csv', # replace with path to raw csv
    "grouped_csv_name": 'csv/tx_processed_grouped_driver_race_raw.csv',
    "hispanic_white_drivers_only_csv_name": 'csv/tx_processed_hispanic_white_drivers_driver_race.csv',
    "only_after_2016": True
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
tx_data = standardize_cols('TX', pd.read_csv(filepath, dtype=dtypes_dict))

if config['only_after_2016']:
    # only take rows that happened in the year 2016 and 2017
    before2016_mask = tx_data['date'].apply(lambda x: str(x)[:4] != '2016' and str(x)[:4] != '2017')
    only_2016_2017 = tx_data['date'].apply(lambda x: str(x)[:4] == '2016' or str(x)[:4] == '2017')
    b2016 = tx_data[before2016_mask]
    a2016 = tx_data[only_2016_2017]
    tx_data = a2016

# Construct filtered multiply-stopped dataset, and write the complete data to csv along with the filtered dataset
grouped_tx = group_df_by(tx_data, config['grouping_keys'], csv_filename='csv/tx_raw_with_driver_id_' + config['descript'] + '.csv')

def tx_cond(name, entries):
    """
    Only keep drivers 
    - with at least 2 entries (=at least 2 stops) and no more than 10 stops
    - assume non-null HA_N_FIRST_DRVR, HA_N_LAST_DRVR, HA_A_ADDRESS_DRVR, HA_A_CITY_DRVR, HA_A_STATE_DRVR, HA_A_ZIP_DRVR (=valid unique identifying features)
    """
    f, l, a, c, s, z = name
    return len(entries) >= 2 and len(entries) <= 10
        
grouped_csv_name = config['grouped_csv_name']
check_cond(grouped_tx, tx_cond, grouped_csv_name)

txgrouped_csv = pd.read_csv(grouped_csv_name)
tx_grouped = txgrouped_csv.groupby(config['grouping_keys'])

# Generate the race_str column
person_race_dict = generate_person_race_dict(tx_grouped)
# make the grouping_keys into a tuple so it can be used as a key per person in person_race_dict
tuple_lst = [tuple(keys) for keys in txgrouped_csv[config['grouping_keys']].values.tolist()]
race_str_col = [person_race_dict[(keys)] for keys in tuple_lst]

# call this new column race_str
txgrouped_with_race_str = txgrouped_csv.copy()
if ('race_str' not in txgrouped_with_race_str.columns):
    txgrouped_with_race_str.insert(2, "race_str", race_str_col, False)

# Filter down to inconsistently-perceived drivers, and write to csv
race_str_cond = txgrouped_with_race_str['race_str'].map(lambda x:x in {"Hispanic_White"})
hispanic_white_drivers = txgrouped_with_race_str.loc[txgrouped_with_race_str['search_conducted'].notnull() & race_str_cond]
write_to_csv(hispanic_white_drivers, config['hispanic_white_drivers_only_csv_name'])