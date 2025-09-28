"""JSON template generator for running programs."""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List

from schemas import WeekPlan, Recommendation


class ProgramTemplateGenerator:
    """Generates pre-structured JSON templates for running programs."""
    
    def generate_program_template(self, goal_km: float, weeks: int) -> Dict[str, Any]:
        """
        Generate a pre-structured JSON template for a running program.
        
        Args:
            goal_km: Target distance in kilometers
            weeks: Number of weeks for the program
            
        Returns:
            Dictionary with pre-generated program structure
        """
        program_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        # Generate weekly plan templates
        weekly_plans = []
        for week_num in range(1, weeks + 1):
            weekly_plan = {
                "week_number": week_num,
                "total_distance_km": None,
                "runs_per_week": 3,  # Default to 3 runs per week
                "long_run_km": None,
                "easy_runs_km": [None, None, None],  # 3 easy runs
                "notes": ""
            }
            weekly_plans.append(weekly_plan)
        
        # Generate recommendation templates
        recommendations = [
            {
                "category": "Training",
                "title": "",
                "description": "",
                "priority": "medium"
            },
            {
                "category": "Recovery",
                "title": "",
                "description": "",
                "priority": "medium"
            },
            {
                "category": "Nutrition",
                "title": "",
                "description": "",
                "priority": "medium"
            },
            {
                "category": "Mental",
                "title": "",
                "description": "",
                "priority": "medium"
            }
        ]
        
        template = {
            "program_id": program_id,
            "goal_km": goal_km,
            "time_weeks": weeks,
            "weekly_plans": weekly_plans,
            "recommendations": recommendations,
            "created_at": created_at
        }
        
        return template
    
    def create_week_plan_template(self, week_number: int, runs_per_week: int = 3) -> Dict[str, Any]:
        """Create a template for a single week plan."""
        easy_runs = [None] * (runs_per_week - 1)  # All runs except long run
        
        return {
            "week_number": week_number,
            "total_distance_km": None,
            "runs_per_week": runs_per_week,
            "long_run_km": None,
            "easy_runs_km": easy_runs,
            "notes": ""
        }
    
    def create_recommendation_template(self, category: str, priority: str = "medium") -> Dict[str, Any]:
        """Create a template for a single recommendation."""
        return {
            "category": category,
            "title": "",
            "description": "",
            "priority": priority
        }


# Global instance
template_generator = ProgramTemplateGenerator()
