# Battery ETL Dashboard

A modular web application designed to streamline the analysis of battery test data generated from cyclers.

## Overview

The Battery ETL Dashboard addresses the lack of standardized tools for researchers and engineers to process battery test data. It allows users to:

- Upload and process `Step.csv` (summary data) and `Detail.csv` (time series data linked by step index)
- Calculate State of Charge (SOC) baselines
- Classify and select relevant test steps
- Store the data systematically
- Visualize results through customizable plots

All of this functionality is available without requiring users to write custom analysis scripts or manual data processing.

## Features

- **Data Upload**: Upload Step.csv and Detail.csv files from cyclers (currently supporting ChromaLex format)
- **ETL Engine**: Extract, transform, and load battery test data
- **SOC Calculation**: Automatically calculate SOC baselines based on a full discharge reference step
- **Step Classification**: Identify and select relevant charge/discharge steps for analysis
- **Data Validation**: Validate data for plausibility and completeness
- **Data Visualization**: Generate predefined and custom plots for battery analysis
- **Data Storage**: Structured PostgreSQL database for storing processed data
- **Dashboard**: Interactive dashboard for exploring and visualizing results

## Technology Stack

- **Frontend**: Streamlit web framework
- **Backend**: Python (Pandas for data manipulation, custom logic for ETL/calculations)
- **Database**: PostgreSQL
- **ORM**: SQLModel
- **Visualization**: Plotly

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-organization/battery-etl-dashboard.git
   cd battery-etl-dashboard
   