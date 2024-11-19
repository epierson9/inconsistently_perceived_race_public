# Reproduction code for "Testing for racial bias using inconsistent perceptions of race" (Gera and Pierson, 2024)

We did preliminary analysis in Python and used R to run the analyses and construct the tables and figures for this paper.

## Instructions for reproducing the results in this paper
1. Raw data can be obtained by contacting the authors of the Open Policing Project at [open-policing@lists.stanford.edu].
2. `policing_data_expl.py` contains all the preprocessing code and generates csv files that are used in the analysis. This file is a module for 
- Before running, replace `path-to-STATE-data.csv` (ex. `path-to-AZ-data.csv`) with the path to the raw data you downloaded.
- Replace `config[base_path]` or `base_path` with the path to this directory.
3. `plot_regression_res.R` contains the code to reproduce the figures in the paper.
- To run the regresisons with the linear probability model on search rate (Figure 1), run `Rscript plot_regression_res.R plot-primary-spec-feols-search-rate`
- To run the regressiosn with linear probability model on arrest rate (Figure S1), run `Rscript plot_regression_res.R plot-primary-spec-feols-arrest-rate`
- To run the regressions with the linear probability model on Arizona search rates, run `Rscript plot_regression_res.R plot-primary-spec-feols-az-stop-duration`
- To run the regressions with the fixed-effects generalized model with logit link regression on search rate (Figure S2), run `Rscript plot_regression_res.R plot-spec-feglm-search-rate`
- To run the regressions with the conditional logit model on search rate (Figure S3), run `Rscript plot_regression_res.R plot-spec-cond-logistic-search-rate`
- To run the analysis on analyzed population representativeness, run `Rscript plot_regression_res.R analyze-population-representativeness`
4. `make_descriptive_stats_table.R` contains the code to reproduce the descriptive stats table (Table 1). Run `Rscript make_descriptive_stats_table.R`

