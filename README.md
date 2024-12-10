# Reproduction code for "Testing for racial bias using inconsistent perceptions of race" (Gera and Pierson, 2024)

# System requirements, software requirements, and installation guide

## Hardware and OS requirements
No non-standard hardware is required to run this code, only a standard computer with enough RAM and suitable CPU (the machine we tested on had 60GB RAM, CPU with 16 cores at 2.6GHz/core, and at least 200 GB of memory). The code runs on Linux and should run on macOS; this software has been tested on Linux Ubuntu 20.04.6 LTS.

## Software requirements
### Python dependencies
We use Python code for preprocessing; the following are the package dependencies:
```
pandas
matplotlib
numpy
scipy
IPython
statsmodels
linearmodels
```

### R dependencies
We use R code for analysis; from an R terminal, you can install the package dependencies as follows:
```R
install.packages(c('xtable', 'data.table', 'magrittr', 'scales', 'dplyr', 'tidyr', 'tidyverse', 'ggplot2', 'fixest', 'patchwork', 'lme4', 'survival', 'alpaca', 'broom', 'stringr'))
```

### Conda dev environment
If you create a brand new conda environment to install these dependencies
```
conda create -n Renv
conda activate Renv
```
you have to install R-essentials first before accessing the R terminal to install the R dependencies
```
conda install r-essentials
conda install pandas matplotlib numpy scipy IPython statsmodels linearmodels
```
but you can use conda to install the Python dependencies.

# Instructions for reproducing the results in this paper
1. Raw data can be obtained by contacting the authors of the Open Policing Project at open-policing@lists.stanford.edu.
2. Preprocess the data (est. runtime: 3-10 mins per state). For each state, run the state-specific python file (ex. `az.py`) to standardize entries and filter the raw state data down to the set of multiply stopped drivers and inconsistently-perceived drivers. `policing_data_expl.py` contains all the preprocessing code and generates csv files in the `csv` folder that are used later on in the analysis; this file is used as a module for the state-specific python files, so it shouldn't be directly. 
    * Before running `python az.py`, `python co.py`,  or `python tx.py`, replace `path-to-raw-csv` in the `config` with the path to the raw state data you downloaded. Note: Sample data can be found in the `csv/samples` folder, so you can also use the path to the sample data (i.e. `csv/samples/az_sample.csv`) instead of the raw state data and proceed with the statistical analysis.
    * It should produce three csv files per state, and these will be used in the statistical analysis; the filenames will start with the state prefix (ex. `az_`)
3. Conduct the statistical analyses on the paper. This includes running regressions using different models to estimate differences in search and arrest rates, along with analyzing the representativeness of our analyzed population. `plot_regression_res.R` contains the code to reproduce the figures in the paper (est. runtime: 5-10 mins per regression); `make_descriptive_stats_table.R` contains the code to reproduce the descriptive stats table (est. runtime: 1hr). Analysis of the raw state data reproduces the figures and table in the paper ; some sample data results are located in the `csv/samples/results` folder.
    * The `plots/` directory will contain all the resulting figures and tables
    * Replace `path-to-STATE-data.csv` (ex. `path-to-AZ-data.csv`) with the path to that state's raw data before running the R script
    * To run the regressions with the linear probability model on search rate (Figure 1), run `Rscript plot_regression_res.R plot-primary-spec-feols-search-rate`
    * To run the regressions with linear probability model on arrest rate (Figure S1), run `Rscript plot_regression_res.R plot-primary-spec-feols-arrest-rate`
    * To run the regressions with the linear probability model on Arizona search rates, run `Rscript plot_regression_res.R plot-primary-spec-feols-az-stop-duration`
    * To run the fixed-effects generalized model with logit link regression on search rate (Figure S2), run `Rscript plot_regression_res.R plot-spec-feglm-search-rate`
    * To run the regressions with the conditional logit model on search rate (Figure S3), run `Rscript plot_regression_res.R plot-spec-cond-logistic-search-rate`
    * To run the analysis on analyzed population representativeness, run `Rscript plot_regression_res.R analyze-population-representativeness`
