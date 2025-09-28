#!/usr/bin/env python3
"""
Simple unit tests for Garmin MCP server functions.
Tests the underlying functions directly without HTTP calls.
"""

import asyncio
import os
import pytest
from typing import Dict, Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the underlying functions from server
from server import (
    _authenticate_garmin, 
    _get_date_range, 
    _fetch_activities, 
    summarize_run,
    week_key,
    aggregate_weekly
)


class TestGarminFunctions:
    """Test class for Garmin MCP server functions."""
    
    @pytest.fixture
    def credentials(self):
        """Get Garmin credentials from environment."""
        username = os.getenv('GARMIN_USERNAME')
        password = os.getenv('GARMIN_PASSWORD')
        
        if not username or not password:
            pytest.skip("Garmin credentials not found in environment variables")
        
        return {"username": username, "password": password}
    
    def test_get_date_range(self):
        """Test date range calculation."""
        start_date, end_date = _get_date_range(7)
        
        # Check that dates are correct
        assert start_date is not None
        assert end_date is not None
        assert (end_date - start_date).days == 7
    
    @pytest.mark.asyncio
    async def test_authenticate_garmin(self, credentials):
        """Test Garmin authentication."""
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        assert client is not None
    
    @pytest.mark.asyncio
    async def test_fetch_activities_7_days(self, credentials):
        """Test fetching activities for 7 days."""
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        start_date, end_date = _get_date_range(7)
        
        activities = _fetch_activities(client, start_date, end_date)
        
        # Should find the treadmill run
        assert len(activities) == 1
        assert activities[0]["activityType"]["typeKey"] == "treadmill_running"
    
    @pytest.mark.asyncio
    async def test_fetch_activities_30_days(self, credentials):
        """Test fetching activities for 30 days."""
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        start_date, end_date = _get_date_range(30)
        
        activities = _fetch_activities(client, start_date, end_date)
        
        # Should find the treadmill run
        assert len(activities) == 1
        assert activities[0]["activityType"]["typeKey"] == "treadmill_running"
    
    @pytest.mark.asyncio
    async def test_fetch_activities_90_days(self, credentials):
        """Test fetching activities for 90 days."""
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        start_date, end_date = _get_date_range(90)
        
        activities = _fetch_activities(client, start_date, end_date)
        
        # Should find the treadmill run
        assert len(activities) == 1
        assert activities[0]["activityType"]["typeKey"] == "treadmill_running"
    
    def test_summarize_run(self, credentials):
        """Test run summarization."""
        # Create a mock run data structure
        mock_run = {
            "activityId": 123456789,
            "startTimeLocal": "2025-09-25T21:00:05",
            "distance": 580,
            "duration": 282,
            "movingDuration": 275,
            "averageSpeed": 2.06,
            "maxSpeed": 3.5,
            "averageHeartRate": None,
            "maxHeartRate": None,
            "averageRunningCadenceInStepsPerMinute": 180,
            "maxRunningCadenceInStepsPerMinute": 190,
            "steps": 520,
            "summarizedActivityLevel": 350,
            "waterEstimated": 500,
            "splitSummaries": []
        }
        
        summary = summarize_run(mock_run)
        
        # Check required fields
        assert summary["activity_id"] == 123456789
        assert summary["start_time_local"] == "2025-09-25T21:00:05"
        assert summary["distance_m"] == 580
        assert summary["duration_sec"] == 282
        assert summary["moving_duration_sec"] == 275
        assert summary["average_speed_m_s"] == 2.06
        assert summary["max_speed_m_s"] == 3.5
        assert summary["average_hr"] is None
        assert summary["max_hr"] is None
        assert summary["avg_cadence"] == 180
        assert summary["max_cadence"] == 190
        assert summary["steps"] == 520
        assert summary["calories"] == 350
        assert summary["water_estimated_ml"] == 500
        
        # Check calculated fields
        assert abs(summary["pace_min_per_km"] - 8.11) < 0.1
        assert abs(summary["moving_ratio"] - 0.975) < 0.01
        assert summary["splits"] == []
    
    @pytest.mark.asyncio
    async def test_get_recent_running_summaries_7_days(self, credentials):
        """Test the main MCP function with 7 days."""
        # Test the underlying logic directly
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        start_date, end_date = _get_date_range(7)
        activities = _fetch_activities(client, start_date, end_date)
        results = [summarize_run(activity) for activity in activities]
        
        # Should find the treadmill run
        assert len(results) == 1
        
        run = results[0]
        assert run["start_time_local"] == "2025-09-25 21:00:05"
        assert abs(run["distance_m"] - 577.6) < 1  # Allow small floating point differences
        assert run["duration_sec"] == 282
        assert abs(run["pace_min_per_km"] - 8.11) < 0.1
    
    @pytest.mark.asyncio
    async def test_get_recent_running_summaries_30_days(self, credentials):
        """Test the main MCP function with 30 days."""
        # Test the underlying logic directly
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        start_date, end_date = _get_date_range(30)
        activities = _fetch_activities(client, start_date, end_date)
        results = [summarize_run(activity) for activity in activities]
        
        # Should find the treadmill run
        assert len(results) == 1
        
        run = results[0]
        assert run["start_time_local"] == "2025-09-25 21:00:05"
        assert abs(run["distance_m"] - 577.6) < 1  # Allow small floating point differences
        assert run["duration_sec"] == 282
        assert abs(run["pace_min_per_km"] - 8.11) < 0.1
    
    @pytest.mark.asyncio
    async def test_get_recent_running_summaries_90_days(self, credentials):
        """Test the main MCP function with 90 days."""
        # Test the underlying logic directly
        client = _authenticate_garmin(credentials["username"], credentials["password"])
        start_date, end_date = _get_date_range(90)
        activities = _fetch_activities(client, start_date, end_date)
        results = [summarize_run(activity) for activity in activities]
        
        # Should find the treadmill run
        assert len(results) == 1
        
        run = results[0]
        assert run["start_time_local"] == "2025-09-25 21:00:05"
        assert abs(run["distance_m"] - 577.6) < 1  # Allow small floating point differences
        assert run["duration_sec"] == 282
        assert abs(run["pace_min_per_km"] - 8.11) < 0.1
    
    def test_invalid_credentials(self):
        """Test with invalid credentials."""
        with pytest.raises(RuntimeError, match="Garmin login failed"):
            _authenticate_garmin("invalid@example.com", "wrongpassword")
    
    def test_week_key(self):
        """Test week key calculation."""
        # Test with a known date
        key = week_key("2025-09-25T21:00:05")
        assert isinstance(key, tuple)
        assert len(key) == 2
        assert isinstance(key[0], int)  # year
        assert isinstance(key[1], int)  # week number
    
    def test_aggregate_weekly_single_run(self):
        """Test weekly aggregation with a single run."""
        mock_runs = [
            {
                "start_time_local": "2025-09-25T21:00:05",
                "distance_m": 577.6,
                "duration_sec": 282,
                "moving_duration_sec": 275,
                "average_speed_m_s": 2.05,
                "max_speed_m_s": 3.5,
                "average_hr": 150,
                "max_hr": 165,
                "avg_cadence": 180,
                "max_cadence": 190,
                "steps": 520,
                "calories": 350,
                "pace_min_per_km": 8.11,
                "moving_ratio": 0.975
            }
        ]
        
        weekly_summary = aggregate_weekly(mock_runs)
        
        # Should have one week
        assert len(weekly_summary) == 1
        
        # Get the week data
        week_data = list(weekly_summary.values())[0]
        
        # Check aggregated values
        assert abs(week_data["total_distance_km"] - 0.5776) < 0.001
        assert abs(week_data["total_duration_h"] - 0.0783) < 0.001  # 282/3600
        assert abs(week_data["total_moving_h"] - 0.0764) < 0.001  # 275/3600
        assert week_data["total_steps"] == 520
        assert week_data["total_calories"] == 350
        assert abs(week_data["avg_pace_min_per_km"] - 8.11) < 0.1
        assert week_data["max_speed_m_s"] == 3.5
        assert week_data["average_hr"] == 150
        assert week_data["max_hr"] == 165
        assert week_data["average_cadence"] == 180
        assert week_data["max_cadence"] == 190
        assert abs(week_data["avg_moving_ratio"] - 0.975) < 0.01
        assert week_data["run_count"] == 1
    
    def test_aggregate_weekly_multiple_runs(self):
        """Test weekly aggregation with multiple runs in the same week."""
        mock_runs = [
            {
                "start_time_local": "2025-09-25T21:00:05",
                "distance_m": 1000,
                "duration_sec": 300,
                "moving_duration_sec": 290,
                "average_speed_m_s": 3.33,
                "max_speed_m_s": 4.0,
                "average_hr": 150,
                "max_hr": 165,
                "avg_cadence": 180,
                "max_cadence": 190,
                "steps": 1000,
                "calories": 400,
                "pace_min_per_km": 5.0,
                "moving_ratio": 0.967
            },
            {
                "start_time_local": "2025-09-27T19:00:00",
                "distance_m": 2000,
                "duration_sec": 600,
                "moving_duration_sec": 580,
                "average_speed_m_s": 3.33,
                "max_speed_m_s": 4.5,
                "average_hr": 155,
                "max_hr": 170,
                "avg_cadence": 185,
                "max_cadence": 195,
                "steps": 2000,
                "calories": 800,
                "pace_min_per_km": 5.0,
                "moving_ratio": 0.967
            }
        ]
        
        weekly_summary = aggregate_weekly(mock_runs)
        
        # Should have one week
        assert len(weekly_summary) == 1
        
        # Get the week data
        week_data = list(weekly_summary.values())[0]
        
        # Check aggregated values
        assert abs(week_data["total_distance_km"] - 3.0) < 0.001  # 1km + 2km
        assert abs(week_data["total_duration_h"] - 0.25) < 0.001  # (300+600)/3600
        assert abs(week_data["total_moving_h"] - 0.2417) < 0.001  # (290+580)/3600
        assert week_data["total_steps"] == 3000  # 1000 + 2000
        assert week_data["total_calories"] == 1200  # 400 + 800
        assert abs(week_data["avg_pace_min_per_km"] - 5.0) < 0.1  # Both runs have same pace
        assert week_data["max_speed_m_s"] == 4.5  # Max of both runs
        assert week_data["average_hr"] == 152.5  # Average of 150 and 155
        assert week_data["max_hr"] == 170  # Max of both runs
        assert week_data["average_cadence"] == 182.5  # Average of 180 and 185
        assert week_data["max_cadence"] == 195  # Max of both runs
        assert abs(week_data["avg_moving_ratio"] - 0.967) < 0.01  # Same for both runs
        assert week_data["run_count"] == 2
    
    def test_aggregate_weekly_empty_runs(self):
        """Test weekly aggregation with empty runs list."""
        weekly_summary = aggregate_weekly([])
        assert len(weekly_summary) == 0
    
    def test_aggregate_weekly_missing_data(self):
        """Test weekly aggregation with runs missing some data."""
        mock_runs = [
            {
                "start_time_local": "2025-09-25T21:00:05",
                "distance_m": 1000,
                "duration_sec": 300,
                "moving_duration_sec": None,  # Missing data
                "average_speed_m_s": 3.33,
                "max_speed_m_s": 4.0,
                "average_hr": None,  # Missing data
                "max_hr": None,  # Missing data
                "avg_cadence": None,  # Missing data
                "max_cadence": None,  # Missing data
                "steps": 1000,
                "calories": 400,
                "pace_min_per_km": 5.0,
                "moving_ratio": None  # Missing data
            }
        ]
        
        weekly_summary = aggregate_weekly(mock_runs)
        
        # Should have one week
        assert len(weekly_summary) == 1
        
        # Get the week data
        week_data = list(weekly_summary.values())[0]
        
        # Check that missing data is handled gracefully
        assert week_data["total_distance_km"] == 1.0
        assert week_data["total_duration_h"] == 300/3600
        assert week_data["total_moving_h"] == 0  # None values filtered out
        assert week_data["total_steps"] == 1000
        assert week_data["total_calories"] == 400
        assert week_data["avg_pace_min_per_km"] == 5.0
        assert week_data["max_speed_m_s"] == 4.0
        assert week_data["average_hr"] is None  # No valid HR data
        assert week_data["max_hr"] is None  # No valid HR data
        assert week_data["average_cadence"] is None  # No valid cadence data
        assert week_data["max_cadence"] is None  # No valid cadence data
        assert week_data["avg_moving_ratio"] is None  # No valid moving ratio data
        assert week_data["run_count"] == 1


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
