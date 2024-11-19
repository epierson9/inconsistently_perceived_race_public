library(tidyverse)
library(ggplot2)
library(fixest)
library(patchwork)
library(lme4)
library(survival)
library(alpaca)
library(broom)
library(stringr)

# Code for producing the regression plots in the paper.

# Derived from https://github.com/5harad/openpolicing/blob/8153b1d034772b6610002b1227d24dd1476943cd/src/processing/processing_driver.R#L94
# Returns a dataframe with various useful time-of-day and time-of-year
# variables which we group_by and use in regressions.
add_time_variables <- function(d){
  #extract stop year.
  d$stop_year = as.factor(as.character(year(d$stop_date)))
  d$stop_year[as.character(d$stop_year) > as.character(year(today()))] = NA
  
  #extract month and year. Cast this to date for convenience in plotting.
  d$month_and_year = as.Date(paste0(substr(d$stop_date, 1, 7), '-01')) # stop month and year are given by first 7 digits. 
  
  # compute stop quarter (Q1 - Q4). 
  d$stop_quarter = quarters(d$stop_date)  
  d$stop_quarter[is.na(d$stop_date)] = NA
  d$stop_quarter = as.factor(d$stop_quarter)
  
  # extract weekday. 
  d$weekday = as.factor(weekdays(d$stop_date))
  
  # bin hour into 8 3-hour bins to create stop_hour_categorical. 
  d$stop_hour = as.numeric(substr(d$stop_time, 1, 2))
  d$stop_hour_categorical = paste0('hour_category_', floor(d$stop_hour / 3) * 3)
  d$stop_hour_categorical[is.na(d$stop_hour)] = NA
  d$stop_hour_categorical = as.factor(d$stop_hour_categorical)
  
  return(d)
}

read_processed_csv = function(state, subset='hispanic-white') {
  stopifnot(state %in% c('AZ', 'CO', 'TX'))
  stopifnot(subset %in% c('all', 'multiply-stopped', 'hispanic-white'))
  col_formatters = cols(stop_date = col_date(format = "%Y-%m-%d"), 
                        stop_time = col_time(format = "%H:%M"), 
                        driver_id = col_character(), 
                        driver_race = col_character(),
                        search_conducted = col_logical(),
                        contraband_found = col_logical(), 
                        county_fips = col_character(), 
                        stop_duration = col_character(), 
                        date = col_date(format = "%Y-%m-%d"), # texas data is in slightly different format with different column names. 
                        time = col_time(format = "%H:%M:%S"))
  if(state == 'AZ') {
    if (subset == 'all') {
      az_all_d = read_csv('csv/az_raw_with_driver_id_Style_Year.csv', col_types=col_formatters)
      az_all_d$driver_id = paste0('AZ', as.character(az_all_d$driver_id))
      return(az_all_d)
    } else if (subset == 'multiply-stopped') {
      az_multiply_stopped_d = read_csv('csv/az_grouped_Style_Year.csv', col_types=col_formatters)
      az_multiply_stopped_d$driver_id = paste0('AZ', as.character(az_multiply_stopped_d$driver_id))
      return(az_multiply_stopped_d)
    } else if (subset == 'hispanic-white') {
      filepath = 'csv/az_hispanic_white_drivers_Style_Year.csv'
    }
    d = read_csv(filepath, col_types = col_formatters)
    print('az rows')
    print(nrow(d))
    extra_cols_to_keep = c('stop_duration', 'county_fips', 'officer_id', 'is_arrested')
  } else if(state == 'CO') {
    if (subset == 'all') {
      co_all_d = read_csv('csv/co_raw_with_driver_id_mod_officer_id.csv', col_types=col_formatters)
      co_all_d$driver_id = paste0('CO', as.character(co_all_d$driver_id))
      return(co_all_d)
    } else if (subset == 'multiply-stopped') {
      co_multiply_stopped_d = read_csv('csv/co_grouped_mod_officer_id.csv', col_types=col_formatters)
      co_multiply_stopped_d$driver_id = paste0('CO', as.character(co_multiply_stopped_d$driver_id))
      return(co_multiply_stopped_d)
    } else if (subset == 'hispanic-white') {
      filepath = 'csv/co_hispanic_white_drivers_only_mod.csv'
    }
    d = read_csv(filepath, col_types = col_formatters)
    print('co rows')
    print(nrow(d))
    extra_cols_to_keep = c('county_fips', 'officer_id', 'is_arrested')
  } else if(state == 'TX') {
    if (subset == 'all') {
      tx_all_d = read_csv('csv/tx_raw_with_driver_id_driver_race.csv', col_types=col_formatters)
      tx_all_d$driver_id = paste0('TX', as.character(tx_all_d$driver_id))
      return(tx_all_d)
    } else if (subset == 'multiply-stopped') {
      tx_multiply_stopped_d = read_csv('csv/tx_processed_grouped_driver_race_raw.csv', col_types=col_formatters)
      tx_multiply_stopped_d$driver_id = paste0('TX', as.character(tx_multiply_stopped_d$driver_id))
      return(tx_multiply_stopped_d)
    } else if (subset == 'hispanic-white') {
      filepath = 'csv/tx_processed_hispanic_white_drivers_driver_race.csv'
    }
    d = read_csv(filepath, col_types = col_formatters)
    print('tx rows')
    print(nrow(d))
    d$stop_date = d$date
    d$stop_time = d$time
    # capitalize driver race
    d$driver_race = tools::toTitleCase(d$driver_race)
    extra_cols_to_keep = c('officer_id')
  }
  print(sprintf('%i total rows; %i total drivers; %2.1f%% of stops are of Hispanic drivers', 
                  nrow(d), length(unique(d$driver_id)), mean(d$driver_race == 'Hispanic') * 100))
  
  # check for null values in critical columns. 
  stopifnot(all(!is.na(d$driver_id)))
  stopifnot(all(!is.na(d$driver_race)))
  stopifnot(all(!is.na(d$search_conducted)))
  stopifnot(all(!is.na(d$stop_time)))
  stopifnot(all(!is.na(d$stop_date)))
  stopifnot(all(d$driver_race %in% c('Hispanic', 'White')))
  
  # concatenate state to driver_id, officer_id, and county_id to make them unique
  d$driver_id = as.character(d$driver_id)
  d$driver_id = paste0(state, d$driver_id)
  officer_id_na = is.na(d$officer_id)
  d$officer_id = paste0(state, d$officer_id)
  d$officer_id[officer_id_na] = NA # set missing officer IDs to NA.
  d$county_id = paste0(state, d$county_fips)
  d$county_id[is.na(d$county_fips)] = NA # set missing county IDs to NA. 
  d$hour_of_day = as.numeric(substr(d$stop_time, 1, 2)) + as.numeric(substr(d$stop_time, 4, 5))/60.0
  stopifnot(min(d$hour_of_day) >= 0 & max(d$hour_of_day) <= 24)
  stopifnot(all(!is.na(d$hour_of_day)))
  d$state = state
  
  # subset columns using vector. 
  all_cols_to_keep = c(c('driver_id', 'driver_race', 'hour_of_day', 'search_conducted', 'county_id', 'stop_date', 'stop_time', 'state', 'contraband_found', 'violation', 'county_name'), 
                       extra_cols_to_keep)
  d = d[,all_cols_to_keep]
  d = add_time_variables(d)
  # print random sample of dataframe - good to inspect and make sure all rows look reasonable. 
  print(state)
  message("Random sample of dataframe")
  print(d %>% sample_n(10))
  message("missing data fractions by column")
  print(colMeans(is.na(d)))
  d
}

texas_d = read_processed_csv('TX')
# print a sample of texas_d of 10 rows
print('texas number of rows')
print(nrow(texas_d))
print((texas_d %>% sample_n(10))[,'officer_id'])
arizona_d = read_processed_csv('AZ')
print('arizona number of rows')
print(nrow(arizona_d))
print((arizona_d %>% sample_n(10))[,'officer_id'])
colorado_d = read_processed_csv('CO')
print('colorado number of rows')
print(nrow(colorado_d))
print((colorado_d %>% sample_n(10))[,'officer_id'])

overall_d = bind_rows(arizona_d, colorado_d, texas_d)
print('overall number of rows')
print(nrow(overall_d))
# print number of unique rows and unique drivers
message('Number of unique rows: ', nrow(overall_d))
message('number of unique drivers: ', length(unique(overall_d$driver_id)))
message("Search rates by state and race")
print(overall_d %>% group_by(state, driver_race) %>% summarize(n = n(), search_p=search_conducted %>% mean()))

# combine all state datasets together to analyze search rates
subset_cols = c('search_conducted', 'driver_race', 'driver_id')
all_d = rbind(
  read_processed_csv('AZ', 'all')[,subset_cols],
  read_processed_csv('CO', 'all')[,subset_cols],
  read_processed_csv('TX', 'all')[,subset_cols]
)
print('all data samples')
print(all_d %>% sample_n(10))
print(nrow(all_d))
save(all_d, file='all_d.RData')
print(all_d %>% sample_n(10))

# combine AZ + CO datasets together to analyze arrest rates
# include is_arrested in this set
az_co_subset_cols  = c('is_arrested', 'search_conducted', 'driver_race', 'driver_id')
az_co_all_d = rbind(
  read_processed_csv('AZ', 'all')[,az_co_subset_cols], 
  read_processed_csv('CO', 'all')[,az_co_subset_cols]
)
save(az_co_all_d, file='az_co_all_d.RData')
print('all number of rows')
print(nrow(az_co_all_d))
print(az_co_all_d %>% sample_n(10))

# combine all multiply-stopped datasets together to analyze search rates
multiply_stopped_cols = c('search_conducted', 'driver_race', 'driver_id')
multiply_stopped_d = rbind(
  read_processed_csv('AZ', 'multiply-stopped')[,multiply_stopped_cols],
  read_processed_csv('CO', 'multiply-stopped')[,multiply_stopped_cols],
  read_processed_csv('TX', 'multiply-stopped')[,multiply_stopped_cols]
)
save(multiply_stopped_d, file='multiply_stopped_d.RData')
print('multiply-stopped number of rows')
print(nrow(multiply_stopped_d))
print(multiply_stopped_d %>% sample_n(10))

# combine AZ + CO multiply-stopped datasets together to analyze arrest rates
az_co_multiply_stopped_cols = c('is_arrested', 'search_conducted', 'driver_race', 'driver_id')
az_co_multiply_stopped_d = rbind(
  read_processed_csv('AZ', 'multiply-stopped')[,az_co_multiply_stopped_cols], 
  read_processed_csv('CO', 'multiply-stopped')[,az_co_multiply_stopped_cols]
)
save(az_co_multiply_stopped_d, file='az_co_multiply_stopped_d.RData')
print(az_co_multiply_stopped_d %>% sample_n(10))

# create dataframe which filters out officers who always search or never search. 
officer_search_rates = overall_d %>% group_by(officer_id) %>% summarize(officer_search_rate = mean(search_conducted), nonuniform_officer=(officer_search_rate < 1) & (officer_search_rate > 0))
county_search_rates = overall_d %>% group_by(county_id) %>% summarize(county_search_rate = mean(search_conducted), nonuniform_county=(county_search_rate < 1) & (county_search_rate > 0))
overall_d = overall_d %>% left_join(officer_search_rates, by='officer_id') %>% left_join(county_search_rates, by='county_id')
message(sprintf("Prior to filtering for non-uniform officers/counties, number of unique officers, counties, and rows: %i, %i, %i", length(unique(overall_d$officer_id)), length(unique(overall_d$county_id)), nrow(overall_d)))
non_uniform_overall_d = overall_d %>% filter(nonuniform_county & nonuniform_officer)
non_uniform_county_d = overall_d %>% filter(nonuniform_county)
non_uniform_officer_d = overall_d %>% filter(nonuniform_officer)
message(sprintf("After filtering for non-uniform officers, number of unique officers, counties, and rows: %i, %i, %i", length(unique(non_uniform_officer_d$officer_id)), length(unique(non_uniform_officer_d$county_id)), nrow(non_uniform_officer_d)))
message(sprintf("After filtering for non-uniform counties, number of unique officers, counties, and rows: %i, %i, %i", length(unique(non_uniform_county_d$officer_id)), length(unique(non_uniform_county_d$county_id)), nrow(non_uniform_county_d)))
message(sprintf("After filtering for non-uniform officers and counties, number of unique officers, counties, and rows: %i, %i, %i", length(unique(non_uniform_overall_d$officer_id)), length(unique(non_uniform_overall_d$county_id)), nrow(non_uniform_overall_d)))

# construct the formulas for feols and feglm (feglm-nobiascorrect, feglm-biascorrect)
construct_feols_feglm_formula = function(formula_pieces, d, model_name) {
  controls = paste(paste(formula_pieces$controls), collapse=' + ')
  if (nchar(controls) > 0) { # assemble formula with the controls
    formula_str = paste0(formula_pieces$dv, ' ~ driver_race + ', controls, ' | ')
  } else {
    formula_str = paste0(formula_pieces$dv, ' ~ ', 'driver_race | ')
  }
  # add the effects to the formula
  effects = paste(paste(formula_pieces$effects), collapse=' + ')
  formula_str = paste0(formula_str, effects)
  print(formula_str)
  if (model_name == 'feols') {
    model = fixest::feols(as.formula(formula_str), d, "cluster")
    print('formula feols')
    print(model)
  } else if (model_name == 'feglm-nobiascorrect') {
    print('formula feglm-nobiascorrect')
    print(formula_str)
    model = fixest::feglm(as.formula(formula_str), d, family=binomial('logit'), vcov="cluster", glm.iter=100, fixef.iter=20000)
    print(summary(model))
  } else { # for the feglm-biascorrect
    print('formula biascorrect')
    print(formula_str)
    model = alpaca::feglm(as.formula(formula_str), d, family=binomial("logit"), control=list(iter.max=1000))
    model = alpaca::biasCorr(model)
  }
  model_summary = summary(model)
  return(list(model=model, model_summary=model_summary))
}

# construct the formulas for mixed-linear and mixed-logistic
construct_mixed_formula = function(formula_pieces, d, model_name) {
  controls = formula_pieces$controls
  controls = paste(paste(controls), collapse=' + ')
  if (nchar(controls) > 0) { # assemble formula with the controls, if there are any
    formula_str = paste0(formula_pieces$dv, ' ~ driver_race + ', controls)
  } else {
    formula_str = paste0(formula_pieces$dv, ' ~ ', 'driver_race')
  }
  # add effects to the formula string
  effects = paste(paste(as.list(sapply(formula_pieces$effects, function(e) paste0("(1 | ", e, ")")))), collapse = " + ")
  formula_str = paste0(formula_str, ' + ', effects)
  print('formula string')
  print(formula_str)
  if (model_name == 'mixed-linear') {
    model = lmer(as.formula(formula_str), d, control=lmerControl(optCtrl=list(maxfun=2000000, tol=2e-2)))
    model_summary = summary(model)
  } else if (model_name == 'mixed-logistic') {
    model = glmer(as.formula(formula_str), data, family=binomial('logit'), 
          glmerControl(optimizer = "bobyqa", optCtrl = list(maxfun = 100000)))
    model_summary = summary(model)
  }
  return(list(model=model, model_summary=model_summary))
}

# construct the formulas for cond-logistic regression
construct_cond_formula = function(formula_pieces, d) {
  controls = paste0(paste(formula_pieces$controls), collapse=' + ')
  if (nchar(controls) > 0) { # assemble formula with the controls
    formula_str = paste0(formula_pieces$dv, ' ~ driver_race + ', controls)
  } else {
    formula_str = paste0(formula_pieces$dv, ' ~ driver_race')
  }
  # add effects to the formula string
  effects = paste(paste(as.list(sapply(formula_pieces$effects, function(e) if (e != 'county_id' && e != 'officer_id') paste0("strata(", e, ")") else e))), collapse = " + ")
  formula_str = paste0(formula_str, ' + ', effects)
  print('formula string')
  print(formula_str)
  model = survival::clogit(as.formula(formula_str), d, method="exact", iter.max=1000)
  model_summary = summary(model)
  return(list(model=model, model_summary=model_summary))
}

check_controls_are_state_columns = function(controls) {
  if (length(controls) > 0) {
    for (control in controls) {
      # if the control is in parens (ex. c(officer_id)), extract only the control (officer_id) inside the parens
      control = gsub("[\\(\\)]", "", regmatches(control, gregexpr("\\(.*?\\)", control))[[1]][1])
      for (state in c('arizona', 'colorado', 'texas')) {
        state_cols = names(get(paste0(state, '_d')))
        stopifnot(control %in% state_cols) # check if the control is in the state columns
      }
    }
  }
}

make_na_stat = function(e, descript) {
  message(sprintf('Warning: Model did not converge\n\t%s', e))
  data.frame(
  point_est = NA,
  xmin = NA,
  xmax = NA,
  labels = descript
  )
}

# the main function that runs the regression and constructst the formulas from the 
# functions that start with construct_
regress_with_model = function(formula_pieces, d, model_name) {
  d$search_conducted = as.logical(d$search_conducted)
  # relevel to use White as the reference category to get everything in terms of (Hispanic - white)
  d$driver_race = as.factor(d$driver_race)
  d$driver_race = relevel(d$driver_race, ref = "White")
  if (model_name == 'feols') {
    # multiply by 100 to get the search rate
    model_results = construct_feols_feglm_formula(formula_pieces, d, model_name)
    model_summary = model_results$model_summary
    # multiply by 100 to get the search rate
    est = 100 * model_summary$coefficients['driver_raceHispanic']
    model = model_results$model
    xmin = 100 * confint(model)['driver_raceHispanic', '2.5 %']
    xmax = 100 * confint(model)['driver_raceHispanic', '97.5 %']
    print(xmin)
    print(xmax)
  } else if (model_name == 'feglm-nobiascorrect') {
    model_results = construct_feols_feglm_formula(formula_pieces, d, model_name)
    model_summary = model_results$model_summary
    # this is logistic, so this is already the rate
    est = model_summary$coefficients['driver_raceHispanic']
    model = model_results$model
    xmin = confint(model)['driver_raceHispanic', '2.5 %']
    xmax = confint(model)['driver_raceHispanic', '97.5 %']
    print(xmin)
    print(xmax)
  } else if (model_name == 'feglm-biascorrect') { # NOTE: not used
    model_results = construct_feols_feglm_formula(formula_pieces, d, model_name)
    model_summary = model_results$model_summary
    est = model_summary$cm['driver_raceHispanic','Estimate']
    std = model_summary$cm['driver_raceHispanic','Std. error']
    xmin = est - 1.96 * std
    xmax = est + 1.96 * std
    print(model_summary)
    model = model_results$model
  } else if (model_name == 'mixed-linear') { # NOTE: not used
    model_results = construct_mixed_formula(formula_pieces, d, model_name)
    model_summary = model_results$model_summary
    model = model_results$model
    print(model_summary)
    # multiply by 100 to get the rate
    est = 100 * model_summary$coefficients['driver_raceHispanic','Estimate']
    std = 100 * model_summary$coefficients['driver_raceHispanic','Std. Error']
    xmin = est - 1.96 * std
    xmax = est + 1.96 * std
  } else if (model_name == 'mixed-logistic') { # NOTE: not used
    model_results = construct_mixed_formula(formula_pieces, d, model_name)
    model_summary = model_results$model_summary
    model = model_results$model
    print('model')
    print(model)
    print('summary')
    print(model_summary)
  } else if (model_name == 'cond-logistic') {
    model_results = construct_cond_formula(formula_pieces, d)
    model_summary = model_results$model_summary
    model = model_results$model
    print('model')
    print(model)
    print('summary')
    print(model_summary)
    est = coef(model)['driver_raceHispanic']
    model = model_results$model
    xmin = confint(model)['driver_raceHispanic', '2.5 %']
    xmax = confint(model)['driver_raceHispanic', '97.5 %']
  } else {
    stop('Model name not recognized')
  }
  print(paste0('#observations: ', toString(nobs(model))))
  conf_int_vals = list(est=est, xmin=xmin, xmax=xmax, descript=formula_pieces$descript)
  return(conf_int_vals)
}

regress_search_rate = function(d, formula_pieces, state, model_name) {
  print(state)
  # catch any convergence warnings or errors
  tryCatch({
    if (state == 'Overall') {
      # make sure the column exists in all of the states
      check_controls_are_state_columns(formula_pieces$controls)
    }
    if (model_name == 'cond-logistic') {
      # use non_uniform datasets based on if there's county_id and officer_id in the effects
      if ("officer_id" %in% formula_pieces$effects && "county_id" %in% formula_pieces$effects) {
        # use non_uniform_overall_d instead of overall_d
        print('using non_uniform_overall_d')
        d = non_uniform_overall_d
      } else if ("officer_id" %in% formula_pieces$effects) {
        # use non_uniform_officer_d instead of overall_d
        print('using non_uniform_officer_d')
        d = non_uniform_officer_d
      } else if ("county_id" %in% formula_pieces$effects) {
        # use non_uniform_county_d instead of overall_d
        print('using non_uniform_county_d')
        d = non_uniform_county_d
      }
    }
    # conf_int_vals has the point estimate, lower confidence interval bound, and upper confidence interval bound
    conf_int_vals = regress_with_model(formula_pieces, d, model_name)
    est = conf_int_vals$est
    xmin = conf_int_vals$xmin
    xmax = conf_int_vals$xmax
    message(sprintf('%s: %2.4f (%2.4f, %2.4f)', state, est, xmin, xmax))
    data.frame(
      point_est = est,
      xmin = xmin,
      xmax = xmax,
      labels = conf_int_vals$descript
    )
  }, 
  error = function(e) { make_na_stat(e, formula_pieces$descript) })
}

regress_search_rate_controls_lst = function(d, controls, state, model_name) {
  state_control_res_lst = data.frame()
  for (control in controls) {
    print('===============================')
    print(state)
    print('===============================')
    state_control_res = regress_search_rate(d, control, state, model_name)
    state_control_res_lst = rbind(state_control_res_lst, state_control_res)
    print(state_control_res)
  }
  state_control_res_lst
}

# for arizona stop duration regression
az_controls = list(
  list(descript='No controls', dv='search_conducted', controls=list(), use_twoway=FALSE, effects=list('driver_id')),
  list(descript='Officer id', dv='search_conducted', controls=list(), use_twoway=TRUE, effects=list('driver_id', 'officer_id')),
  list(descript='Stop county', dv='search_conducted', controls=list(), use_twoway=FALSE, effects=list('driver_id', 'county_id')),
  list(descript='Stop date/time', dv='search_conducted', controls=list('C(stop_year)', 'C(stop_quarter)', 'C(weekday)', 'C(stop_hour_categorical)'), use_twoway=FALSE, effects=list('driver_id')),
  list(descript='Stop duration', dv='search_conducted', controls=list('C(stop_duration)'), use_twoway=FALSE, effects=list('driver_id')),
  list(descript='All controls', dv='search_conducted', controls=list('C(stop_year)', 'C(county_id)', 'C(stop_quarter)', 'C(weekday)', 'C(stop_hour_categorical)', 'C(stop_duration)'), use_twoway=TRUE, effects=list('driver_id', 'officer_id', 'county_id'))
)


overall_controls = list(
  list(descript='All', dv='search_conducted', controls=list('C(stop_year)', 'C(stop_quarter)', 'C(weekday)', 'C(stop_hour_categorical)'), use_twoway=TRUE, effects=list('driver_id', 'officer_id', 'county_id')),
  list(descript='Stop date/time', dv='search_conducted', controls=list('C(stop_year)', 'C(stop_quarter)', 'C(weekday)', 'C(stop_hour_categorical)'), use_twoway=FALSE, effects=list('driver_id')),
  list(descript='Stop location', dv='search_conducted', controls=list(), use_twoway=FALSE, effects=list('driver_id', 'county_id')),
  list(descript='Officer id', dv='search_conducted', controls=list(), use_twoway=TRUE, effects=list('driver_id', 'officer_id')),
  list(descript='None', dv='search_conducted', controls=list(), use_twoway=FALSE, effects=list('driver_id'))  
)

# plot data
plot_data = function(data, state, dep_var, x_ax_label, label_suffix="", comparison_plots = FALSE) {
  data['breaks'] = c(1:nrow(data))
  print('Data')
  print(data)

  # find the min and max of the point estimates for the axis limits
  min_x = min(min(data$xmin, na.rm = TRUE), 0) # make sure 0 is at the left-end
  max_x = max(data$xmax, na.rm = TRUE) 
  
  # set the rate type for the plot title
  if (dep_var == 'search_conducted') {
    rate_type = 'search'
  } else {
    rate_type = 'arrest'
  }

  if (comparison_plots) {
    # keeps the two datapoints on the same line, instead of numbering the rows
    y_vals = data['y_vals']
    color_choice = data$color
  } else {
    y_vals = c(1:nrow(data))
    color_choice = 'black'
  }

  if (comparison_plots) {
    # add different colors
    plot = ggplot(data, aes(x = point_est, y = y_vals, color = color_choice))
    breaks = c(1:3)
    labels = c('All drivers', 'Multiply-stopped drivers', 'Inconsistently-perceived drivers')
    y_ax_label = NULL
  } else {
    plot = ggplot(data, aes(x = point_est, y = y_vals))
    breaks = data$breaks
    labels = data$labels
    y_ax_label = 'Additional controls\nbeyond driver fixed effects'
  }

  plot = plot + 
    geom_errorbar(aes(xmin = xmin, xmax = xmax), color=color_choice, width = 0) + 
    geom_point(pch = 21, color=color_choice, fill=color_choice) + 
    scale_x_continuous(x_ax_label, labels=function(x) paste0(x, label_suffix)) +
    scale_y_continuous(y_ax_label, breaks=breaks, labels=labels) +
    theme_bw() +
    theme(axis.ticks.y = element_blank(),
          panel.grid.major.y = element_blank(), # removing gridlines
          panel.grid.minor.y = element_blank(),
          panel.grid.major.x = element_blank(),
          panel.grid.minor.x = element_blank(),
          text = element_text(family = "Helvetica"),
          plot.title = element_text(hjust = 0.5),
          axis.title.y = element_text(size = 9))

  if (!comparison_plots) {
    # add in the dashed axis line and set the coordinates, don't add a legend, and set the y-axis title
    plot = plot + 
      geom_vline(xintercept = 0, linetype = "dashed", color = "blue", alpha=0.4) +
      coord_cartesian(xlim=c(min_x - 0.01, max_x + 0.01), ylim = c(0.5, nrow(data) + 0.5), clip="off") + # for getting annotations outside the figure
      theme(legend.position = "none")
  } else {
    # add margins to prevent overflow, adding a legend
    plot = plot + 
      theme(plot.margin = margin(t = 10, r = 10, b = 10, l = 10, unit = "pt")) +
      scale_color_identity(name = "Perceived race",
                       breaks = c("black", "blue"),
                       labels = c("White", "Hispanic"),
                       guide = "legend") + 
      geom_point(show.legend = TRUE) + 
      theme(
        legend.position = c(0.97, 0.95),
        legend.justification = c("right", "top"),
        legend.key.size = unit(0.4, "cm"),
        legend.title = element_text(size = 8),
        legend.text = element_text(size = 8),
        legend.box.background = element_rect(color = "black", size = 0.25),
        legend.box.margin = margin(2, 2, 2, 2)
      )
  }
  plot
}

abbrev = c('az', 'co', 'tx', 'overall')
states = c('Arizona', 'Colorado', 'Texas', 'Overall')
names(abbrev) = states

# plot feols for arizona (for stop duration regression)
plot_feols_arizona = function() {
  az_search_stats = regress_search_rate_controls_lst(arizona_d, az_controls, 'Arizona', 'feols')
  plot = plot_data(az_search_stats, 'Arizona', 'search_conducted', 'Hispanic search rate - white search rate', '%')
  ggsave('plots/feols/Arizona_search_conducted_regr_plot.pdf', plot, width=5, height=2)
}

# plot arrest data for supp. figure 1
plot_az_co_data = function(dv) {
  az_co_d = bind_rows(arizona_d, colorado_d)
  # use the controls from the overall but change the dependent variable to is_arrested
  az_co_controls = lapply(overall_controls, function(inner_list) {
    inner_list$dv = dv
    inner_list
  })
  if (dv == 'is_arrested') {
    rate_type = 'arrest'
  } else {
    rate_type = 'search'
  }
  az_co_arrest_stats = regress_search_rate_controls_lst(az_co_d, az_co_controls, 'Arizona and Colorado', 'feols')
  plot = plot_data(az_co_arrest_stats, 'Arizona and Colorado', dv, paste('Hispanic', rate_type, 'rate - white', rate_type, 'rate'), '%')
  ggsave(paste0('plots/feols/Arizona_and_Colorado_', dv, '_regr_plot.pdf'), plot, width=5, height=2)
}

compute_search_rate_comparison = function(dv, data, yaxis_val, label) {
  print(nrow(data))
  white_hispanic_data = data.frame()
  for (race in c('White', 'Hispanic')) {
    race_data = data %>% filter(driver_race == race)
    model = fixest::feols(as.formula(paste0(dv, ' ~ 1')), race_data)
    # all data doesn't have a driver_id, so don't cluster on it
    model_summary = summary(model, cluster=~driver_id)
    confint = confint(model, cluster=~driver_id)
    print(model_summary)
    print(confint)
    est = 100 * model_summary$coefficients['(Intercept)']
    xmin = 100 * confint['(Intercept)', '2.5 %']
    xmax = 100 * confint['(Intercept)', '97.5 %']
    color = if(race == 'White') 'black' else 'blue'
    df = data.frame(
      point_est = est,
      xmin = xmin,
      xmax = xmax,
      labels = label,
      color = color
    )
    white_hispanic_data = rbind(white_hispanic_data, df)
  }
  white_hispanic_data['y_vals'] = yaxis_val
  print(white_hispanic_data)
  white_hispanic_data
}

load('all_d.RData')
load('multiply_stopped_d.RData')
load('az_co_all_d.RData')
load('az_co_multiply_stopped_d.RData')

print(all_d %>% sample_n(10))
print('-------')
print(multiply_stopped_d %>% sample_n(10))
print('-------')
print(az_co_all_d %>% sample_n(10))
# plot the five most common values for the column col in the dataframe d
print_top_five_col_values = function(d, col) {
  col_frequency = table(d[[col]])
  # sort by frequency, most frequent first
  sorted_freq = sort(col_frequency, decreasing = TRUE) %>% head(5)
  print('sorted frequency')
  print(head(sorted_freq, 5))
}

# print the top 5 values for the columns 'violation' and 'county_name' for each state and type
print_top_five_values_per_datset = function() {
  for (state in c('AZ', 'CO', 'TX')) {
    for (type in c('all', 'multiply-stopped', 'hispanic-white')) {
      for (col in c('violation', 'county_name')) {
        print(sprintf('Top 5 values for %s - %s %s', col, state, type))
        print_top_five_col_values(read_processed_csv(state, type), col)
      }
    }
  }
}

plot_subset_comparisons = function(dv) {
  # plot search and arrest rate comparisons across subpopulations
  # arrest data only available for az and co
  all_data = if(dv == 'search_conducted') all_d else az_co_all_d
  multiply_stopped_data = if(dv == 'search_conducted') multiply_stopped_d else az_co_multiply_stopped_d
  hispanic_white_data = if(dv == 'search_conducted') overall_d else bind_rows(arizona_d, colorado_d)
  comparison_data = rbind(
    compute_search_rate_comparison(dv, all_data, 1, 'All Drivers'),
    compute_search_rate_comparison(dv, multiply_stopped_data, 2, 'Multiply Stopped Drivers'),
    compute_search_rate_comparison(dv, hispanic_white_data, 3, 'Hispanic-white Drivers')
  )
  rate = if(dv == 'search_conducted') 'Search rate' else 'Arrest rate'
  plot = plot_data(comparison_data, 'All', dv, rate, '%', comparison_plots = TRUE)
  ggsave(paste0('plots/feols/comparison_', dv, '_plot.pdf'), plot, width=5, height=2)
}


# overall regressions using the other models 
plot_overall_regressions = function(model_name) {
  stats = regress_search_rate_controls_lst(overall_d, overall_controls, 'Overall', model_name)
  
  if (model_name != 'feols') {
    x_ax_label = 'Race coefficient'
    label_suffix = ""
  } else {
    x_ax_label = 'Hispanic search rate - white search rate'
    label_suffix = "%"
  }
  plot = plot_data(stats, 'Overall', 'search_conducted', x_ax_label, label_suffix)
  ggsave(sprintf('%s/%s/Overall_search_conducted_regr_plot_%s.pdf', 'plots', model_name, model_name), plot, width=5, height=2)
}

# read in the args
args = commandArgs(trailingOnly = TRUE)
print(args)
if (args == 'plot-primary-spec-feols-search-rate') {
  plot_overall_regressions('feols')
} else if (args == 'plot-primary-spec-feols-arrest-rate') {
  plot_az_co_data('is_arrested')
} else if (args == 'plot-primary-spec-feols-az-stop-duration') {
  plot_feols_arizona()
} else if (args == 'plot-spec-feglm-search-rate') {
  plot_overall_regressions('feglm-nobiascorrect')
} else if (args == 'plot-spec-cond-logistic-search-rate') {
  plot_overall_regressions('cond-logistic')
} else if (args == 'analyze-population-representativeness') {
  plot_subset_comparisons('search_conducted')
  plot_subset_comparisons('is_arrested')
  print_top_five_values_per_datset()
} else {
  stop('Not a valid argument; try one of the following: plot-primary-spec-feols-search-rate, plot-primary-spec-feols-arrest-rate, plot-primary-spec-feols-az-stop-duration, plot-spec-feglm-search-rate, plot-spec-cond-logistic-search-rate, analyze-population-representativeness')
}