import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import statistics
import datetime
import os
from scipy.stats import ttest_ind, ttest_rel
from collections import Counter
from IPython.display import display
import statsmodels.api as sm
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS

# Functions used during the data exploration phase of the Policing Project

def get_percent_complete_column(df, c):
    """
    Given a pandas dataframe df and a column c,
    return the proportion of non-null values in c
    """
    return len(df.loc[df[c].notnull() & df[c].notna()]) / len(df)

def calc_complete_cols(state_data, grouping_key_list, driver_race_col='driver_race'):
    """
    Output the number of rows where all the columns in grouping_key_list have non-null entries
    """
    grouping_keys = grouping_key_list.copy()
    grouping_keys.append(driver_race_col)
    grouping_keys.append('search_conducted') # make sure only rows have non-null search_conducted values as well
    data_non_null = state_data[grouping_keys].notnull()
    data_complete_cols = data_non_null.all(axis=1) # only take the rows where all of these columns are complete

    print("#rows of complete columns:", sum(data_complete_cols))
    print(grouping_keys)
    print("#groups:", state_data.loc[data_complete_cols].groupby(grouping_key_list).ngroups)

def verify_raw_and_clean_match(raw_df, clean_df, key_list_raw, key_list_clean):
    """
    Assert that the raw_df and clean_df have the same number of rows and that they match on all entries for the columns in key_list
    """
    assert(len(raw_df) == len(clean_df))
    # compare each column separately
    assert(len(key_list_raw) == len(key_list_clean))
    for i in range(len(key_list_raw)):
        assert(raw_df[key_list_raw[i]].equals(clean_df[key_list_clean[i]]))

def print_unmatched_cols(d1, d2, cols1, cols2):
    """
    Given two dataframes d1 and d2 and their respective columns cols1 and cols2,
    check if the dataframes match on those columns and print out how many rows don't match"""
    for i in range(len(cols1)):
        try:
            verify_raw_and_clean_match(d1, d2, [cols1[i]], [cols2[i]])
            print(f'{i}: {cols1[i]}')
        except:
            print('ERROR: ', i, cols1[i])
            d = pd.DataFrame([d1[cols1[i]], d2[cols2[i]]]).T
            d.columns = ['raw', 'clean']
            print((d['raw'].isnull() != d['clean'].isnull()).sum(), "rows where raw is null and website is not or vice-versa")

            diff_vals = d['raw'].notna() & d['clean'].notna() & (d['raw'] != d['clean'])
            print(f'{(diff_vals).sum()} rows have different non-null values')

def get_state_data(state_name):
    """
    Given the state name, return the dataframes for
    - all drivers (raw data with complete grouping columns, includes driver_id)
    - multiply stopped drivers (filtered data)
    - multiply stopped drivers with white-Hispanic racial ambiguity (final dataset)
    """
    state_data_dict = {}
    if (state_name == 'az'):
        state_data_dict['all_drivers'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/az_raw_with_driver_id_Style_Year.csv')
        state_data_dict['multiply_stopped'] = pd.read_csv('az_grouped_Style_Year.csv')
        state_data_dict['racially_ambig'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/az_hispanic_white_drivers_Style_Year.csv')
    elif (state_name == 'co'):
        state_data_dict['all_drivers'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/co_raw_with_driver_id_mod_officer_id.csv')
        state_data_dict['multiply_stopped'] = pd.read_csv('co_grouped_mod_officer_id.csv')
        state_data_dict['racially_ambig'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/co_hispanic_white_drivers_only_mod.csv')
    elif (state_name == 'tx'):
        state_data_dict['all_drivers'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/tx_raw_with_driver_id_driver_race.csv')
        state_data_dict['multiply_stopped'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/tx_processed_grouped_driver_race_raw.csv')
        state_data_dict['racially_ambig'] = pd.read_csv('/share/pierson/non_public_open_policing_data/nora_work/tx_processed_hispanic_white_drivers_driver_race.csv')
    else:
        raise ValueError("Invalid state name")
    return state_data_dict

def plot_stop_freq_histogram(state_grouped):
    """
    Given the state dataframe grouped by driver_id, plot the histogram of the number of stops per person
    """
    num_stops_per_person = state_grouped.size()
    num_stops_per_person.hist(bins=range(2, max(num_stops_per_person)))
    plt.show()
    num_stops_between_2_and_5 = num_stops_per_person[num_stops_per_person.between(2, 5)]
    num_stops_between_2_and_5.hist(bins=range(2, max(num_stops_per_person)))
    plt.show()
    num_stops_more_than_5 = num_stops_per_person[num_stops_per_person > 5]
    num_stops_more_than_5.hist(bins=range(5, max(num_stops_per_person)))
    plt.show()

def plot_top_5_col_values(state_csv, stategrouped_csv, col_name, driver_race_col='driver_race'):
    """
    Display the top 5 most common values for the column col_name in the state_csv among white and Hispanic drivers as a table, along with the latex code to render it
    """
    top_5_vals = []
    index_list = []
    for label, data in zip(['All Drivers', 'Multiply Stopped Drivers'], [state_csv, stategrouped_csv]):
        top_5_vals.extend([data[col_name].value_counts().head(5).index])
        index_list.extend([f'{label} - white and Hispanic', f'{label} - white only', f'{label} - Hispanic only'])
    print(top_5_vals)
    display(pd.DataFrame({col_name: top_5_vals}, index=index_list))
    print(state_csv.loc[(state_csv[driver_race_col] == 'White') | (state_csv[driver_race_col] == 'Hispanic'), col_name].value_counts().head(5).index.to_latex())

def plot_top_5_col_values_all_states(az_data_dict, co_data_dict, tx_data_dict, col_name):
    """
    Display the top 5 most common values for the column col_name across all states as a table, along with the latex code to render it
    """
    for state, data_dict in zip(['AZ', 'CO', 'TX'], [az_data_dict, co_data_dict, tx_data_dict]):
        top_5_vals = []
        index_list = []
        for data_label, data in zip(['All Drivers', 'Multiply Stopped Drivers', 'Racially Ambiguous'], [data_dict['all_drivers'], data_dict['multiply_stopped'], data_dict['racially_ambig']]):
            top_5_vals.extend([data.loc[(data['driver_race'] == 'White') | (data['driver_race'] == 'Hispanic'), col_name].value_counts().head(5).index])
            index_list.extend([f'{data_label} - white and Hispanic'])
        print(state)
        display(pd.DataFrame({col_name: top_5_vals}, index=index_list))
        print(pd.DataFrame({col_name: top_5_vals}, index=index_list).to_dict())

def plot_search_rates_comparison(state, col, state_csv, stategrouped_csv, stategrouped_with_race_str, driver_race_col='driver_race'):
    """
    Plot mean column rates for white and Hispanic drivers
    """
    stat_list = []
    ci_width_list = []
    index_list = []
    for label, data in zip(['All Drivers', 'Multiply Stopped Drivers', 'Racially Ambiguous Drivers'], [state_csv, stategrouped_csv, stategrouped_with_race_str]):
        # multiplying both by 100 to display as percents
        stat_list.extend([
            100 * data.loc[(data[driver_race_col] == 'White') | (data[driver_race_col] == 'Hispanic'), col].mean(),
            100 * data.loc[data[driver_race_col] == 'White', col].mean(),
            100 * data.loc[data[driver_race_col] == 'Hispanic', col].mean()
        ])
        ci_width_list.extend([
            196 * data.loc[(data[driver_race_col] == 'White') | (data[driver_race_col] == 'Hispanic'), col].sem(),
            196 * data.loc[data[driver_race_col] == 'White', col].sem(),
            196 * data.loc[data[driver_race_col] == 'Hispanic', col].sem()
        ])
        index_list.extend([f'{label} - white and Hispanic', f'{label} - white only', f'{label} - Hispanic only'])
    display(pd.DataFrame({col: stat_list, 'CI Width': ci_width_list}, index=index_list))
    _, ax = plt.subplots(figsize=(7, 3))
    for (stat, ci_width, index) in zip(stat_list, ci_width_list, range(1, len(stat_list) + 1)):
        ax.errorbar(stat, index, xerr=ci_width, fmt='ko')
    label = 'Search Rate' if col == 'search_conducted' else 'Arrest Rate'
    plt.title(f'{state} {label} Comparison')
    plt.xlabel(label + ' (%)')
    plt.yticks(range(1,len(stat_list)+1), index_list)
    plt.tick_params(left = False) # remove y-axis ticks
    ax.yaxis.grid(True, linestyle='--') # but add horizontal gridlines
    plt.show()

def plot_search_rates_comparison_all_states(az_data_dict, co_data_dict, tx_data_dict, col):
    """
    Plot column rates for white and Hispanic drivers, across subsets of the population, pooled across all states
    """
    fig, ax = plt.subplots(figsize=(7, 2))
    data_label_list = ['All Drivers', 'Multiply Stopped Drivers', 'Racially Ambiguous Drivers']
    dict_keys = ['all_drivers', 'multiply_stopped', 'racially_ambig']
    index_list = [f'{data_label} - white and Hispanic drivers' for data_label in data_label_list]
    # create a dictionary of combined state datasets with col and driver_race only
    combined_datasets = {}
    cols = [col, 'driver_race']
    for data_key in dict_keys:
        if col == 'is_arrested':
            # texas doesn't have is_arrested
            combined_data = pd.concat([az_data_dict[data_key][cols], co_data_dict[data_key][cols]])
        else:
            combined_data = pd.concat([az_data_dict[data_key][cols], co_data_dict[data_key][cols], tx_data_dict[data_key][cols]])
        combined_datasets[data_key] = combined_data.loc[combined_data[col].notnull() & combined_data[col].notna() & combined_data['driver_race'].notnull() & combined_data['driver_race'].notna()]

    for idx, data in enumerate([combined_datasets['all_drivers'], combined_datasets['multiply_stopped'], combined_datasets['racially_ambig']]):
        display(data)
        stat_list = [
            100 * data.loc[(data['driver_race'] == 'White'), col].mean(),
            100 * data.loc[(data['driver_race'] == 'Hispanic'), col].mean()
        ]
        ci_width_list = [
            196 * data.loc[(data['driver_race'] == 'White'), col].sem(),
            196 * data.loc[(data['driver_race'] == 'Hispanic'), col].sem()
        ]
        display(pd.DataFrame({col: stat_list, 'CI Width': ci_width_list}, index=['White', 'Hispanic']))
        for (stat, ci_width, race_cond) in zip(stat_list, ci_width_list, ['White', 'Hispanic']):
            # label points with the state (only the first one to avoid repeats)
            ax.errorbar(stat, idx, label=race_cond if idx == 0 else None, xerr=ci_width, fmt='o', color='green' if race_cond == 'White' else 'blue')
    fig.legend(loc='upper right')
    label = 'Search Rate' if col == 'search_conducted' else 'Arrest Rate'
    plt.title(f'All States {label} Comparison')
    plt.xlabel(label + ' (%)')
    plt.yticks(range(len(index_list)), index_list)
    plt.tick_params(left = False) # remove y-axis ticks
    ax.yaxis.grid(True, linestyle='--') # but add horizontal gridlines
    plt.show()

def calc_mean_med_max_stops(state_grouped):
    """
    Given a grouped dataframe that's grouped on driver_id, output the min, max, mean, and median number of stops per person 
    """
    stops_per_person = state_grouped.size()

    print("Min # of Stops:", min(stops_per_person))
    print("Max # of Stops:", max(stops_per_person))
    print("Mean # of Stops:", statistics.mean(stops_per_person))
    print("Median # of Stops:", statistics.median(stops_per_person))

def int_or_none(x):
    """
    Helper for standardize_cols to cast x as an integer if possible, otherwise return None
    """
    try:
        return int(x)
    except:
        return None

def set_to_none_if_not_valid_date_or_is_jan_1(x):
    """
    Helper for standardize_cols to set the date to None if it's not a valid date or if it's January 1
    """
    try:
        cast_as_date = datetime.datetime.strptime(x, '%Y-%m-%d')
        if (cast_as_date.month == 1) and (cast_as_date.day == 1):
            # some of these people have valid dates but some don't so to be safe, set to None
            return None
        return x
    except:
        return None

def standardize_cols(state, d):
    """
    Standardize columns for each of the three states
    """
    if state == 'AZ':
        d['VehicleYear'] = d['VehicleYear'].map(lambda x:int_or_none(x)).astype('Int64')
        d['SubjectFirstName'] = d['SubjectFirstName'].str.upper()
        d['SubjectLastName'] = d['SubjectLastName'].str.upper()
        d['VehicleStyle'] = d['VehicleStyle'].str.upper()
        # not sure following line is necessary. 
        d = d.loc[(d['SubjectFirstName'].map(lambda x:len(str(x).strip()) > 0)) & (d['SubjectLastName'].map(lambda x:len(str(x).strip()) > 0))]
    elif state == 'CO':
        d.loc[d['DOB'] == '1900-01-01', 'DOB'] = None
        d['DOB'] = d['DOB'].map(set_to_none_if_not_valid_date_or_is_jan_1)
        d['driver_first_name'] = d['driver_first_name'].str.upper()
        d['driver_last_name'] = d['driver_last_name'].str.upper()
        d = d.loc[(d['driver_last_name'] != "NOT OBTAINED") & (d['driver_last_name'] != "--") & (d['driver_first_name'].map(lambda x:len(str(x).strip()) > 1)) & (d['driver_last_name'].map(lambda x:len(str(x).strip()) > 1))]
    elif state == 'TX':
        d = d.loc[d['date'].map(lambda x: int(x[:4]) >= 2016)].copy()
        d['HA_N_FIRST_DRVR'] = d['HA_N_FIRST_DRVR'].str.upper()
        d['HA_N_LAST_DRVR'] = d['HA_N_LAST_DRVR'].str.upper()
        d['HA_A_ADDRESS_DRVR'] = d['HA_A_ADDRESS_DRVR'].str.upper()
        d.loc[d['HA_A_ADDRESS_DRVR'] == 'UNKNOWN', 'HA_A_ADDRESS_DRVR'] = None
        d['HA_A_CITY_DRVR'] = d['HA_A_CITY_DRVR'].str.upper()
        d['HA_A_STATE_DRVR'] = d['HA_A_STATE_DRVR'].str.upper()
        d['HA_A_ZIP_DRVR'] = d['HA_A_ZIP_DRVR'].str.upper().map(lambda x:str(x)[:5] if x is not None else None) # need to format zips consistently; some have trailing zeroes. 
        d.loc[d['HA_A_ZIP_DRVR'].map(lambda x:len(x) != 5), 'HA_A_ZIP_DRVR'] = None # this filters out a minority of addresses which are nan or DATE or something. 
        d['driver_race'] = d['driver_race_raw'].str.capitalize()
        del d['driver_race_raw']
    return d

def write_to_csv(df, csv_filename):
    """
    Write pandas dataframe df to the csv named csv_filename
    Append without the header if the csv is not empty.
    Assume csv_filename is a relative path from the current directory
    """
    if os.path.isfile(csv_filename) and os.path.getsize(csv_filename) > 0:
        # append to the csv
        df.to_csv(csv_filename, index=False, mode='a', header=False)
    else:
        # just write to it
        df.to_csv(csv_filename, index=False)

def group_df_by(df, key_list, driver_race_col='driver_race', csv_filename=None):
    """
    Group pandas dataframe df based on the keys in key_list,
    return dataframe with all the rows with non-null/non-nan entries for
    each of the keys are grouped per the key_list along with
    driver_race, and add a driver_id column to the dataframe, numbered off
    from number 0 to the number of unique driver groups
    If csv_filename is not None, write the data with the driver_id column to the
    csv specified by csv_filename
    """
    notnull_df = df
    for key in key_list:
        notnull_df = notnull_df.loc[notnull_df[key].notnull() & notnull_df[key].notna()]
        print(f"Rows remaining after taking only non-null key {key}:", len(notnull_df))
    # don't group by the driver_race col or search_conducted, so do this outside the loop
    notnull_df = notnull_df.loc[notnull_df[driver_race_col].notnull() & notnull_df[driver_race_col].notna()]
    notnull_df = notnull_df.loc[notnull_df['search_conducted'].notnull() & notnull_df['search_conducted'].notna()]
    print(f"Rows remaining after taking only non-null key {driver_race_col}:", len(notnull_df))

    driver_id = notnull_df.groupby(key_list).ngroup().to_list()
    notnull_df.insert(0, 'driver_id', driver_id)
    notnull_df_with_driver_id = notnull_df
    print(f"Number of unique driver groups: {len(notnull_df['driver_id'].value_counts())}")
    if csv_filename is not None:
        notnull_df_with_driver_id.to_csv(csv_filename, index=False)
    return notnull_df_with_driver_id.groupby(key_list)

def check_cond(dfgroup, cond, csv_filename):
    """
    Check each group g in dfgroup against the condition cond
    If true, write g to the csv. Also keep track of the number of groups written
    to the csv
    Don't write anything to the csv otherwise
    """
    if os.path.isfile(csv_filename):
        print(f"{csv_filename} already exists, NO CHANGE")
    else:
        num_groups = 0
        for name, entries in dfgroup:
            if cond(name, entries):
                # assert first all entries have a non-null/non-nan driver id
                # and that there's only one driver_id per individual
                assert(entries['driver_id'].notnull().all())
                assert(entries['driver_id'].notna().all())
                assert(entries['driver_id'].nunique() == 1)
                assert(len(entries['driver_id'].value_counts()) == 1)
                num_groups += 1
                write_to_csv(entries, csv_filename)
        print(f"Number of groups written to csv: {num_groups}")

def calc_racial_ambig(state_grouped, driver_race_col='driver_race'):
    """"
    Return the number of rows and number of individuals who have more than one
    race recorded for their set of stops, and also record the number of stops
    for Hispanic/white drivers
    """
    num_racial_ambig_entries = 0
    num_racial_ambig_ind = 0
    num_hispanic_white_entries = 0
    for name, entries in state_grouped:
        if len(set(entries[driver_race_col])) > 1:
            num_racial_ambig_entries += len(entries)
            num_racial_ambig_ind += 1
        if len(set(entries[driver_race_col])) == 2 and 'Hispanic' in set(entries[driver_race_col]) and 'White' in set(entries[driver_race_col]):
            num_hispanic_white_entries += len(entries)

    print("# Racially Ambiguous - Entries:", num_racial_ambig_entries)
    print("# Racially Ambiguous - Individuals:", num_racial_ambig_ind)
    print("# Hispanic-white - Entries:", num_hispanic_white_entries)

def enumerate_racial_ambig(state_grouped, driver_race_col='driver_race'):
    """
    Return a Counter of the number of each kind of racially ambiguity
    """
    race_set_list = []

    for name, entries in state_grouped:
        if len(set(entries[driver_race_col])) > 1:
            # list of unique driver races per their set of stops
            race_set = list(set(entries[driver_race_col]))
            race_set.sort()
            # sort them and join with '_'
            race_set_list.append('_'.join(race_set))

    print("#Individuals -", len(race_set_list))

    return Counter(race_set_list)

def generate_person_race_dict(state_grouped, driver_race_col='driver_race'):
    """
    Return a dictionary with each person (identified according to their grouped
    attributes) and their race(s) for all their stops
    """
    person_race_dict = {} # records race(s) per person for their stops

    for name, entries in state_grouped:
        if len(set(entries[driver_race_col])) == 1:
            # no racial ambiguity
            person_race_dict[name] = list(set(entries[driver_race_col]))[0]
        else:
            # racially ambiguous driver - record all this driver's races
            # (same procedure as in enumerate_racial_ambig)
            race_set = list(set(entries[driver_race_col]))
            race_set.sort()
            person_race_dict[name] = ('_'.join(race_set))

    print("#Individuals -", len(person_race_dict))
    return person_race_dict

def generate_state_stats(stategrouped_with_race_str, grouping_cols, driver_race_col='driver_race'):
    """
    Return a list of tuples of the stat and dictionaries with the rates of 
    is_arrested, search_conducted for a given state, across different segments 
    of the population
    """
    # ambig_race_set = more than 1 race in the race string, just subtract off the singleton race strings
    ambig_race_set = set(stategrouped_with_race_str['race_str']).difference(set(stategrouped_with_race_str[driver_race_col]))

    stats_dict_lst = []

    race_list_sets_dict = {} # each race_str is an abbreviation and key to a list of tuples (race_str_set, driver_race_set) pairs
    # where the race_str_set is used to filter with column race_str and driver_race_set is used to filter with the column driver_race
    for race_str in ['White', 'Hispanic']:
        race_list_sets_dict[race_str] = [({race_str}, {race_str})]
    race_list_sets_dict['White_Hispanic'] = [({"Hispanic_White"}, {"White"}), ({"Hispanic_White"}, {"Hispanic"}), ({"Hispanic_White"}, {"Hispanic", "White"})]
    race_list_sets_dict['Ambiguous'] = [(ambig_race_set, set(stategrouped_with_race_str[driver_race_col]))]

    col_lst = []
    if 'is_arrested' in stategrouped_with_race_str.columns:
        col_lst += ['is_arrested']
    if 'search_conducted' in stategrouped_with_race_str.columns:
        col_lst += ['search_conducted']
    print(col_lst)

    for col in col_lst:
        race_frac_dict = {'Name': [], 'Rate': [], 'Std Err': [], '# Entries': [], '# Groups': []}
        for race_str, race_lists in race_list_sets_dict.items():
            for race_str_set, driver_race_set in race_lists:
                # take drivers of that race_str (all races from their stops)
                # and for Hispanic-white drivers, also split based on white, Hispanic, along with all stops
                sorted_driver_lst = list(driver_race_set) # to keep set in alphabetical order
                sorted_driver_lst.sort()
                race_frac_dict['Name'].append(race_str + '_' + col + '_' + ''.join(sorted_driver_lst))
                race_str_cond = stategrouped_with_race_str['race_str'].map(lambda x:x in race_str_set)
                driver_race_cond = stategrouped_with_race_str[driver_race_col].map(lambda x:x in driver_race_set)
                race_frac_dict['Rate'].append(stategrouped_with_race_str.loc[race_str_cond & driver_race_cond, col].mean())
                race_frac_dict['Std Err'].append(stategrouped_with_race_str.loc[race_str_cond & driver_race_cond, col].sem(axis=0))
                race_frac_dict['# Entries'].append(len(stategrouped_with_race_str.loc[race_str_cond & driver_race_cond]))
                race_frac_dict['# Groups'].append(stategrouped_with_race_str.loc[race_str_cond & driver_race_cond].groupby(grouping_cols).ngroups)
        # also run stats for the whole dataframe
        race_frac_dict['Name'].append('whole_' + col)
        race_frac_dict['Rate'].append(stategrouped_with_race_str[col].mean())
        race_frac_dict['Std Err'].append(stategrouped_with_race_str[col].sem(axis=0))
        race_frac_dict['# Entries'].append(len(stategrouped_with_race_str))
        race_frac_dict['# Groups'].append(stategrouped_with_race_str.groupby(grouping_cols).ngroups)
        stats_dict_lst.append((col, race_frac_dict))

    return stats_dict_lst

def ttest_unpaired(stategrouped_with_race_str, driver_race_col='driver_race'):
    """
    Return a t-test on the search and arrest rates of white-Hispanic drivers
    identified as white versus Hispanic at stops
    """
    # Only take the stops where the driver was identified as either white or
    # Hispanic
    stat_dict = {}

    stat_lst = []
    if 'is_arrested' in stategrouped_with_race_str.columns:
        stat_lst += ['is_arrested']
    if 'search_conducted' in stategrouped_with_race_str.columns:
        stat_lst += ['search_conducted']
    print(stat_lst)

    for stat_name in stat_lst:
        non_null = stategrouped_with_race_str[stat_name].notnull()

        race_str_cond = stategrouped_with_race_str['race_str'].map(lambda x:x in {"Hispanic_White"})
        print(len(stategrouped_with_race_str.loc[race_str_cond]))

        white_race_cond = race_str_cond & stategrouped_with_race_str[driver_race_col].map(lambda x:x in {"White"})
        hispanic_race_cond = race_str_cond & stategrouped_with_race_str[driver_race_col].map(lambda x:x in {"Hispanic"})

        # taking the rows where drivers were identified as white versus when they were Hispanic
        # (the length of white stops may not necessarily equal the number of Hispanic stops)
        white_search_cond = stategrouped_with_race_str.loc[non_null & white_race_cond, stat_name]
        print("white stops:", len(white_search_cond))
        # take means to automatically exclude nan values
        print(f"white {stat_name}:", white_search_cond.mean())

        hispanic_search_cond = stategrouped_with_race_str.loc[non_null & hispanic_race_cond, stat_name]
        print("Hispanic stops:", len(hispanic_search_cond))
        print(f"Hispanic {stat_name}:", hispanic_search_cond.mean())

        print("white vec:\n", white_search_cond)
        print("Hispanic vec:\n", hispanic_search_cond)
        print(f"Var (white, hispanic): ({np.var(white_race_cond)}, {np.var(hispanic_race_cond)})")
        
        stat_dict[stat_name] = ttest_ind(white_search_cond.astype('bool'), hispanic_search_cond.astype('bool'))
    return stat_dict

def ttest_paired(state_grouped, driver_race_col='driver_race'):
    """
    Return a paired t-test statistic on the search/arrest rates of 
    white-Hispanic drivers identified as white versus Hispanic at stops
    """
    stat_dict = {}

    # only add the columns that are actually present as columns
    stat_lst = []
    columns = state_grouped.obj.columns
    print(columns)
    if 'is_arrested' in columns:
        stat_lst += ['is_arrested']
    if 'search_conducted' in columns:
        stat_lst += ['search_conducted']
    print(stat_lst)

    for stat_name in stat_lst:
        white_search_rate = []
        hispanic_search_rate = []
        for _, entries in state_grouped:
            # only get the individuals perceived race Hispanic+white
            if len(set(entries[driver_race_col])) == 2 and "Hispanic" in set(entries[driver_race_col]) and "White" in set(entries[driver_race_col]):
                non_null = entries[stat_name].notnull()
                
                white_race_cond = entries[driver_race_col].map(lambda x: x in {"White"})
                white_searched_stops = entries.loc[non_null & white_race_cond, stat_name].mean()

                hispanic_race_cond = entries[driver_race_col].map(lambda x: x in {"Hispanic"})
                hispanic_searched_stops = entries.loc[non_null & hispanic_race_cond, stat_name].mean()

                white_search_rate.append(white_searched_stops)
                hispanic_search_rate.append(hispanic_searched_stops)
        # white_search_rate and hispanic_search_rate have the same length (the number of Hispanic-white individuals)
        # they are the average number of searches for when the individual was identified as white versus when they were identified as Hispanic
        print(len(white_search_rate), len(hispanic_search_rate))
        print(white_search_rate, '\n', hispanic_search_rate)
        # nans will occur if there are no entries for white_search or hispanic_search
        # so omit them in the paired t-test
        stat_dict[stat_name] = ttest_rel(white_search_rate, hispanic_search_rate, nan_policy='omit')
    return stat_dict

def display_driver_race_stats(stategrouped_csv, driver_race_col='driver_race'):
    """
    Plot distribution of race for the traffic stops of the state
    Return the driver_race_stats
    """
    norm_race_stats = stategrouped_csv[driver_race_col].value_counts(normalize=True) * 100
    print(norm_race_stats)

    stategrouped_csv[driver_race_col].value_counts(normalize=True).plot(kind='bar')
    plt.show()
    return norm_race_stats

def get_state_stats(state_csv, race_col, grouping_cols, driver_race_col='driver_race'):
    """
    From the state csv, insert a race_col and 
    return the statistics of the is_arrested and search_conducted
    for different segments of the population
    """
    stategrouped_with_race_str = state_csv.copy()
    # race_str is the string that contains all the races that individual was identified as
    stategrouped_with_race_str.insert(2, "race_str", race_col, False)

    return generate_state_stats(stategrouped_with_race_str, grouping_cols, driver_race_col)

def plot_state_stats(state_stats_dict_lst, state, save_fig=False, use_rate=False):
    """
    Plot state statistics of is_arrested and search_conducted
    use_rate=False if plotting percents, True otherwise
    save_fig=True if saving the figure, False otherwise
    """
    # determine which stats are in this list
    stats_lst = []
    for stat_name, _ in state_stats_dict_lst:
        stats_lst.append(stat_name)
    print(stats_lst)

    # Get the ambiguous stat names
    ambig_stat_name_lst = [name for _, state_stats_dict in state_stats_dict_lst for name in state_stats_dict['Name'] if name.startswith('Ambiguous')]

    # lots of label substitutions for the graphs
    stats_to_title_dict = {
        'is_arrested': 'Arrest Rates',
        'search_conducted': 'Search Rates'
    }

    plt_title_lst = []
    for stat_name in stats_lst:
        plt_title_lst.append((f'{state} {stats_to_title_dict[stat_name]} (%) across Groups', f'{state} {stats_to_title_dict[stat_name]} (%) for Hispanic+white Drivers'))

    general_dict_lst = []
    for i, stat in enumerate(stats_lst):
        general_dict_lst.append({
            f'White_{stat}_White': "Drivers' perceived only white",
            f'Hispanic_{stat}_Hispanic': "Drivers' perceived only Hispanic",
            f'White_Hispanic_{stat}_White': "Drivers' perceived Hispanic+white, stops perceived white",
            f'White_Hispanic_{stat}_Hispanic': "Drivers' perceived Hispanic+white, stops perceived Hispanic",
            f'White_Hispanic_{stat}_HispanicWhite': "Drivers' perceived Hispanic+white, all stops",
            ambig_stat_name_lst[i]: "Drivers perceived as multiple races, all stops",
            f'whole_{stat}': "All drivers, all stops"
        })

    label_dict_lst = []
    for stat in stats_lst:
        label_dict_lst.append({
            f'White_Hispanic_{stat}_White': 'Stops w/ perceived race white',
            f'White_Hispanic_{stat}_Hispanic': 'Stops w/ perceived race Hispanic',
            f'White_Hispanic_{stat}_HispanicWhite': 'All stops'
        })

    # plot the stats
    for i, (stat_name, stats_dict) in enumerate(state_stats_dict_lst):
        print(stat_name) # make stat_name into the dataframe
        df = pd.DataFrame(stats_dict)
        if use_rate:
            sort_by_col = 'Rate'
        else: # multiply rates and std error by 100
            df['Rate'] *= 100
            df['Std Err'] *= 100
            df.rename(columns={'Rate': 'Percent (%)'}, inplace=True)
            sort_by_col = 'Percent (%)'
        display(df.sort_values(sort_by_col))

        gen_title, hw_title = plt_title_lst[i]

        # Plot the general stats
        _, ax = plt.subplots(figsize=(7, 4))
        sorted_vals = df.sort_values(sort_by_col)
        num_range = np.arange(len(sorted_vals))
        # plot the Hispanic-white stats in blue, everything else black
        colors = ['blue' if 'White_Hispanic' in name else 'black' for name in sorted_vals['Name']]
        for (stat, num, std_err, c) in zip(sorted_vals[sort_by_col], num_range, sorted_vals['Std Err'], colors):
            ax.errorbar(stat, num, xerr=std_err, fmt='o', color=c)
        # set the labels for the y-axis
        general_labels = [general_dict_lst[i][name] for name in sorted_vals['Name']]
        ax.set_yticks(num_range, labels=general_labels)
        plt.tick_params(left = False) # remove y-axis ticks
        plt.title(gen_title)
        ax.yaxis.grid(True, linestyle='--')
        if save_fig: # take the first 5 characters of the title for the figure
            fig_name = gen_title[:5] + '_gen'
            plt.savefig(f'lab_diagrams/{fig_name}.pdf', bbox_inches='tight')
        plt.show()

        # Plot the white/Hispanic stats as a separate plot
        white_hispanic_only = df.loc[df['Name'].str.contains('White_Hispanic')]
        display(white_hispanic_only)
        num_range = np.arange(len(white_hispanic_only))
        _, ax = plt.subplots(figsize=(7, 2))
        ax.errorbar(white_hispanic_only[sort_by_col], num_range, xerr=white_hispanic_only['Std Err'], fmt='o', color='blue')
        stat_labels = [label_dict_lst[i][name] for name in white_hispanic_only['Name']]
        ax.set_yticks(num_range, labels=stat_labels)
        ax.yaxis.grid(True, linestyle='--')
        plt.tick_params(left = False) # remove y-axis ticks
        plt.title(hw_title)
        if save_fig:
            fig_name = hw_title[:5]
            plt.savefig(f'lab_diagrams/{fig_name}.pdf', bbox_inches='tight')
        plt.show()

def regress(stategrouped_with_race_str, dep_var, cols, controls, model_name, useFixedEffects=True, stop_date_col='stop_date', driver_race_col='driver_race', stop_time_col='stop_time', drop_absorbed=False):
    """
    Return a fixed effects model of the dependent var, fit on state data that
    is controlling for the variables in the controls, plus fixed effects
    """
    print(f'drop_absorbed: {drop_absorbed}')
    # only take stops of Hispanic-white drivers and non-null dep_var
    race_str_cond = stategrouped_with_race_str['race_str'].map(lambda x:x in {"Hispanic_White"})
    hispanic_white_drivers = stategrouped_with_race_str.loc[race_str_cond & stategrouped_with_race_str[dep_var].notnull() & stategrouped_with_race_str[dep_var].notna()]
    print('number rows', len(hispanic_white_drivers))
    print(f'number {dep_var}', len(hispanic_white_drivers[dep_var].loc[hispanic_white_drivers[dep_var] == True]))

    # construct binary_race_and_id with columns "Hispanic", "White", "driver_id", "search_conducted"
    # and all of the cols
    # set stop_date_col to be a datetime object, and set the index to be driver_id and stop_date_col
    binary_race_and_id = pd.get_dummies(hispanic_white_drivers[driver_race_col])
    binary_race_and_id.insert(0, 'driver_id', hispanic_white_drivers['driver_id'])
    binary_race_and_id.insert(0, dep_var, hispanic_white_drivers[dep_var])
    binary_race_and_id.insert(4, stop_date_col, hispanic_white_drivers[stop_date_col])

    for col in cols:
        if col == 'hour_of_day':
            # construct hour_of_day from stop_time as a decimal
            # like 14:15 will be hour of day 14.25
            binary_race_and_id['hour_of_day'] = hispanic_white_drivers[stop_time_col].apply(lambda x: int(x.split(':')[0]) * 60 + int(x.split(':')[1])) / 60.
            assert (min(binary_race_and_id['hour_of_day']) >= 0) and (max(binary_race_and_id['hour_of_day']) <= 24)
        else:
            binary_race_and_id.insert(0, col, hispanic_white_drivers[col])
    print(binary_race_and_id.columns)

    binary_race_and_id[stop_date_col] = pd.to_datetime(binary_race_and_id[stop_date_col])

    binary_race_and_id = binary_race_and_id.set_index(['driver_id', stop_date_col])
    # (Optional) set the binary_race_and_id columns all to be bools

    # set search_conducted to be bool type in case it's in int64
    binary_race_and_id[dep_var] = binary_race_and_id[dep_var].astype(bool)

    # binary_race_and_id = binary_race_and_id.astype(bool)
    print(binary_race_and_id.shape)

    # construct the model string from the controls, and the EntityEffects if useFixedEffects is True for dep_var
    controls_str = "+".join(controls)
    model_str = f"{dep_var} ~ 1 + Hispanic{' + %s' % controls_str if len(controls_str) > 0 else ''}{' + EntityEffects' if useFixedEffects else ''}"
    
    print(model_str)

    model = PanelOLS.from_formula(f"{model_str}", data=binary_race_and_id, drop_absorbed=drop_absorbed)
    res = model.fit()
    res.model_name = model_name
    display(res.summary)
    return res

def make_sensitivity_dot_plot(list_of_models, coef_to_plot, title):
    # make plot
    plt.figure(figsize=(6, 0.5*len(list_of_models)))
    yticks = []
    for i, res in enumerate(list_of_models):
        coef = res.params[coef_to_plot]
        ci = res.conf_int().loc[coef_to_plot].values
        # plot each figure on its own horizontal "track" at i
        plt.plot(coef, i, 'ko')
        plt.plot(ci, [i, i], 'k-')
        yticks.append(res.model_name)
    plt.axvline(0, color='k', linestyle='--')
    plt.yticks(range(len(list_of_models)), yticks)
    if coef_to_plot == 'Hispanic':
        plt.xlabel('Hispanic - white search rate difference')
    else:
        raise ValueError('Unknown coef_to_plot')
    plt.title(title)
    plt.show()

def regress_statsmodel(stategrouped_with_race_str, dep_var):
    """
    Use the statsmodels package to confirm the linearmodels package results
    Modeling fixed effects as binary variables for each of the driver_ids
    """
    race_str_cond = stategrouped_with_race_str['race_str'].map(lambda x:x in {"Hispanic_White"})
    hispanic_white_drivers = stategrouped_with_race_str.loc[race_str_cond & stategrouped_with_race_str[dep_var].notnull()]
    display(hispanic_white_drivers)
    print('number rows', len(hispanic_white_drivers))
    print('number searched', len(hispanic_white_drivers['search_conducted'].loc[hispanic_white_drivers['search_conducted'] == True]))

    # make the driver_id columns not just numbers
    id_num = hispanic_white_drivers['driver_id'].apply(lambda n: f"id{str(n)}")
    hispanic_white_drivers.insert(0, 'id_num', id_num)
    binary_id_and_race = pd.get_dummies(hispanic_white_drivers['id_num'])
    id_cols = binary_id_and_race.columns.to_list()
    id_cols = id_cols[:-1] # remove one of the ids since we have the intercept term
    
    binary_id_and_race['Hispanic'] = pd.get_dummies(hispanic_white_drivers['driver_race'])['Hispanic']
    binary_id_and_race[dep_var] = hispanic_white_drivers[dep_var]
    binary_id_and_race[dep_var] = binary_id_and_race[dep_var].astype('int64')

    display(binary_id_and_race)

    # add all the binary columns in the ids_string
    ids_string = "+".join(id_cols)
    mod = smf.ols(formula=f"{dep_var} ~ 1 + Hispanic + {ids_string}", data=binary_id_and_race)
    res = mod.fit()
    return res.summary()