library(xtable)
library(data.table)
library("magrittr")
library(scales)
library(dplyr)
library(stringr)
library(tidyr)

# Code for creating the descriptive stats table for the paper

az_data = c(
  'path-to-AZ-data.csv',
  'az_grouped_Style_Year.csv',
  'az_hispanic_white_drivers_Style_Year.csv'
)
names(az_data) = c('Raw', 'Filtered', 'Hispanic_White')

co_data = c(
  'path-to-CO-data.csv',
  'co_grouped_mod_officer_id.csv',
  'co_hispanic_white_drivers_only_mod.csv'
)
names(co_data) = c('Raw', 'Filtered', 'Hispanic_White')

tx_data = c(
  'path-to-TX-data.csv',
  'tx_processed_grouped_driver_race_raw.csv',
  'tx_processed_hispanic_white_drivers_driver_race.csv'
)
names(tx_data) = c('Raw', 'Filtered', 'Hispanic_White')

overall_data = c(
  # 'overall_raw_mod_co.csv',
  'overall_grouped_mod_co.csv',
  'overall_hispanic_white_drivers_mod_co.csv'
)
names(overall_data) = c('Filtered', 'Hispanic_White') # c('Raw', 'Filtered', 'Hispanic_White')

fix_cols = function(state, df) {
  if (state == 'az') {
    df$VehicleYear = as.numeric(df$VehicleYear) # convert to numeric
    # make first name, last name, vehicle style all uppercase
    df$SubjectFirstName = str_to_upper(df$SubjectFirstName)
    df$SubjectLastName = str_to_upper(df$SubjectLastName)
    df$VehicleStyle = str_to_upper(df$VehicleStyle)
  } else if (state == 'co') {
    print('co dimensions before fix cols')
    print(nrow(df))
    df = df %>% mutate(DOB = ifelse(as.character(DOB) == '1900-01-01', NA, DOB))
    df = df %>% mutate(DOB = as.Date(DOB, format='%Y-%m-%d'))
    # check if substring is 01-01, then make it NA
    df = df %>% mutate(DOB = ifelse(format(DOB, format="%m-%d") == "01-01", NA, DOB))
    
    df$driver_first_name = str_to_upper(as.character(df$driver_first_name))
    df$driver_last_name = str_to_upper(as.character(df$driver_last_name))
    # filter out rows with driver_last_name as 'NOT OBTAINED' or '--' or with less than 2 characters in driver_first_name or driver_last_name
    df = df %>% filter(!(driver_last_name == 'NOT OBTAINED' | 
                         driver_last_name == '--' | 
                         (nchar(str_trim(as.character(driver_first_name))) < 2) | 
                         (nchar(str_trim(as.character(driver_last_name))) < 2)))
  } else if (state == 'tx') {
    # add the stop_date and stop_time columns
    df$stop_date = df$date
    df$stop_time = df$time
    stop_year = as.numeric(substr(df$stop_date, 1, 4))
    # only keep years 2016 and 2017
    df = df[(stop_year >= 2016), ]
    # # uppercase the first letter of driver_race_raw
    if ('driver_race_raw' %in% colnames(df)) {
      df$driver_race = str_to_title(df$driver_race_raw)
    }
    # make first name, last name, address, city, state, zip code all uppercase
    df$HA_N_FIRST_DRVR = str_to_upper(df$HA_N_FIRST_DRVR)
    df$HA_N_LAST_DRVR = str_to_upper(df$HA_N_LAST_DRVR)
    df$HA_A_ADDRESS_DRVR = str_to_upper(df$HA_A_ADDRESS_DRVR)
    # if HA_A_ADDRESS_DRVR is UNKNOWN, make it NA
    df = df %>% mutate(HA_A_ADDRESS_DRVR = ifelse(HA_A_ADDRESS_DRVR == "UNKNOWN", NA, HA_A_ADDRESS_DRVR))
    df$HA_A_STATE_DRVR = str_to_upper(df$HA_A_STATE_DRVR)
    df$HA_A_CITY_DRVR = str_to_upper(df$HA_A_CITY_DRVR)
    # take first 5 digits of zip code
    df = df %>% mutate(HA_A_ZIP_DRVR = ifelse(nchar(HA_A_ZIP_DRVR) < 5, NA, substr(HA_A_ZIP_DRVR, 1, 5)))
    # uppercase the first letter of driver_race_raw
    df$driver_race = str_to_title(df$driver_race)
  }
  df
}

# values considered null in the data
null_str = c("", "NaN", "NA", "N/A", "nan", "#N/A", "-NaN", "-n/a", "NULL")

# columns to keep for each state
az_cols = c('SubjectFirstName', 'SubjectLastName', 'VehicleStyle', 'VehicleYear', 'driver_race')
co_cols = c('driver_first_name', 'driver_last_name', 'DOB', 'driver_race')
tx_cols = c('HA_N_FIRST_DRVR', 'HA_N_LAST_DRVR', 'HA_A_ADDRESS_DRVR', 'HA_A_CITY_DRVR', 'HA_A_STATE_DRVR', 'HA_A_ZIP_DRVR', 'driver_race')
extra_cols = c('search_conducted', 'driver_id')
overall_cols = sort(unique(c(az_cols, co_cols, tx_cols, extra_cols)))
print('overall cols')
print(overall_cols)

# create overall data by combining the data from each state for Filtered and Hispanic_White, not for Raw
create_overall_data = function() {
  for (type_data in c('Filtered', 'Hispanic_White')) {
    overall = data.frame()
    for (state in c('az', 'co', 'tx')) {
      data = read.csv(get(paste0(state, '_data'))[[type_data]], na.strings=null_str)
      # if (type_data == 'Raw') {
      #   # make the same adjustments as standardize_cols in policing_data_expl
      #   data = fix_cols(state, data)
      #   # there is no driver_id column so make the driver id the state abbreviation like AZ for all of the data rows
      #   data$driver_id = matrix(state, nrow=nrow(data), ncol=1)
      # } else {
        # otherwise, add the state abbreviation to the driver_id to make them unique across states
        data$driver_id = paste0(state, '_', data$driver_id)
      # }
      cols = c(get(paste0(state, '_cols')), extra_cols)
      print(cols)
      state_data = data[cols]
      print('after fixing data, the data size is')
      print(dim(state_data))
      # fill the rest of the columns that aren't in the state's columns with NA
      state_data = cbind(state_data, matrix(NA, nrow=nrow(state_data), ncol=length(overall_cols) - ncol(state_data)))
      other_cols = setdiff(overall_cols, cols)
      # place the state columns first, the other columns with NA afterwards
      colnames(state_data) = c(cols, other_cols)
      # sort the columns to get the same order in the overall csv
      state_data = state_data[, order(colnames(state_data))]
      print('after filling in the rest of the columns, the data size is')
      print(dim(state_data))
      overall = rbind(overall, state_data) # append to the overall data
      print('overall data size')
      print(dim(overall))
    }
    print('before the write to csv')
    print(dim(overall))
    write.csv(overall, overall_data[[type_data]], row.names=FALSE, quote=TRUE)
    print('check dims')
    print(dim(read.csv(overall_data[[type_data]])))
  }
}

# Create the overall data for Filtered and Hispanic_White
# create_overall_data()
print('DIMS')
# print(dim(read.csv(overall_data[['Raw']])))
print(dim(read.csv(overall_data[['Filtered']])))
print(dim(read.csv(overall_data[['Hispanic_White']])))
print('END DIMS')

calculate_raw_complete = function(df, state, cols) {
  # just return for the one state
  # check for complete rows including the search_conducted column
  complete_cols = c(cols, 'search_conducted')
  print('checking completeness')
  complete_df = df[complete.cases(df[,complete_cols]), ]
  total_complete = nrow(complete_df)
  driver_cols = setdiff(cols, 'driver_race')
  total_drivers = complete_df %>% group_by(across(all_of(driver_cols))) %>% n_groups()
  return(list(total_complete, total_drivers))
}

calculate_overall_complete = function() {
  # add the complete columns per state for the Raw data
  print('total number of overall rows')
  total_complete = 0
  total_drivers = 0
  for (s in c('az', 'co', 'tx')) {
    # only take rows from that state and count complete rows
    only_state_df = fix_cols(s, read.csv(get(paste0(s, '_data'))[['Raw']], na.strings=null_str))
    print('state only df - total rows')
    print(nrow(only_state_df))
    state_cols = get(paste0(s, '_cols'))
    # also include search_conducted in the columns to check for completeness
    complete_cols = c(state_cols, 'search_conducted')
    print('state cols for completeness in the overall')
    print(state_cols)
    complete_data = only_state_df[complete.cases(only_state_df[,complete_cols]), ]
    print('state complete data rows')
    print(nrow(complete_data))
    total_complete = total_complete + nrow(complete_data)
    # also count the number of drivers
    driver_cols = setdiff(state_cols, 'driver_race') # race can differ so remove driver_race from the grouping
    total_drivers = total_drivers + complete_data %>% group_by(across(all_of(driver_cols))) %>% n_groups()
  }
  return(list(total_complete, total_drivers))
}

abbrev = c('Arizona', 'Colorado', 'Texas', 'Overall')
names(abbrev) = c('az', 'co', 'tx', 'overall')

populate_latex_df = function() {
  latex_df = data.frame()
  for (state in c('az', 'co', 'tx', 'overall')) { #c('overall')) { 
    state_data = c()
    for (data_type in c('Raw', 'Filtered', 'Hispanic_White')) {
      type_data = c()
      # don't use the overall df for the Raw data, just use the state data
      if (!(state == 'overall' && data_type == 'Raw')) {
        df = read.csv(get(paste0(state, '_data'))[[data_type]], na.strings=null_str)
        df = fix_cols(state, df)
      }
      if (data_type == 'Raw') {
        # group on all cols EXCEPT driver_race (that could differ)
        print(paste0(state, data_type))
        cols = get(paste0(state, '_cols'))
        print('cols')
        print(cols)
        # only for raw do we need to calculate the number of complete rows, everything downstream is already complete
        if (state != 'overall') {
          stops_drivers = calculate_raw_complete(df, state, cols)
        } else {
          # don't use the Raw overall df, just calculate from the state data
          stops_drivers = calculate_overall_complete()
        }
        total_complete = stops_drivers[[1]]
        total_drivers = stops_drivers[[2]]
        print(total_complete)
        print(total_drivers)
        # add number of stops, number of drivers (the # of groups)
        type_data = c(type_data, comma(total_complete), comma(total_drivers))
      } else { # for Filtered and Hispanic_White
        print(paste0(state, data_type))
        print(dim(df))
        # number of stops + number of drivers
        type_data = c(type_data, comma(nrow(df)), comma(length(unique(df$driver_id))))
        if (data_type == 'Hispanic_White') {
          # mean search rate only for Hispanic-white drivers
          # search_conducted as a boolean
          df$search_conducted_bool = (df$search_conducted == 'True')
          type_data = c(type_data, percent(mean(df[df$driver_race == 'Hispanic', 'search_conducted_bool'], na.rm=TRUE), accuracy=0.1, suffix="\\%"))
          type_data = c(type_data, percent(mean(df[df$driver_race == 'White', 'search_conducted_bool'], na.rm=TRUE), accuracy=0.1, suffix="\\%"))
          if (state == 'overall') {
              print('overall columns search rate')
              complete_search_conducted = df[complete.cases(df[,c('search_conducted')]), ]
              print('number of rows')
              print(nrow(complete_search_conducted))
              print('calculating average search rate over all states')
              # convert search_conducted into a bool
              search_conducted_bool = (complete_search_conducted$search_conducted == 'True')
              print('number of searches conducted')
              print(sum(search_conducted_bool == TRUE))
              print('average search rate')
              print(mean(search_conducted_bool, na.rm=TRUE))
          }
        } else {
          # calculate the number of racial discordant groups there are
          print('racially discordant stops')
          print(df %>% group_by(driver_id) %>% filter(length(unique(driver_race)) >= 2) %>% ungroup() %>% nrow())
          type_data = c(type_data, comma(df %>% group_by(driver_id) %>% filter(length(unique(driver_race)) >= 2) %>% ungroup() %>% nrow()))
          print('racially discordant drivers')
          print(df %>% group_by(driver_id) %>% filter(length(unique(driver_race)) >= 2) %>% n_groups())
          type_data = c(type_data, comma(df %>% group_by(driver_id) %>% filter(length(unique(driver_race)) >= 2) %>% n_groups()))
        }
      }
      state_data = c(state_data, type_data)
    }
    # append state name + state data to the latex_df
    state_data = c(abbrev[[state]], state_data)
    latex_df = rbind(latex_df, state_data)
  }
  latex_df
}

# Populate the latex df
latex_df = populate_latex_df()
# print('FROM THE POPULATING')
# print(latex_df)
# print("_________________ END POPULATING")
# save(latex_df, file = "latex_df_mod_co.RData")
# latex_df_read = load("latex_df_mod_co.RData")
# print('BEGIN READ')
# print(latex_df_read)
# transpose the table to get the columns to be the states
latex_df = t(latex_df)
print('transposed')
print(latex_df)

# swap the rows so that drivers data comes before corresponding stops data
swapped_drivers_stops = c(1, 3, 2, 5, 4, 7, 6, 9, 8, 10, 11)
latex_df = latex_df[swapped_drivers_stops,]
print('swapped drivers and stops')
print(latex_df)

# add the headers for all of the rows
headers_per_row = c(
  'Drivers with Complete Data',
  'Complete Data', 
  'Unique Drivers with More than One Stop',
  'Stops of Drivers Stopped More Than Once',
  'Unique Drivers with Racial Discrepancy',
  'Stops of Multi-Stop Drivers with Racial Discrepancy',
  'Unique Drivers (Hispanic-white discrepancy)',
  'Stops of Hispanic-white Racial Discrepancy',
  'Hispanic Search Rate of Hispanic-white Drivers',
  'white Search Rate of Hispanic-white Drivers'
)
headers_per_col = lapply(latex_df[1,], function(elmnt) {
  return(paste0("\\textbf{", elmnt, "}")) # make the header row bold
})
latex_df = latex_df[-1,]
# make the header row
rownames(latex_df) = headers_per_row # latex_df[1,]
colnames(latex_df) = headers_per_col 

create_percent_rows = function(row_num_frac, row_num_whole, description) {
  decimals = as.numeric(gsub(",", "", latex_df[row_num_frac,])) / as.numeric(gsub(",", "", latex_df[row_num_whole,]))
  percent_str = paste0("\\midrule\n", description)
  for (i in 1:length(decimals)) {
    percent_str = paste0(percent_str, " & ", percent(decimals[i], accuracy=0.1, suffix="\\%"))
  }
  percent_str = paste0(percent_str, "\\\\") # need to add final new line
  percent_str
}
# add the percentages of filtered/complete and Hispanic-white/filtered
# removing the commas to convert back into numbers
filtered_percent_str = create_percent_rows(3, 1, "\\% of all drivers")
filtered_drivers_percent_str = create_percent_rows(4, 2, "\\% of all stops")
print(filtered_drivers_percent_str)
racially_discordant_str = create_percent_rows(5, 3, "\\% of all multiply-stopped drivers")
racially_discordant_drivers_str = create_percent_rows(6, 4, "\\% of all multiply-stopped driver stops")
print(racially_discordant_drivers_str)
hispanic_white_percent_str = create_percent_rows(7, 5, "\\% of inconsistently-perceived drivers")
hispanic_white_drivers_percent_str = create_percent_rows(8, 6, "\\% of inconsistently-perceived driver stops")
print(hispanic_white_drivers_percent_str)

# Print the LaTeX table to the file
align_str = "p{6.3cm}llll"
lines=c(-1, 0, 2)
latex_table = xtable(latex_df, align=align_str, label="tab:descriptive_stats", 
                     caption="Descriptive Statistics for Drivers in Arizona, Colorado, and Texas")

x = print(latex_table, tabular.environment = "tabular*", 
          hline.after=lines, booktabs=TRUE, floating.environment="table*", 
          width="1.02\\textwidth", caption.placement = "top", sanitize.text.function=identity)

# add the multi-column part (which means adding another column, fixing the alignment string)
r = sub(align_str, "@{}p{6.3cm}llll@{}", x, fixed=TRUE)
# r = gsub(" & Arizona", "\\multicolumn{2}{l}{} & Arizona", r, fixed=TRUE)
r = sub(headers_per_row[1], paste0("\\toprule\\multicolumn{5}{l}{\\textbf{Full dataset}}\\\\\n\\toprule\nDrivers"), r, fixed=TRUE)
r = sub(headers_per_row[2], "\\midrule\nStops", r, fixed=TRUE)
r = sub(headers_per_row[3], "\\toprule\n\\multicolumn{5}{l}{\\textbf{Multiply-stopped drivers}}\\\\\n\\toprule\n Drivers", r, fixed=TRUE)
r = sub(headers_per_row[4], paste0(filtered_percent_str, " \\midrule\n Stops"), r, fixed=TRUE)
r = sub(headers_per_row[5], paste0(filtered_drivers_percent_str, "\\midrule\\toprule\n\\multicolumn{5}{l}{\\textbf{Multiply-stopped drivers with inconsistently perceived race}}\\\\\n\\toprule\n Drivers"), r, fixed=TRUE)
r = sub(headers_per_row[6], paste0(racially_discordant_str, " \\midrule\n Stops"), r, fixed=TRUE)
r = sub(headers_per_row[7], paste0(racially_discordant_drivers_str, "\\midrule\\toprule\n\\multicolumn{5}{l}{\\textbf{Drivers perceived as both white and Hispanic}}\\\\\n\\toprule\n Drivers"), r, fixed=TRUE)
r = sub(headers_per_row[8], paste0(hispanic_white_percent_str, " \\midrule\n Stops"), r, fixed=TRUE)
r = sub(headers_per_row[9], paste0(hispanic_white_drivers_percent_str, " \\midrule\n Search rate when perceived as Hispanic"), r, fixed=TRUE)
r = sub(headers_per_row[10], " \\midrule\n Search rate when perceived as white", r, fixed=TRUE)
r = sub("\\end{tabular*}", " \\bottomrule\n\\end{tabular*}", r, fixed=TRUE)

sink(file="plots/descriptive_stats_table_mod_co_two_fix_functions.tex")
cat(r)
sink(NULL)