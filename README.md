# Reproduction code for "Testing for racial bias using inconsistent perceptions of race" (Gera and Pierson, 2024)

## Instructions for reproducing the results in this paper
1. Raw data can be obtained by contacting the authors of the Open Policing Project at [open-policing@lists.stanford.edu].
2. Preprocess the data. For each state, run the state-specific python file (ex. `az.py`) to standardize entries and filter the raw state data down to the set of multiply stopped drivers and inconsistently-perceived drivers. `policing_data_expl.py` contains all the preprocessing code and generates csv files in the `csv` folder that are used later on in the analysis; this file is used as a module for the state-specific python files, so it shouldn't be directly. 
    * Before running `python az.py`, `python co.py`,  or `python tx.py`, replace `path-to-raw-csv` in the `config` with the path to the raw state data you downloaded.
    * It should produce three csv files per state, and these will be used in the statistical analysis; the filenames will start with the state prefix (ex. `az_`)
3. Conduct the statistical analyses on the paper. This includes running regressions using different models to estimate differences in search and arrest rates, along with analyzing the representativeness of our analyzed population. `plot_regression_res.R` contains the code to reproduce the figures in the paper; `make_descriptive_stats_table.R` contains the code to reproduce the descriptive stats table.
    * The `plots/` directory will contain all the resulting figures and tables
    * Replace `path-to-STATE-data.csv` (ex. `path-to-AZ-data.csv`) with the path to that state's raw data before running the R script
    * To run the regressions with the linear probability model on search rate (Figure 1), run `Rscript plot_regression_res.R plot-primary-spec-feols-search-rate`
    * To run the regressions with linear probability model on arrest rate (Figure S1), run `Rscript plot_regression_res.R plot-primary-spec-feols-arrest-rate`
    * To run the regressions with the linear probability model on Arizona search rates, run `Rscript plot_regression_res.R plot-primary-spec-feols-az-stop-duration`
    * To run the fixed-effects generalized model with logit link regression on search rate (Figure S2), run `Rscript plot_regression_res.R plot-spec-feglm-search-rate`
    * To run the regressions with the conditional logit model on search rate (Figure S3), run `Rscript plot_regression_res.R plot-spec-cond-logistic-search-rate`
    * To run the analysis on analyzed population representativeness, run `Rscript plot_regression_res.R analyze-population-representativeness`