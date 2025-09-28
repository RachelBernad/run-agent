"""Activity summarization service for processing raw run data."""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from statistics import mean, median

from schemas import RunData

logger = logging.getLogger(__name__)


class ActivitySummarizer:
    """Summarizes recent running activity for LLM context."""
    
    def summarize_recent_activity(self, recent_runs: List[RunData], days_back: int = 30) -> Dict[str, Any]:
        """
        Summarize recent running activity into key metrics.
        
        Args:
            recent_runs: List of recent run data
            days_back: Number of days to look back for trend analysis
            
        Returns:
            Dictionary with summarized activity metrics
        """
        if not recent_runs:
            return self._get_default_summary()
        
        # Convert RunData to dictionaries for easier processing
        runs_data = [run.model_dump() for run in recent_runs]
        
        # Calculate basic metrics
        total_distance_km = sum(run["distance_m"] / 1000 for run in runs_data)
        total_duration_hours = sum(run["duration_sec"] / 3600 for run in runs_data)
        
        # Calculate pace metrics (convert from m/s to min/km)
        paces = []
        for run in runs_data:
            if run["average_speed_m_s"] > 0:
                pace_min_per_km = (1000 / run["average_speed_m_s"]) / 60  # Convert to min/km
                paces.append(pace_min_per_km)
        
        avg_pace = mean(paces) if paces else None
        median_pace = median(paces) if paces else None
        
        # Find longest run
        longest_run_km = max((run["distance_m"] / 1000 for run in runs_data), default=0)
        
        # Calculate weekly metrics
        weekly_distance_km = self._calculate_weekly_distance(runs_data)
        
        # Calculate trend (comparing recent weeks vs older weeks)
        trend = self._calculate_trend(runs_data, days_back)
        
        # Calculate consistency metrics
        runs_per_week = self._calculate_runs_per_week(runs_data)
        
        # Heart rate and cadence analysis (if available)
        hr_data = [run["average_hr"] for run in runs_data if run.get("average_hr")]
        avg_hr = mean(hr_data) if hr_data else None
        
        cadence_data = [run["avg_cadence"] for run in runs_data if run.get("avg_cadence")]
        avg_cadence = mean(cadence_data) if cadence_data else None
        
        summary = {
            "total_runs": len(runs_data),
            "total_distance_km": round(total_distance_km, 2),
            "total_duration_hours": round(total_duration_hours, 2),
            "weekly_distance_km": round(weekly_distance_km, 2),
            "longest_run_km": round(longest_run_km, 2),
            "avg_pace_min_per_km": round(avg_pace, 2) if avg_pace else None,
            "median_pace_min_per_km": round(median_pace, 2) if median_pace else None,
            "runs_per_week": round(runs_per_week, 1),
            "avg_hr": round(avg_hr) if avg_hr else None,
            "avg_cadence": round(avg_cadence) if avg_cadence else None,
            "trend": trend,
            "consistency_score": self._calculate_consistency_score(runs_data),
            "days_back": days_back
        }
        
        logger.info(f"Activity summarized - {len(runs_data)} runs, {weekly_distance_km:.1f}km/week, trend: {trend}")
        
        return summary
    
    def _calculate_weekly_distance(self, runs_data: List[Dict]) -> float:
        """Calculate average weekly distance."""
        if not runs_data:
            return 0.0
        
        # Group runs by week
        weekly_distances = {}
        for run in runs_data:
            try:
                run_date = datetime.strptime(run["date"], "%Y-%m-%d")
                week_key = run_date.strftime("%Y-W%U")
                
                if week_key not in weekly_distances:
                    weekly_distances[week_key] = 0
                
                weekly_distances[week_key] += run["distance_m"] / 1000
            except ValueError:
                logger.warning(f"Invalid date format: {run['date']}")
                continue
        
        if not weekly_distances:
            return 0.0
        
        return mean(weekly_distances.values())
    
    def _calculate_trend(self, runs_data: List[Dict], days_back: int) -> str:
        """Calculate trend by comparing recent vs older activity."""
        if len(runs_data) < 4:  # Need at least 4 runs to calculate trend
            return "insufficient_data"
        
        # Sort runs by date
        sorted_runs = sorted(runs_data, key=lambda x: x["date"])
        
        # Split into recent and older halves
        mid_point = len(sorted_runs) // 2
        older_runs = sorted_runs[:mid_point]
        recent_runs = sorted_runs[mid_point:]
        
        # Calculate weekly distance for each period
        older_weekly = self._calculate_weekly_distance(older_runs)
        recent_weekly = self._calculate_weekly_distance(recent_runs)
        
        if recent_weekly > older_weekly * 1.1:
            return "increasing"
        elif recent_weekly < older_weekly * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_runs_per_week(self, runs_data: List[Dict]) -> float:
        """Calculate average runs per week."""
        if not runs_data:
            return 0.0
        
        # Group runs by week
        weekly_counts = {}
        for run in runs_data:
            try:
                run_date = datetime.strptime(run["date"], "%Y-%m-%d")
                week_key = run_date.strftime("%Y-W%U")
                
                if week_key not in weekly_counts:
                    weekly_counts[week_key] = 0
                
                weekly_counts[week_key] += 1
            except ValueError:
                logger.warning(f"Invalid date format: {run['date']}")
                continue
        
        if not weekly_counts:
            return 0.0
        
        return mean(weekly_counts.values())
    
    def _calculate_consistency_score(self, runs_data: List[Dict]) -> float:
        """Calculate consistency score based on run frequency and pace variability."""
        if len(runs_data) < 3:
            return 0.0
        
        # Calculate pace consistency
        paces = []
        for run in runs_data:
            if run["average_speed_m_s"] > 0:
                pace_min_per_km = (1000 / run["average_speed_m_s"]) / 60
                paces.append(pace_min_per_km)
        
        if not paces:
            return 0.0
        
        # Lower coefficient of variation = more consistent
        mean_pace = mean(paces)
        pace_std = (sum((p - mean_pace) ** 2 for p in paces) / len(paces)) ** 0.5
        pace_cv = pace_std / mean_pace if mean_pace > 0 else 1.0
        
        # Calculate frequency consistency
        runs_per_week = self._calculate_runs_per_week(runs_data)
        frequency_score = min(runs_per_week / 4.0, 1.0)  # Normalize to 0-1, 4 runs/week = perfect
        
        # Combine scores (pace consistency + frequency consistency)
        consistency_score = max(0.0, 1.0 - pace_cv) * 0.6 + frequency_score * 0.4
        
        return round(consistency_score, 2)
    
    def _get_default_summary(self) -> Dict[str, Any]:
        """Return default summary for users with no recent activity."""
        return {
            "total_runs": 0,
            "total_distance_km": 0.0,
            "total_duration_hours": 0.0,
            "weekly_distance_km": 0.0,
            "longest_run_km": 0.0,
            "avg_pace_min_per_km": None,
            "median_pace_min_per_km": None,
            "runs_per_week": 0.0,
            "avg_hr": None,
            "avg_cadence": None,
            "trend": "no_data",
            "consistency_score": 0.0,
            "days_back": 30
        }


# Global instance
activity_summarizer = ActivitySummarizer()
