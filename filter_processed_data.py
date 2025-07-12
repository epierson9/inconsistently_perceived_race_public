import pandas as pd
import os
import hashlib
from pathlib import Path


def safe_hash_convert(x):
    """
    Convert to string for hashing while minimizing data changes
    """
    if pd.isna(x) or x is None or x == '' or x == 'nan':
        return None  # Keep None/NaN as None for hashing
    return str(x)

def anonymize_ids(df):
    """
    Anonymize driver and officer ids by creating new hashed columns
    while preserving original columns to match tx.py behavior
    """
    for col in ['officer_id', 'driver_id']:
        if col in df:
            print(f'MD5 hashing {col}')
            print('Original column info:')
            print(f'Data type: {df[col].dtype}')
            print(f'Sample values: {df[col].head(10).tolist()}')
            print(f'Unique values: {df[col].nunique()}')

            # Create hashed version without changing original
            hashed_col = f'{col}_hash'
            df[hashed_col] = df[col].apply(lambda x: hashlib.md5(safe_hash_convert(x).encode()).hexdigest() if safe_hash_convert(x) is not None else None)
            print(f'\nCreated {hashed_col} column')
            print(f'Unique hashed values: {df[hashed_col].nunique()}')
            print(f'Original unique values: {df[col].nunique()}')
            print(f'Difference: {df[hashed_col].nunique() - df[col].nunique()}')
            
            print('Replacing original column with hashed column')
            # Replace the original column with the hashed column
            df[col] = df[hashed_col]
        else:
            print(f'Skipping col {col} - does not exist in this df')
    print(df.head(10))
    return df

def int_or_none(x):
    """
    Return x cast as an int or if that errors out, just return none
    """
    try:
        return int(x)
    except:
        return None

def filter_processed_csv_columns():
    """
    Filter the processed csv columns to only include the columns we need for the analysis
    """

    csv_files = [
        'csv/az_grouped_Style_Year.csv',
        'csv/az_hispanic_white_drivers_Style_Year.csv',
        'csv/az_raw_with_driver_id_Style_Year.csv',
        'csv/co_grouped_mod_officer_id.csv',
        'csv/co_hispanic_white_drivers_only_mod.csv',
        'csv/co_raw_with_driver_id_mod_officer_id.csv',
        'csv/tx_processed_grouped_driver_race_raw.csv',
        'csv/tx_processed_hispanic_white_drivers_driver_race.csv',
        'csv/tx_raw_with_driver_id_driver_race.csv'
    ]

    # Dictionary to store column sets for each file
    column_sets = {}
    file_info = {}

    print("Reading CSV files and extracting column information...")

    # Read in each CSV file and get its columns
    for file_path in csv_files:
        if os.path.exists(file_path):
            try:
                # Read in the header to get the columns
                df = pd.read_csv(file_path, nrows=0)
                columns = set(df.columns)
                column_sets[file_path] = columns
                file_info[file_path] = {
                    'column_count': len(columns),
                    'file_size_mb': os.path.getsize(file_path) / (1024 * 1024)
                }
                print(f'Columns in file: {columns}:')
                print(f"✓ {file_path}: {len(columns)} columns, {file_info[file_path]['file_size_mb']:.1f} MB")
            except Exception as e:
                print(f"✗ Error reading {file_path}: {e}")
        else:
            print(f"✗ File not found: {file_path}")

    # Columns to keep in the processed csvs if they exist
    cols_to_keep = {'violation', 'search_conducted', 'county_name', 'stop_duration', 'officer_id',
                    'state', 'driver_race', 'stop_time','is_arrested', 'driver_id', 
                    'county_fips', 'stop_date', 'contraband_found', 'date', 'time'}


    print(f"\n=== CREATING FILTERED CSV FILES ===")
    output_dir = "csv/processed/"
    os.makedirs(output_dir, exist_ok=True)

    for file_path in csv_files:
        if file_path in column_sets:
            try:
                intersect_columns = set(column_sets[file_path]).intersection(cols_to_keep)
                # Read the file with only intersecting columns
                df = pd.read_csv(file_path, usecols=list(intersect_columns))
                if (file_path.startswith('csv/tx')):
                    print('Standardizing texas driver and officer ids')
                    for col in ['driver_id', 'officer_id']:
                        df[col] = df[col].map(lambda x: int_or_none(x)).astype('Int64')

                anonymized_df = anonymize_ids(df)
                print('Anonymized df')
                print(anonymized_df.head(10))

                # Create output filename
                filename = os.path.basename(file_path)
                output_path = os.path.join(output_dir, f"filtered_{filename}")

                # Save filtered CSV
                anonymized_df.to_csv(output_path, index=False, quotechar='"')
                print(f"✓ Created: {output_path} ({len(df)} rows) and the following columns:{intersect_columns}")

            except Exception as e:
                print(f"✗ Error processing {file_path}: {e}")

if __name__ == "__main__":
    filter_processed_csv_columns()