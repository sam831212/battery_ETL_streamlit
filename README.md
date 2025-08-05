# Battery ETL Dashboard

A comprehensive dashboard for processing, analyzing, and visualizing battery test data using Streamlit and PostgreSQL.

## Project Overview

The Battery ETL Dashboard is designed to help battery researchers and engineers process and visualize battery test data. The application provides tools for:

- Uploading and processing battery test data files (Step.csv and Detail.csv)
- Validating data quality and identifying anomalies
- Transforming raw data into useful metrics (C-rate, SOC, etc.)
- Visualizing battery performance through interactive charts
- Storing processed data in a PostgreSQL database for future access

## Current Status

### Completed Features
- ✓ Basic UI structure with navigation
- ✓ Database models and connection setup
- ✓ Settings page with database connection management
- ✓ Upload page with file upload interface
- ✓ Dashboard page with visualization placeholders
- ✓ Data validation module
- ✓ ETL processing implementation for battery test data
- ✓ Visualization components for battery performance metrics by Metabase


### Planned Features
- Advanced analytics for battery degradation analysis
- Comparative visualization across multiple experiments
- Export functionality for processed data and reports
- User authentication and data access controls

## Technical Stack

- **Frontend**: Streamlit
- **Database**: PostgreSQL
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly, Streamlit native components
- **ORM**: SQLModel

## Project Structure

```
/
├── app/                    # Main application code
│   ├── etl/                # ETL processing logic
│   │   ├── validation.py   # Data validation functions
│   │   └── ...
│   ├── models/             # Database models
│   │   ├── database.py     # SQLModel definitions
│   │   └── ...
│   ├── ui/                 # Streamlit UI components
│   │   ├── dashboard.py    # Dashboard UI
│   │   ├── settings.py     # Settings UI
│   │   ├── upload.py       # Upload UI
│   │   └── ...
│   ├── utils/              # Utility functions
│   │   ├── config.py       # Configuration utilities
│   │   ├── database.py     # Database utilities
│   │   └── ...
│   └── visualization/      # Plotting functions
├── uploads/                # Directory for uploaded files
├── .streamlit/             # Streamlit configuration
│   └── config.toml         # Streamlit settings
├── streamlit_app.py        # Main application entry point
└── README.md               # Project documentation
```

## Setup and Installation

### Prerequisites
- Python 3.8+
- SQLite database

### Installation
1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd streamlit_project
   ```
2. Create a Python virtual environment and activate it (recommended):
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the root directory of the project with the following environment variables:
   ```
   DATABASE_URL="postgresql+psycopg2://user:password@host:port/database_name"
   # Example for SQLite (if used for local development):
   # DATABASE_URL="sqlite:///./test.db"
   ```
   Replace `user`, `password`, `host`, `port`, and `database_name` with your PostgreSQL database credentials. If using SQLite, uncomment the SQLite example.
5. Run the application:
   ```bash
   streamlit run main.py
   ```
   The application will typically open in your web browser at `http://localhost:8501`.

## Usage

1. **Upload Data**: Navigate to the "Upload & Process" page to upload Step.csv and Detail.csv files
2. **Process Data**: Fill in experiment information and process the uploaded files
3. **View Results**: Switch to the "Dashboard" page to view visualizations of the processed data
4. **Configure Settings**: Use the "Settings" page to manage database connections and application preferences

## Data Format

The application expects input data in the following formats:

### Step.csv
File containing step-level data with the following required columns:
- Step Number
- Step Type (Charge, Discharge, Rest)
- Start Time
- End Time
- Voltage (V)
- Current (A)
- Capacity (Ah)
- Energy (Wh)
- Temperature (°C)

### Detail.csv
File containing detailed measurement data with the following required columns:
- Step Number
- Time
- Voltage (V)
- Current (A)
- Temperature (°C)
- Capacity (Ah)
- Energy (Wh)

## Future Development

The next phases of development will focus on:
1. Implementing the ETL processing logic for battery test data
2. Developing advanced visualization components
3. Enhancing the dashboard with filtering and comparative analysis tools
4. Adding user authentication and access controls