"""
Database models for the Battery ETL Dashboard

This module defines SQLModel classes for the battery test data schema,
including experiments, test steps, and measurement details.
"""
from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Column, JSON


class BaseModel(SQLModel):
    """Base model with common fields and methods"""
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class Experiment(BaseModel, table=True):
    """Model representing a battery test experiment"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, index=True)
    description: Optional[str] = Field(default=None)
    battery_type: str = Field(nullable=False)
    nominal_capacity: float = Field(nullable=False)  # Ah
    temperature_avg: Optional[float] = Field(default=None)  # Average test temperature in Celsius
    operator: Optional[str] = Field(default=None)
    start_date: datetime = Field(nullable=False)
    end_date: Optional[datetime] = Field(default=None)
    metadata: dict = Field(default={}, sa_column=Column(JSON))
    
    # Relationships
    steps: List["Step"] = Relationship(back_populates="experiment")


class Step(BaseModel, table=True):
    """Model representing a test step within an experiment"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id", nullable=False)
    step_number: int = Field(nullable=False)
    step_type: str = Field(nullable=False)  # charge, discharge, rest
    start_time: datetime = Field(nullable=False)
    end_time: Optional[datetime] = Field(default=None)
    duration: float  # seconds
    voltage_start: float  # V
    voltage_end: float  # V
    current: float  # A
    capacity: float  # Ah
    energy: float  # Wh
    temperature_avg: float  # Celsius
    temperature_min: float  # Celsius
    temperature_max: float  # Celsius
    c_rate: float  # C
    soc_start: Optional[float] = Field(default=None)  # %
    soc_end: Optional[float] = Field(default=None)  # %
    ocv: Optional[float] = Field(default=None)  # V
    metadata: dict = Field(default={}, sa_column=Column(JSON))
    
    # Relationships
    experiment: "Experiment" = Relationship(back_populates="steps")
    measurements: List["Measurement"] = Relationship(back_populates="step")


class Measurement(BaseModel, table=True):
    """Model representing detailed measurements within a step"""
    id: Optional[int] = Field(default=None, primary_key=True)
    step_id: int = Field(foreign_key="step.id", nullable=False)
    timestamp: datetime = Field(nullable=False)
    voltage: float  # V
    current: float  # A
    temperature: float  # Celsius
    capacity: float  # Ah
    energy: float  # Wh
    soc: Optional[float] = Field(default=None)  # %
    
    # Relationship
    step: "Step" = Relationship(back_populates="measurements")


class ProcessedFile(BaseModel, table=True):
    """Model to track processed files to prevent duplicates"""
    id: Optional[int] = Field(default=None, primary_key=True)
    experiment_id: int = Field(foreign_key="experiment.id", nullable=False)
    filename: str = Field(nullable=False)
    file_type: str = Field(nullable=False)  # step, detail
    file_hash: str = Field(nullable=False, unique=True)
    processed_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    row_count: int = Field(nullable=False)
    metadata: dict = Field(default={}, sa_column=Column(JSON))
    
    # Relationship
    experiment: "Experiment" = Relationship()