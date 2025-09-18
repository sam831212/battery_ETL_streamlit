<img width="1598" height="724" alt="image" src="https://github.com/user-attachments/assets/8801cbc1-83e8-45a9-896e-d6f9e7dd46df" /># Battery ETL Dashboard

A comprehensive dashboard for processing, analyzing, and visualizing battery test data using Streamlit and SQLite.

## Project Overview

The Battery ETL Dashboard is designed to help battery researchers and engineers process and visualize battery test data. The application provides tools for:

- Uploading and processing battery test data files (e.g., Step.csv and Detail.csv).
- Validating data quality and identifying anomalies.
- Transforming raw data into useful metrics.
- Visualizing battery performance through interactive charts.
- Storing processed data in a local SQLite database for future access and analysis.

## Technical Stack

- **Frontend**: Streamlit
- **Database**: SQLite
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly, Streamlit native components
- **ORM**: SQLModel
- **Database Migrations**: Alembic

## Project Structure

```
/
├── app/                    # Main application code
│   ├── etl/                # ETL (Extract, Transform, Load) processing logic
│   ├── models/             # Database models (SQLModel)
│   ├── ui/                 # Streamlit UI components and pages
│   ├── utils/              # Utility functions (config, database helpers)
│   └── visualization/      # Plotting and visualization functions
├── migrations/             # Alembic database migration scripts
├── tests/                  # Pytest tests for the application
├── .streamlit/             # Streamlit configuration
│   └── config.toml         # Streamlit settings
├── main.py                 # Main application entry point
├── requirements.txt        # Project dependencies
├── battery.db              # SQLite database file
└── README.md               # Project documentation
```

## Setup and Installation

### Prerequisites
- Python 3.8+

### Installation
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```
2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Initialize the database:**
    The application will automatically create and initialize the `battery.db` file when you first run it. If you need to apply database migrations, you can use Alembic:
    ```bash
    alembic upgrade head
    ```

## Usage

1.  **Run the application:**
    ```bash
    streamlit run main.py
    ```
    The application will open in your web browser, typically at `http://localhost:8501`.

2.  **Using the Dashboard:**
    - **Data Preview**: Upload your battery test data files (e.g., `_detail.csv` and `_step.csv`).
    - **Step Selection**: Select the relevant steps from your data for analysis.
    - **Meta Data**: Add metadata for your experiment.
    - **Dashboard**: View visualizations and analysis of your data.
    - **Settings**: Configure application settings.
  
<img width="1598" height="724" alt="image" src="https://github.com/user-attachments/assets/9d936159-7f95-4f03-8d41-df4db77c69ac" />

