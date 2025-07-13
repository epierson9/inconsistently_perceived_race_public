# Reproduction code for "Testing for racial bias using inconsistent perceptions of race" (Gera and Pierson, 2024)

# System requirements, software requirements, and installation guide

## Hardware and OS requirements
No non-standard hardware is required to run this code, only a standard computer with enough RAM and suitable CPU (the machine we tested on had 60GB RAM, CPU with 16 cores at 2.6GHz/core, and at least 200 GB of memory). The code runs on Linux and should run on macOS; this software has been tested on Linux Ubuntu 20.04.6 LTS.

## Software requirements
### Python dependencies
We use Python (3.13.1) for preprocessing; the following are the package dependencies:
```
pandas=2.2.3
matplotlib=3.9.3
numpy=2.2.0
scipy=1.14.1
ipython=8.30.0
statsmodels=0.14.4
linearmodels=6.1
```

### R dependencies
We use R (4.4.2) for analysis; from an R terminal, you can install the package dependencies:
```R
install.packages(c('xtable', 'data.table', 'magrittr', 'scales', 'dplyr', 'tidyr', 'tidyverse', 'ggplot2', 'fixest', 'patchwork', 'lme4', 'survival', 'alpaca', 'broom', 'stringr'))
```
Below is the specific versioning of those packages:
```
xtable=1.8.4
data.table=1.15.4
magrittr=2.0.3
scales=1.3.0
dplyr=1.1.4
tidyr=1.3.1
tidyverse=2.0.0
ggplot2=3.5.1
fixest=0.12.1
patchwork=1.3.0
lme4=1.1.35.5
survival=3.7.0
alpaca=0.3.4
broom=1.0.7
stringr=1.5.1
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
There are two options for producing the processed data that is used in the statistical analyses.
## Option 1: Processing from Raw Data
1. Raw data can be obtained by contacting the authors of the Open Policing Project at open-policing@lists.stanford.edu.
2. _Preprocess raw data to get raw csv files_ (est. 10 mins - 1 hour per state): Use the following [fork](https://github.com/epierson9/emma_fork_of_openpolicing_repo/tree/master) of the Open Policing Project repo to process the state data for Arizona, Colorado, and Texas. Set the `reprocess_state_data` [flag](https://github.com/epierson9/emma_fork_of_openpolicing_repo/blob/master/src/recreate_results_in_paper.R#L29) to `TRUE` in `src/recreate_results_in_paper.R`, and run this script to generate clean csv files for each state (ex. `AZ-clean.csv`).
3. _Process the raw csv files_ (est. runtime: 3-10 mins per state): For each state, run the state-specific python file (ex. `az.py`) to standardize entries and filter the raw state data down to the set of multiply stopped drivers and inconsistently-perceived drivers. `policing_data_expl.py` contains all the processing code and generates csv files in the `csv` folder that are used later on in the analysis; this file is used as a module for the state-specific python files, so it shouldn't be directly. 
    * Before running `python az.py`, `python co.py`,  or `python tx.py`, replace `path-to-clean-csv` in the `config` with the path to the clean state data you downloaded.
    * This step outputs 9 csv files, 3 csv files per state, and these will be used in the statistical analysis; the filenames will start with the state prefix (ex. `az_`)
## Option 2: Using the anonymized, processed data provided in the `csv/processed_data` folder
To ensure reproducibility of our results, we also provide anonymized, processed versions of the raw data (with driver and officer identifiers replaced with anonymized hashes); this is the easier way to reproduce our results unless you have specific reasons to need the original raw data. The files are individually zipped and are available in the `csv/processed_data` folder. They were created using the script `filter_processed_data.py` that filters Option 1's output to a reduced set of columns and hashes driver and officer ids to anonymize any PII data, and these csv files can be used to run the analyses.

Unzip the 9 zipped csv files (3 per state) before proceeding with the statistical analysis; all filenames begin with `filtered_` followed by the state prefix (ex. `csv/processed_data/filtered_az...`).
## Perform statistical analyses
1. This includes running regressions using different models to estimate differences in search and arrest rates, along with analyzing the representativeness of our analyzed population, to reproduce the results in the paper. `plot_regression_res.R` contains the code to reproduce the figures in the paper (est. runtime: 5-10 mins per regression); `make_descriptive_stats_table.R` contains the code to reproduce the descriptive stats table (est. runtime: 1hr). Analysis of the processed state data reproduces the figures and table in the paper.
    * The `plots/` directory will contain all the resulting figures and tables
    * Replace `path-to-STATE-data.csv` (ex. `path-to-AZ-data.csv`) with the path to that state's raw data before running the R script (if you used option 2 and are running with the provided anonymized, processed data, there are 9 places to update file paths, 3 per state in the [beginning part](https://github.com/epierson9/inconsistently_perceived_race_public/blob/main/plot_regression_res.R#L54-L106) of the `read_processed_csv` function)
    * To run the regressions with the linear probability model on search rate (Figure 1), run `Rscript plot_regression_res.R plot-primary-spec-feols-search-rate`
    * To run the regressions with linear probability model on arrest rate (Figure S1), run `Rscript plot_regression_res.R plot-primary-spec-feols-arrest-rate`
    * To run the regressions with the linear probability model on Arizona search rates, run `Rscript plot_regression_res.R plot-primary-spec-feols-az-stop-duration`
    * To run the fixed-effects generalized model with logit link regression on search rate (Figure S2), run `Rscript plot_regression_res.R plot-spec-feglm-search-rate`
    * To run the regressions with the conditional logit model on search rate (Figure S3), run `Rscript plot_regression_res.R plot-spec-cond-logistic-search-rate`
    * To run the analysis on analyzed population representativeness, run `Rscript plot_regression_res.R analyze-population-representativeness`
