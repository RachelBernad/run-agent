"""Unified LLM service for running coach operations."""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from langchain.schema import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain.callbacks import LangChainTracer

from promts import SYSTEM_PROMPT, USER_PROMPT, PROGRAM_GENERATION_SYSTEM_PROMPT, PROGRAM_GENERATION_RUNNER_DATA
from schemas import (
    ProgramRequest, ProgramResponse, WeekPlan, Recommendation, PlanAnalysisResponse, ProgressData, RunData
)
from settings import settings

# Initialize logger
logger = logging.getLogger(__name__)


class RunningCoachLLM:

    def __init__(self):
        self.llm = ChatOllama(
            model=settings.ollama_model,
                temperature=settings.llm_temperature
        )

    def _invoke_llm(self, system_prompt: str, human_prompt: str) -> Dict[str, Any]:
        logger.info("Invoking LLM", extra={
                   "system_prompt_length": len(system_prompt), 
                   "human_prompt_length": len(human_prompt)
               })
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            # Add LangSmith tracing callback
            tracer = LangChainTracer()
            response = self.llm.invoke(messages, config={"callbacks": [tracer]})
            result_json = response.content.strip()
            
            logger.info("LLM response received", extra={
                       "response_length": len(result_json),
                       "response_preview": result_json[:200] + "..." if len(result_json) > 200 else result_json
                   })
            
            # Clean up JSON formatting
            if result_json.startswith("```json"):
                result_json = result_json[7:-3]
            elif result_json.startswith("```"):
                result_json = result_json[3:-3]
            
            parsed_result = json.loads(result_json)
            logger.info("LLM response parsed successfully")
            return parsed_result
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON", extra={
                        "error": str(e), 
                        "response_preview": result_json[:500] if 'result_json' in locals() else "No response"
                    })
            raise
        except Exception as e:
            logger.error("LLM invocation failed", extra={"error": str(e)})
            raise
    
    async def generate_program_with_context(self, request: ProgramRequest, recent_runs: List[RunData]) -> ProgramResponse:
        """Generate a personalized running program using LLM."""
        
        logger.info("Starting program generation", extra={
                   "goal_km": request.goal_km, 
                   "time_weeks": request.time_weeks,
               })
        
        system_prompt = PROGRAM_GENERATION_SYSTEM_PROMPT

        # Include recent run context if available
        run_context = "no runs "
        if recent_runs:
            run_context = recent_runs
            logger.info("Using recent run context")
        else:
            logger.info("No recent runs available, using default context")

        human_prompt = PROGRAM_GENERATION_RUNNER_DATA.format(goal_km=request.goal_km, time_weeks=request.time_weeks, run_context=run_context)

        try:
            result_data = self._invoke_llm(system_prompt, human_prompt)
            
            program_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()
            
            logger.info("Processing LLM response", extra={
                       "program_id": program_id,
                       "weekly_plans_count": len(result_data.get("weekly_plans", [])),
                       "recommendations_count": len(result_data.get("recommendations", []))
                   })
            
            weekly_plans = [
                WeekPlan(
                    week_number=week["week_number"],
                    total_distance_km=week["total_distance_km"],
                    runs_per_week=week["runs_per_week"],
                    long_run_km=week["long_run_km"],
                    easy_runs_km=week["easy_runs_km"],
                    notes=week["notes"]
                )
                for week in result_data["weekly_plans"]
            ]
            
            recommendations = [
                Recommendation(
                    category=rec["category"],
                    title=rec["title"],
                    description=rec["description"],
                    priority=rec["priority"]
                )
                for rec in result_data["recommendations"]
            ]
            
            program_response = ProgramResponse(
                program_id=program_id,
                goal_km=request.goal_km,
                time_weeks=request.time_weeks,
                weekly_plans=weekly_plans,
                recommendations=recommendations,
                created_at=created_at
            )
            
            logger.info("Program generation completed successfully", extra={
                       "program_id": program_id,
                       "total_weeks": len(weekly_plans),
                       "total_recommendations": len(recommendations)
                   })
            
            return program_response
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON during program generation", extra={
                        "error": str(e), 
                        "goal_km": request.goal_km, 
                        "time_weeks": request.time_weeks
                    })
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error("Program generation failed", extra={
                        "error": str(e), 
                        "goal_km": request.goal_km, 
                        "time_weeks": request.time_weeks
                    })
            raise RuntimeError(f"Program generation failed: {e}")
    
    async def analyze_plan_with_data(self, recent_runs: List[RunData], current_plan: Optional[Dict], current_date: str) -> PlanAnalysisResponse:
        """Analyze running plan progress."""
        
        logger.info("Starting plan analysis", extra={
                   "recent_runs_count": len(recent_runs),
                   "has_current_plan": current_plan is not None,
                   "current_date": current_date
               })
        
        runs_json = json.dumps([run.model_dump() for run in recent_runs])
        plan_json = json.dumps(current_plan) if current_plan else "null"
        
        logger.info("Prepared analysis data", extra={
                   "runs_json_length": len(runs_json),
                   "plan_json_length": len(plan_json)
               })
        
        human_prompt = USER_PROMPT.format(
            runs_json=runs_json,
            plan_json=plan_json,
            current_date=current_date
        )
        
        try:
            result_data = self._invoke_llm(SYSTEM_PROMPT, human_prompt)
            
            logger.info("Processing plan analysis response", extra={
                       "plan_status": result_data.get("plan_status"),
                       "recommendations_count": len(result_data.get("recommendations", [])),
                       "next_steps_count": len(result_data.get("next_steps", []))
                   })
            
            analysis_response = PlanAnalysisResponse(
                plan_status=result_data["plan_status"],
                summary=result_data["summary"],
                progress_data=ProgressData(**result_data["progress_data"]),
                recommendations=result_data["recommendations"],
                next_steps=result_data["next_steps"]
            )
            
            logger.info("Plan analysis completed successfully", extra={
                       "plan_status": analysis_response.plan_status,
                       "summary_length": len(analysis_response.summary)
                   })
            
            return analysis_response
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON during plan analysis", extra={
                        "error": str(e), 
                        "recent_runs_count": len(recent_runs),
                        "current_date": current_date
                    })
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error("Plan analysis failed", extra={
                        "error": str(e), 
                        "recent_runs_count": len(recent_runs),
                        "current_date": current_date
                    })
            raise RuntimeError(f"Analysis failed: {e}")
