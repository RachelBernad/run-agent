import datetime
import json
import logging
from collections import defaultdict
from typing import List, Dict, Any

import numpy as np
from fastmcp import FastMCP
from garminconnect import Garmin

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mcp = FastMCP(name="Garmin Run Summarizer")


def _calculate_pace(avg_speed: float, distance_m: float, duration_sec: float) -> float:
    """Calculate pace in minutes per kilometer."""
    if avg_speed and avg_speed > 0:
        return (1000 / avg_speed) / 60
    elif distance_m and distance_m > 0 and duration_sec:
        return (duration_sec / (distance_m / 1000)) / 60
    return None


def _calculate_moving_ratio(moving_duration_sec: float, duration_sec: float) -> float:
    """Calculate moving time ratio."""
    if moving_duration_sec is not None and duration_sec:
        return moving_duration_sec / duration_sec
    return None


def _extract_splits(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and simplify split data."""
    splits = run.get("splitSummaries")
    if not splits:
        return []

    return [
        {
            "split_type": s.get("splitType"),
            "duration": s.get("duration"),
            "distance": s.get("distance"),
            "average_speed": s.get("averageSpeed"),
            "max_speed": s.get("maxSpeed"),
        }
        for s in splits
    ]


def summarize_run(run: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize a single run activity."""
    summary = {
        "activity_id": run.get("activityId"),
        "start_time_local": run.get("startTimeLocal"),
        "distance_m": run.get("distance"),
        "duration_sec": run.get("duration"),
        "moving_duration_sec": run.get("movingDuration"),
        "average_speed_m_s": run.get("averageSpeed"),
        "max_speed_m_s": run.get("maxSpeed"),
        "average_hr": run.get("averageHeartRate"),
        "max_hr": run.get("maxHeartRate"),
        "avg_cadence": run.get("averageRunningCadenceInStepsPerMinute"),
        "max_cadence": run.get("maxRunningCadenceInStepsPerMinute"),
        "steps": run.get("steps"),
        "calories": run.get("summarizedActivityLevel"),
        "water_estimated_ml": run.get("waterEstimated"),
    }

    # Calculate derived fields
    summary["pace_min_per_km"] = _calculate_pace(
        summary["average_speed_m_s"], summary["distance_m"], summary["duration_sec"]
    )
    summary["moving_ratio"] = _calculate_moving_ratio(
        summary["moving_duration_sec"], summary["duration_sec"]
    )
    summary["splits"] = _extract_splits(run)

    return summary


def _authenticate_garmin(username: str, password: str) -> Garmin:
    """Authenticate with Garmin Connect."""
    try:
        client = Garmin(username, password)
        client.login()
        logger.info("Garmin login successful")
        return client
    except Exception as e:
        logger.error(f"Garmin login failed: {e}")
        raise RuntimeError(f"Garmin login failed: {e}")


def _get_date_range(days_back: int) -> tuple[datetime.date, datetime.date]:
    """Get start and end dates for the query."""
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days_back)
    logger.info(f"Fetching data from {start_date} to {end_date}")
    return start_date, end_date


def _parse_activity_date(activity: Dict[str, Any]) -> datetime.date:
    """Parse activity start date from ISO string."""
    start_time_str = activity.get('startTimeLocal', '')
    if not start_time_str:
        return None

    try:
        clean_time = start_time_str.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(clean_time).date()
    except ValueError:
        logger.warning(f"Could not parse date for activity {activity.get('activityId')}: {start_time_str}")
        return None


def _is_running_activity(activity: Dict[str, Any]) -> bool:
    """Check if activity is a running activity."""
    activity_type = activity.get('activityType', {}).get('typeKey', '').lower()
    return 'run' in activity_type


def _fetch_activities(client: Garmin, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
    """Fetch all activities and filter for running activities in date range."""
    running_activities = []
    start_activity = 0
    activity_limit = 100

    while True:
        try:
            logger.info(f"Fetching activities batch (start: {start_activity})")
            activities_batch = client.get_activities(start_activity, activity_limit)

            if not activities_batch:
                logger.info("No more activities found")
                break

            for activity in activities_batch:
                activity_date = _parse_activity_date(activity)
                if activity_date and start_date <= activity_date <= end_date:
                    if _is_running_activity(activity):
                        running_activities.append(activity)
                        logger.info(f"Found running activity: {activity.get('activityName', 'N/A')} on {activity_date}")

            start_activity += activity_limit

        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            break

    logger.info(f"Found {len(running_activities)} running activities in date range")
    return running_activities


def week_key(date_str: str) -> tuple[int, int]:
    """Get week key (year, week number) from date string."""
    dt = datetime.datetime.fromisoformat(date_str)
    return dt.isocalendar()[0], dt.isocalendar()[1]  # (year, week number)


def aggregate_weekly(runs: List[Dict[str, Any]]) -> Dict[tuple[int, int], Dict[str, Any]]:
    """Aggregate runs by week and calculate weekly statistics."""
    weeks = defaultdict(list)
    for run in runs:
        key = week_key(run["start_time_local"])
        weeks[key].append(run)

    weekly_summary = {}
    for key, week_runs in weeks.items():
        distances = [r["distance_m"] / 1000 for r in week_runs if r["distance_m"]]
        paces = [r["pace_min_per_km"] for r in week_runs if r["pace_min_per_km"]]
        avg_hrs = [r["average_hr"] for r in week_runs if r["average_hr"]]
        cadences = [r["avg_cadence"] for r in week_runs if r["avg_cadence"]]
        moving_ratios = [r["moving_ratio"] for r in week_runs if r["moving_ratio"]]

        # Helper function to safely get max value
        def safe_max(values):
            valid_values = [v for v in values if v is not None]
            return max(valid_values) if valid_values else None

        weekly_summary[key] = {
            "total_distance_km": sum(distances),
            "total_duration_h": sum(r["duration_sec"] for r in week_runs if r["duration_sec"]) / 3600,
            "total_moving_h": sum(r["moving_duration_sec"] for r in week_runs if r["moving_duration_sec"]) / 3600,
            "total_steps": sum(r["steps"] for r in week_runs if r["steps"]),
            "total_calories": sum(r["calories"] for r in week_runs if r["calories"]),
            "avg_pace_min_per_km": np.mean(paces) if paces else None,
            "pace_cv": np.std(paces) / np.mean(paces) if paces and np.mean(paces) else 0,
            "max_speed_m_s": safe_max([r["max_speed_m_s"] for r in week_runs]),
            "average_hr": np.mean(avg_hrs) if avg_hrs else None,
            "hr_cv": np.std(avg_hrs) / np.mean(avg_hrs) if avg_hrs and np.mean(avg_hrs) else 0,
            "max_hr": safe_max([r["max_hr"] for r in week_runs]),
            "average_cadence": np.mean(cadences) if cadences else None,
            "cadence_cv": np.std(cadences) / np.mean(cadences) if cadences and np.mean(cadences) else 0,
            "max_cadence": safe_max([r["max_cadence"] for r in week_runs]),
            "avg_moving_ratio": np.mean(moving_ratios) if moving_ratios else None,
            "run_count": len(week_runs)
        }

    return weekly_summary


def _save_json(data: Any, filename: str) -> None:
    """Save data to JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, default=str)
        logger.info(f"Data saved to '{filename}'")
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")


@mcp.tool()
async def get_recent_running_summaries(
        username: str,
        password: str,
        days_back: int = 30,
        save_raw_to_file: bool = True,
        save_summary_to_file: bool = True
) -> List[Dict[str, Any]]:
    """
    Fetch recent running activities from Garmin Connect and return summaries.

    Args:
        username: Garmin Connect username
        password: Garmin Connect password
        days_back: Number of days back to look for runs (default 30)
        save_raw_to_file: Save raw activity data to 'garmin_raw_activities.json'
        save_summary_to_file: Save summarized data to 'garmin_summarized_runs.json'

    Returns:
        List of summarized run data dictionaries
    """
    logger.info(f"Fetching runs from Garmin Connect for the last {days_back} days")

    # Authenticate and get date range
    client = _authenticate_garmin(username, password)
    start_date, end_date = _get_date_range(days_back)

    # Fetch running activities
    running_activities = _fetch_activities(client, start_date, end_date)

    # Save raw data if requested
    if save_raw_to_file and running_activities:
        _save_json(running_activities, "garmin_raw_activities.json")

    # Summarize activities
    logger.info("Summarizing running activities")
    summarized_runs = [summarize_run(run) for run in running_activities]

    # Save summary if requested
    if save_summary_to_file and summarized_runs:
        _save_json(summarized_runs, "garmin_summarized_runs.json")

    logger.info(f"Returning {len(summarized_runs)} summarized runs")
    return summarized_runs


@mcp.tool()
async def get_weekly_running_summaries(
        username: str,
        password: str,
        days_back: int = 30,
        save_raw_to_file: bool = True,
        save_summary_to_file: bool = True
) -> Dict[str, Any]:
    """
    Fetch recent running activities from Garmin Connect and return weekly summaries.

    Args:
        username: Garmin Connect username
        password: Garmin Connect password
        days_back: Number of days back to look for runs (default 30)
        save_raw_to_file: Save raw activity data to 'garmin_raw_activities.json'
        save_summary_to_file: Save weekly summary data to 'garmin_weekly_summaries.json'

    Returns:
        Dictionary with weekly summaries keyed by (year, week_number)
    """
    logger.info(f"Fetching runs from Garmin Connect for the last {days_back} days")

    # Authenticate and get date range
    client = _authenticate_garmin(username, password)
    start_date, end_date = _get_date_range(days_back)

    # Fetch running activities
    running_activities = _fetch_activities(client, start_date, end_date)

    # Save raw data if requested
    if save_raw_to_file and running_activities:
        _save_json(running_activities, "garmin_raw_activities.json")

    # Summarize activities
    logger.info("Summarizing running activities")
    summarized_runs = [summarize_run(run) for run in running_activities]

    # Create weekly summaries
    logger.info("Creating weekly summaries")
    weekly_summaries = aggregate_weekly(summarized_runs)

    # Convert tuple keys to string keys for JSON serialization
    weekly_summaries_str_keys = {
        f"{year}_week_{week}": summary
        for (year, week), summary in weekly_summaries.items()
    }

    # Save weekly summary if requested
    if save_summary_to_file and weekly_summaries_str_keys:
        _save_json(weekly_summaries_str_keys, "garmin_weekly_summaries.json")

    logger.info(f"Returning {len(weekly_summaries_str_keys)} weekly summaries")
    return weekly_summaries_str_keys


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="127.0.0.1", port=3000, path="/mcp")
