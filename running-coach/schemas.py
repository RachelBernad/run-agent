"""Pydantic schemas for request and response models."""

from typing import List, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from settings import (
    MSG_GOAL_TOO_SMALL, MSG_GOAL_TOO_LARGE, MSG_TIME_TOO_SHORT, MSG_TIME_TOO_LONG
)

class ProgramRequest(BaseModel):
    """Request model for creating a running program."""
    
    goal_km: float = Field(
        ..., 
        ge=1.0, 
        le=1000.0, 
        description="Distance goal in kilometers"
    )
    time_weeks: int = Field(
        ..., 
        ge=1, 
        le=52, 
        description="Time to achieve goal in weeks"
    )
    
    @field_validator('goal_km')
    def validate_goal_km(cls, v):
        if v < 1.0:
            raise ValueError(MSG_GOAL_TOO_SMALL)
        if v > 1000.0:
            raise ValueError(MSG_GOAL_TOO_LARGE)
        return v
    
    @field_validator('time_weeks')
    def validate_time_weeks(cls, v):
        if v < 1:
            raise ValueError(MSG_TIME_TOO_SHORT)
        if v > 52:
            raise ValueError(MSG_TIME_TOO_LONG)
        return v


class WeekPlan(BaseModel):
    """Weekly training plan."""
    
    week_number: int = Field(..., description="Week number in the program")
    total_distance_km: float = Field(..., description="Total distance for the week")
    runs_per_week: int = Field(..., description="Number of runs per week")
    long_run_km: float = Field(..., description="Distance of the longest run")
    easy_runs_km: List[float] = Field(..., description="Distances for easy runs")
    notes: str = Field(..., description="Weekly training notes and tips")


class Recommendation(BaseModel):
    """Running recommendation."""
    
    category: str = Field(..., description="Category of recommendation")
    title: str = Field(..., description="Title of the recommendation")
    description: str = Field(..., description="Detailed description")
    priority: str = Field(..., description="Priority level (high, medium, low)")


class ProgramResponse(BaseModel):
    """Response model for a running program."""
    
    program_id: str = Field(..., description="Unique program identifier")
    goal_km: float = Field(..., description="Original goal distance")
    time_weeks: int = Field(..., description="Original time frame")
    weekly_plans: List[WeekPlan] = Field(..., description="Weekly training plans")
    recommendations: List[Recommendation] = Field(..., description="General recommendations")
    created_at: str = Field(..., description="Program creation timestamp")


class HistoryResponse(BaseModel):
    """Response model for program history."""
    
    total_programs: int = Field(..., description="Total number of programs")
    programs: List[ProgramResponse] = Field(..., description="List of all programs")


class RunData(BaseModel):
    """Individual run data."""
    
    distance_m: float = Field(..., description="Distance in meters")
    duration_sec: int = Field(..., description="Duration in seconds")
    average_speed_m_s: float = Field(..., description="Average speed in m/s")
    avg_cadence: Optional[int] = Field(None, description="Average cadence")
    average_hr: Optional[int] = Field(None, description="Average heart rate")
    date: str = Field(..., description="Run date in YYYY-MM-DD format")


class RunningPlan(BaseModel):
    """Current running plan structure."""
    
    weeks: int = Field(..., description="Total weeks in plan")
    target_distances: List[float] = Field(..., description="Target distances per week in km")
    workouts_per_day: List[int] = Field(..., description="Workouts per day per week")


class ProgressData(BaseModel):
    """Progress tracking data."""
    
    completed_weeks: int = Field(..., description="Number of completed weeks")
    completed_workouts: int = Field(..., description="Number of completed workouts")
    total_distance_completed_km: float = Field(..., description="Total distance completed in km")
    total_distance_target_km: float = Field(..., description="Total target distance in km")


class PlanAnalysisRequest(BaseModel):
    """Request for running plan analysis."""
    
    program_id: str = Field(..., description="Program ID to analyze")
    current_date: str = Field(..., description="Current date in YYYY-MM-DD format")
    days_back: int = Field(30, description="Number of days back to fetch runs from Garmin")


class PlanAnalysisResponse(BaseModel):
    """Response from running plan analysis."""
    
    plan_status: Literal["on_track", "behind", "ahead", "completed", "needs_new_plan"] = Field(
        ..., description="Current plan status"
    )
    summary: str = Field(..., description="Short summary of progress and challenges")
    progress_data: ProgressData = Field(..., description="Progress tracking data")
    recommendations: List[str] = Field(..., description="List of recommendations")
    next_steps: str = Field(..., description="Next steps recommendation")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    program_id: Optional[str] = Field(None, description="Program ID if applicable")
