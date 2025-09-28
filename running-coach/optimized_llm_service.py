"""Optimized LLM service using LangChain chains for step-wise program generation."""

import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from langchain.schema import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain.callbacks import LangChainTracer
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough

from optimized_prompts import (
    TEMPLATE_GENERATION_SYSTEM_PROMPT, TEMPLATE_GENERATION_USER_PROMPT,
    WEEKLY_PLANS_SYSTEM_PROMPT, WEEKLY_PLANS_USER_PROMPT,
    RECOMMENDATIONS_SYSTEM_PROMPT, RECOMMENDATIONS_USER_PROMPT,
    FAST_GENERATION_SYSTEM_PROMPT, FAST_GENERATION_USER_PROMPT
)
from schemas import ProgramRequest, ProgramResponse, WeekPlan, Recommendation, RunData
from settings import settings
from template_generator import template_generator
from activity_summarizer import activity_summarizer
from program_cache import program_cache

logger = logging.getLogger(__name__)


class OptimizedRunningCoachLLM:
    """Optimized LLM service with template-based generation and caching."""

    def __init__(self):
        self.llm = ChatOllama(
            model=settings.ollama_model,
            temperature=settings.llm_temperature
        )
        
        # Initialize LangChain chains
        self._initialize_chains()
        
        logger.info("Optimized LLM service initialized")

    def _initialize_chains(self):
        """Initialize LangChain chains for different generation steps."""
        
        # Template generation chain
        self.template_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["goal_km", "time_weeks"],
                template=TEMPLATE_GENERATION_USER_PROMPT
            ),
            verbose=True
        )
        
        # Weekly plans generation chain
        self.weekly_plans_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["template_json", "goal_km", "time_weeks", "recent_summary", "cached_program"],
                template=WEEKLY_PLANS_USER_PROMPT
            ),
            verbose=True
        )
        
        # Recommendations generation chain
        self.recommendations_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["program_json", "goal_km", "time_weeks", "recent_summary"],
                template=RECOMMENDATIONS_USER_PROMPT
            ),
            verbose=True
        )
        
        # Fast generation chain for cached programs
        self.fast_generation_chain = LLMChain(
            llm=self.llm,
            prompt=PromptTemplate(
                input_variables=["existing_program", "goal_km", "time_weeks", "recent_summary"],
                template=FAST_GENERATION_USER_PROMPT
            ),
            verbose=True
        )

    async def generate_program_optimized(
        self, 
        request: ProgramRequest, 
        recent_runs: List[RunData]
    ) -> ProgramResponse:
        """
        Generate a program using optimized template-based approach.
        
        Args:
            request: Program request parameters
            recent_runs: Recent running activity data
            
        Returns:
            Generated program response
        """
        logger.info("Starting optimized program generation", extra={
            "goal_km": request.goal_km,
            "time_weeks": request.time_weeks
        })
        
        # Step 1: Check cache for similar programs
        cached_program = program_cache.get_similar_program(
            request.goal_km, 
            request.time_weeks, 
            tolerance=0.15  # 15% tolerance
        )
        
        # Step 2: Summarize recent activity
        activity_summary = activity_summarizer.summarize_recent_activity(recent_runs)
        
        # Step 3: Generate or update program
        if cached_program and self._is_program_suitable(cached_program, request, activity_summary):
            logger.info(f"Using cached program {cached_program.program_id} with updates")
            program = await self._update_cached_program(cached_program, request, activity_summary)
        else:
            logger.info("Generating new program from template")
            program = await self._generate_new_program(request, activity_summary, cached_program)
        
        # Step 4: Cache the result
        program_cache.cache_program(program)
        
        logger.info("Program generation completed successfully", extra={
            "program_id": program.program_id,
            "used_cache": cached_program is not None
        })
        
        return program

    def _is_program_suitable(self, cached_program: ProgramResponse, request: ProgramRequest, activity_summary: Dict) -> bool:
        """Check if cached program is suitable for reuse."""
        goal_diff = abs(cached_program.goal_km - request.goal_km) / request.goal_km
        weeks_diff = abs(cached_program.time_weeks - request.time_weeks)
        
        # Suitable if goal within 15% and weeks within 1 week
        return goal_diff <= 0.15 and weeks_diff <= 1

    async def _generate_new_program(
        self, 
        request: ProgramRequest, 
        activity_summary: Dict, 
        cached_program: Optional[ProgramResponse]
    ) -> ProgramResponse:
        """Generate a new program using template-based approach."""
        
        # Step 1: Generate template
        template = template_generator.generate_program_template(request.goal_km, request.time_weeks)
        template_json = json.dumps(template)
        
        # Step 2: Fill weekly plans
        cached_json = json.dumps(cached_program.model_dump()) if cached_program else "null"
        
        weekly_plans_response = await self.weekly_plans_chain.arun(
            template_json=template_json,
            goal_km=request.goal_km,
            time_weeks=request.time_weeks,
            recent_summary=json.dumps(activity_summary),
            cached_program=cached_json
        )
        
        # Step 3: Fill recommendations
        recommendations_response = await self.recommendations_chain.arun(
            program_json=weekly_plans_response,
            goal_km=request.goal_km,
            time_weeks=request.time_weeks,
            recent_summary=json.dumps(activity_summary)
        )
        
        # Step 4: Parse and create response
        return self._parse_program_response(recommendations_response)

    async def _update_cached_program(
        self, 
        cached_program: ProgramResponse, 
        request: ProgramRequest, 
        activity_summary: Dict
    ) -> ProgramResponse:
        """Update a cached program with minimal changes."""
        
        existing_json = json.dumps(cached_program.model_dump())
        
        updated_response = await self.fast_generation_chain.arun(
            existing_program=existing_json,
            goal_km=request.goal_km,
            time_weeks=request.time_weeks,
            recent_summary=json.dumps(activity_summary)
        )
        
        return self._parse_program_response(updated_response)

    def _parse_program_response(self, response_text: str) -> ProgramResponse:
        """Parse LLM response into ProgramResponse object."""
        try:
            # Clean up JSON formatting
            if response_text.startswith("```json"):
                response_text = response_text[7:-3]
            elif response_text.startswith("```"):
                response_text = response_text[3:-3]
            
            result_data = json.loads(response_text.strip())
            
            # Create weekly plans
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
            
            # Create recommendations
            recommendations = [
                Recommendation(
                    category=rec["category"],
                    title=rec["title"],
                    description=rec["description"],
                    priority=rec["priority"]
                )
                for rec in result_data["recommendations"]
            ]
            
            # Create program response
            return ProgramResponse(
                program_id=result_data["program_id"],
                goal_km=result_data["goal_km"],
                time_weeks=result_data["time_weeks"],
                weekly_plans=weekly_plans,
                recommendations=recommendations,
                created_at=result_data["created_at"]
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse program response: {e}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"Failed to create program response: {e}")
            raise RuntimeError(f"Program creation failed: {e}")

    async def generate_program_fast(
        self, 
        request: ProgramRequest, 
        recent_runs: List[RunData]
    ) -> ProgramResponse:
        """
        Fast program generation using cached templates and minimal LLM calls.
        
        Args:
            request: Program request parameters
            recent_runs: Recent running activity data
            
        Returns:
            Generated program response
        """
        logger.info("Starting fast program generation")
        
        # Check cache first
        cached_program = program_cache.get_program(f"{request.goal_km}_{request.time_weeks}")
        if cached_program:
            logger.info("Returning cached program")
            return cached_program
        
        # Summarize activity quickly
        activity_summary = activity_summarizer.summarize_recent_activity(recent_runs)
        
        # Generate using template + single LLM call
        template = template_generator.generate_program_template(request.goal_km, request.time_weeks)
        
        # Use fast generation chain
        program = await self._generate_program_from_template(template, activity_summary)
        
        # Cache result
        program_cache.cache_program(program)
        
        return program

    async def _generate_program_from_template(
        self, 
        template: Dict[str, Any], 
        activity_summary: Dict
    ) -> ProgramResponse:
        """Generate program from template with single LLM call."""
        
        template_json = json.dumps(template)
        
        # Single comprehensive prompt for fast generation
        fast_prompt = f"""Fill this running program template based on the activity summary:

Template: {template_json}
Activity Summary: {json.dumps(activity_summary)}

Apply progressive overload, recovery weeks, and goal-specific adaptations.
Return complete JSON with all fields filled."""

        messages = [
            SystemMessage(content="You are an expert running coach. Fill the template efficiently."),
            HumanMessage(content=fast_prompt)
        ]
        
        try:
            tracer = LangChainTracer()
            response = self.llm.invoke(messages, config={"callbacks": [tracer]})
            result_json = response.content.strip()
            
            # Clean JSON
            if result_json.startswith("```json"):
                result_json = result_json[7:-3]
            elif result_json.startswith("```"):
                result_json = result_json[3:-3]
            
            result_data = json.loads(result_json)
            return self._parse_program_response(result_json)
            
        except Exception as e:
            logger.error(f"Fast generation failed: {e}")
            raise RuntimeError(f"Fast program generation failed: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get caching statistics."""
        return program_cache.get_cache_stats()

    def clear_cache(self) -> None:
        """Clear program cache."""
        program_cache.clear_cache()
        logger.info("Program cache cleared")


# Global instance
optimized_llm_service = OptimizedRunningCoachLLM()
