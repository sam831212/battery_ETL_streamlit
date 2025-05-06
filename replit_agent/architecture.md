# Battery ETL Dashboard - Architecture

## Overview

The Battery ETL Dashboard is a comprehensive web application designed for processing, analyzing, and visualizing battery test data. It enables researchers and engineers to upload battery test data files, process them through an ETL (Extract, Transform, Load) pipeline, validate data quality, visualize battery performance through interactive charts, and store processed data in a PostgreSQL database for future access.

The application follows a modular architecture with clear separation of concerns between data processing, visualization, and storage components. It is primarily built as a Streamlit web application with a PostgreSQL backend database.

## System Architecture

The system follows a three-tier architecture:

1. **Presentation Layer**: Streamlit-based web interface for user interactions, file uploads, and data visualization
2. **Application Layer**: ETL processing logic, data validation, and transformation components
3. **Data Layer**: PostgreSQL database for structured storage of battery test data and metadata

### Key Design Decisions

- **Streamlit Framework**: Chosen for rapid development of data-focused web applications with minimal frontend code
- **SQLModel ORM**: Provides type-safe database access with SQLAlchemy compatibility and Pydantic integration
- **Modular ETL Pipeline**: Separates extraction, transformation, and loading concerns for maintainability
- **Alembic Migrations**: Manages database schema changes and versioning

## Key Components

### 1. User Interface (Streamlit)

The application uses Streamlit for its user interface, creating an interactive dashboard with the following pages:

- **Main Dashboard**: Overview of processed data and key metrics
- **Upload Page**: Interface for uploading and processing CSV files
- **Settings Page**: Database connection and application configuration management

### 2. ETL Pipeline

The ETL process is divided into three distinct modules:

- **Extraction (`app.etl.extraction`)**: 
  - Reads and validates CSV files (Step.csv and Detail.csv)
  - Parses data and detects file formats
  - Performs initial preprocessing
  
- **Transformation (`app.etl.transformation`)**:
  - Calculates derived metrics (C-rate, SOC, etc.)
  - Normalizes data
  - Identifies charge/discharge cycles
  
- **Loading (`app.utils.database`)**:
  - Stores processed data in the PostgreSQL database
  - Manages database sessions and connections

### 3. Data Validation

Data quality is ensured through a dedicated validation module (`app.etl.validation`) that:
- Detects anomalies in voltage, current, and temperature readings
- Generates validation reports
- Provides summary tables of data quality metrics

### 4. Database Models

The application uses SQLModel to define the database schema with the following key models:

- **Experiment**: Represents a battery test experiment with metadata
- **Step**: Represents test steps within an experiment (charge, discharge, rest)
- **Measurement**: Contains detailed measurements within a step
- **Cell**: Stores information about battery cells being tested
- **Machine**: Represents testing equipment used in experiments
- **ProcessedFile**: Tracks processed files to prevent duplicates

### 5. Visualization Components

Visualization is handled by the `app.visualization` module using Plotly for interactive charts:
- Capacity vs. voltage plots
- Voltage and current vs. time charts
- Combined multi-metric visualizations

## Data Flow

1. **Data Ingestion**:
   - Users upload CSV files (Step.csv and Detail.csv) through the Streamlit interface
   - Files are saved to a temporary location and validated

2. **ETL Processing**:
   - CSV files are parsed and validated for required headers
   - Raw data is transformed into standardized metrics
   - Derived calculations (C-rate, SOC, etc.) are performed
   - Data quality validation is executed

3. **Database Storage**:
   - Processed data is mapped to database models
   - Data is stored in PostgreSQL database tables
   - File metadata is tracked to prevent duplicate processing

4. **Data Retrieval and Visualization**:
   - Stored data is queried from the database
   - Visualization components transform data into interactive plots
   - Users interact with visualizations through the Streamlit interface

## External Dependencies

The application relies on the following key external dependencies:

- **PostgreSQL**: Primary database for structured data storage
- **Streamlit**: Web application framework
- **Pandas/NumPy**: Data processing and numerical calculations
- **Plotly**: Interactive data visualization
- **SQLModel**: ORM for database access
- **Alembic**: Database schema migration tool
- **Pytest**: Testing framework

## Deployment Strategy

The application is configured for deployment via Replit's autoscaling infrastructure, as evidenced by the `.replit` configuration file. The deployment strategy includes:

- **Containerized Runtime**: Uses Python 3.11 and PostgreSQL 16 modules
- **Port Configuration**: Streamlit runs on port 5000, mapped to external port 80
- **Environment Variables**: Configuration stored in `.env` files
- **Database Migrations**: Managed through Alembic for schema versioning

### Development Workflow

The repository includes a testing workflow that allows developers to:
1. Test transformations on example data without database dependencies
2. Run unit and integration tests with pytest
3. Apply database migrations with Alembic

## Security Considerations

- Database credentials are stored in environment variables
- The application does not appear to implement user authentication currently
- Database access is managed through SQLModel sessions to prevent SQL injection

## Future Architecture Extensions

Based on the repository's progress indicators, these areas are planned for architectural expansion:

- Advanced analytics for battery degradation analysis
- Comparative visualization across multiple experiments
- Export functionality for processed data and reports
- User authentication and data access controls