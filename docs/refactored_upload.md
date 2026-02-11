# Function Documentation for refactored_upload.py

## Module Dependencies
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union

## Functions

### render_entity_management
```python
def render_entity_management(entity_type, entity_class, header_text, form_fields, display_fields, reference_check)
"""
Generic entity management UI component

Args:
    entity_type: String name of the entity type (e.g., "cell", "machine")
    entity_class: The SQLModel class for the entity
    header_text: Text to display as the header
    form_fields: List of dictionaries defining form fields for adding entities
    display_fields: List of dictionaries mapping entity attributes to display names
    reference_check: Optional function to check if entity can be deleted
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### cell_reference_check
```python
def cell_reference_check(session, cell_id)
"""
Check if a cell can be safely deleted
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### check_file_already_processed
```python
def check_file_already_processed(file_hash: str) -> bool
"""
Check if a file with the given hash has already been processed.

Args:
    file_hash: Hash value of the file
    
Returns:
    True if already processed, False otherwise
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### display_file_statistics
```python
def display_file_statistics(step_df: pd.DataFrame, detail_df: pd.DataFrame)
"""
Display statistics for uploaded CSV files.

Args:
    step_df: Step data DataFrame
    detail_df: Detail data DataFrame
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### validate_files
```python
def validate_files(step_file_path: str, detail_file_path: str) -> Tuple[bool, bool, List[str], List[str], List[str], List[str]]
"""
Validate the format of step and detail files.

Args:
    step_file_path: Path to the step file
    detail_file_path: Path to the detail file
    
Returns:
    Tuple containing:
    - Whether step file is valid
    - Whether detail file is valid
    - Missing headers in step file
    - Missing headers in detail file
    - All headers in step file
    - All headers in detail file
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### display_validation_results
```python
def display_validation_results(step_valid: bool, detail_valid: bool, step_missing: List[str], detail_missing: List[str])
"""
Display validation results for the files.

Args:
    step_valid: Whether step file is valid
    detail_valid: Whether detail file is valid
    step_missing: Missing headers in step file
    detail_missing: Missing headers in detail file
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### generate_validation_results
```python
def generate_validation_results(step_df: pd.DataFrame, detail_df: pd.DataFrame) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]
"""
Generate validation reports for step and detail data.

Args:
    step_df: Step data DataFrame
    detail_df: Detail data DataFrame
    
Returns:
    Tuple containing:
    - Overall validation status
    - Step validation report
    - Detail validation report
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### display_validation_summary
```python
def display_validation_summary(validation_status: bool, step_validation_report: Dict[str, Any], detail_validation_report: Dict[str, Any])
"""
Display validation summary for the data.

Args:
    validation_status: Overall validation status
    step_validation_report: Step validation report
    detail_validation_report: Detail validation report
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### get_file_data_and_metadata
```python
def get_file_data_and_metadata(step_source: Union[str, BinaryIO], detail_source: Union[str, BinaryIO], is_example_file: bool) -> Dict[str, Any]
"""
Get file data and metadata depending on source type.

This helper function handles the differences between example files (paths)
and uploaded files (UploadedFile objects).

Args:
    step_source: Either a file path (for example files) or an UploadedFile object
    detail_source: Either a file path (for example files) or an UploadedFile object
    is_example_file: Whether the source is an example file
    
Returns:
    Dictionary containing:
    - step_df: DataFrame with step data
    - detail_df: DataFrame with detail data
    - step_file_path: Path to step file (temp file for uploads)
    - detail_file_path: Path to detail file (temp file for uploads)
    - step_file_hash: Hash of step file
    - detail_file_hash: Hash of detail file
    - step_filename: Original filename of step file
    - detail_filename: Original filename of detail file
    - is_uploaded_file: Whether temp files were created for upload
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### handle_file_processing_pipeline
```python
def handle_file_processing_pipeline(file_data: Dict[str, Any]) -> bool
"""
Handle the complete file processing pipeline.

This function handles the entire workflow from validation to ETL to database
saving and UI feedback, regardless of file source.

Args:
    file_data: Dictionary with file data and metadata from get_file_data_and_metadata
    
Returns:
    True if processing was successful, False otherwise
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### save_experiment_to_db
```python
def save_experiment_to_db(experiment_metadata: Dict[str, Any], validation_report: Dict[str, Any], cell_id: int, machine_id: int, battery_type: str, temperature: float) -> Experiment
"""
Create and save a new experiment record in the database.

Args:
    experiment_metadata: Metadata about the experiment
    validation_report: Validation report
    cell_id: ID of the cell used in the experiment
    machine_id: ID of the machine used in the experiment
    battery_type: Type of battery used
    temperature: Average temperature
    
Returns:
    Created Experiment object
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### convert_datetime_to_python
```python
def convert_datetime_to_python(value)
"""
將各種日期時間格式轉換為 Python datetime 物件

Args:
    value: 輸入的日期時間值（可以是字串、pd.Timestamp 或 datetime）
    
Returns:
    Python datetime 物件或 None
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### save_steps_to_db
```python
def save_steps_to_db(experiment_id: int, steps_df: pd.DataFrame, nominal_capacity: float) -> List[Step]
"""
Save step data to the database.

Args:
    experiment_id: ID of the experiment
    steps_df: Step data DataFrame
    nominal_capacity: Nominal capacity of the battery
    
Returns:
    List of created Step objects
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### save_measurements_to_db
```python
def save_measurements_to_db(experiment_id: int, details_df: pd.DataFrame, step_mapping: Dict[int, int], nominal_capacity: float, batch_size: int)
"""
保存測量數據到資料庫
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### save_processed_files_to_db
```python
def save_processed_files_to_db(experiment_id: int, step_filename: str, detail_filename: str, step_file_hash: str, detail_file_hash: str, step_df_len: int, detail_df_len: int, step_metadata: Dict[str, Any], detail_metadata: Dict[str, Any])
"""
Save processed file records to the database.

Args:
    experiment_id: ID of the experiment
    step_filename: Filename of the step file
    detail_filename: Filename of the detail file
    step_file_hash: Hash of the step file
    detail_file_hash: Hash of the detail file
    step_df_len: Number of rows in step DataFrame
    detail_df_len: Number of rows in detail DataFrame
    step_metadata: Metadata about the step file
    detail_metadata: Metadata about the detail file
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### update_experiment_end_date
```python
def update_experiment_end_date(experiment_id: int, end_time: datetime)
"""
Update the end date of an experiment.

Args:
    experiment_id: ID of the experiment
    end_time: End time to set
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### find_example_file_pairs
```python
def find_example_file_pairs() -> List[Tuple[str, str, str]]
"""
Find matching step and detail file pairs in the example folder.

Returns:
    List of tuples containing (base_name, step_file, detail_file)
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### machine_reference_check
```python
def machine_reference_check(session, machine_id)
"""
Check if a machine can be safely deleted
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_machine_management
```python
def render_machine_management()
"""
Render machine management UI
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_cell_management
```python
def render_cell_management()
"""
Render cell management UI
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_experiment_metadata
```python
def render_experiment_metadata(cells, machines, has_data_from_preview)
"""
Render experiment metadata form
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### save_experiment_metadata
```python
def save_experiment_metadata(experiment_name, nominal_capacity, selected_cell_id, experiment_date, operator, description, selected_machine_id, cells, machines)
"""
Save experiment metadata to session state
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_preview_data_section
```python
def render_preview_data_section()
"""
Render UI section for data from preview page
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### handle_selected_steps_save
```python
def handle_selected_steps_save()
"""
Handle saving selected steps to database
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_example_files_section
```python
def render_example_files_section()
"""
Render UI section for example files
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### process_loaded_example_files
```python
def process_loaded_example_files()
"""
Process loaded example files
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_file_upload_section
```python
def render_file_upload_section()
"""
Render UI section for regular file uploads
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### process_uploaded_files
```python
def process_uploaded_files(step_file, detail_file)
"""
Process uploaded files from user
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```

### render_upload_page
```python
def render_upload_page()
"""
Render the upload page UI

This function displays the experiment information components.
"""

Dependencies:
- app.etl.convert_numpy_types
- app.etl.extraction.DETAIL_REQUIRED_HEADERS
- app.etl.extraction.STEP_REQUIRED_HEADERS
- app.etl.load_and_preprocess_files
- app.etl.parse_detail_csv
- app.etl.parse_step_csv
- app.etl.validate_csv_format
- app.etl.validation.generate_validation_report
- app.models.Cell
- app.models.Experiment
- app.models.Machine
- app.models.Measurement
- app.models.ProcessedFile
- app.models.Step
- app.models.database.CellChemistry
- app.models.database.CellFormFactor
- app.utils.config.UPLOAD_FOLDER
- app.utils.database.get_session
- app.utils.temp_files.calculate_file_hash
- app.utils.temp_files.calculate_file_hash_from_memory
- app.utils.temp_files.create_session_temp_file
- app.utils.temp_files.temp_file_from_upload
- datetime.datetime
- hashlib
- os
- pandas
- sqlmodel.delete
- sqlmodel.desc
- sqlmodel.func
- sqlmodel.select
- streamlit
- typing.Any
- typing.BinaryIO
- typing.Dict
- typing.List
- typing.Optional
- typing.Tuple
- typing.Union
```
