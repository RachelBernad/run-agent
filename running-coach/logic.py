"""Business logic for the running coach application."""

import logging
from typing import List, Dict, Optional

from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from settings import (
    LOG_PROGRAM_GENERATED,
    LOG_ERROR_OCCURRED,
    MSG_SERVER_ERROR
)
from schemas import ProgramRequest, ProgramResponse, PlanAnalysisRequest, PlanAnalysisResponse
from llm_service import RunningCoachLLM
# Removed GarminMCPClient import - using MCP client from app.state instead

logger = logging.getLogger(__name__)


class RunningCoachLogic:
    """Business logic for running program generation."""
    
    def __init__(self):
        """Initialize the running coach logic."""
        self.programs_memory: Dict[str, ProgramResponse] = {}
        self.llm_service = RunningCoachLLM()
        # MCP client will be accessed from app.state
        logger.info("RunningCoachLogic initialized")
    
    async def generate_program(self, request: ProgramRequest, mcp_client=None) -> ProgramResponse:
        try:
            logger.info(f"Generating LLM-based program for {request.goal_km}km in {request.time_weeks} weeks")
            
            # Get recent runs from Garmin for context
            recent_runs = await self._get_recent_runs_summary(mcp_client=mcp_client)
            
            # Use LLM service with run context
            program = await self.llm_service.generate_program_with_context(request, recent_runs)
            
            # Save to memory
            self._save_program(program)
            
            logger.info(f"{LOG_PROGRAM_GENERATED} - ID: {program.program_id}")
            return program
            
        except Exception as e:
            logger.error(f"{LOG_ERROR_OCCURRED}: {str(e)}")
            raise Exception(f"{MSG_SERVER_ERROR}: {str(e)}")
    
    
    def _save_program(self, program: ProgramResponse) -> None:
        """Save program to memory."""
        self.programs_memory[program.program_id] = program
        logger.info(f"Program saved to memory - ID: {program.program_id}")
    
    def get_program_history(self) -> List[ProgramResponse]:
        """
        Get all previously generated programs.
        
        Returns:
            List of all programs in memory
        """
        logger.info("Retrieving program history")
        return list(self.programs_memory.values())
    
    def get_program_by_id(self, program_id: str) -> ProgramResponse:
        if program_id not in self.programs_memory:
            logger.warning(f"Program not found - ID: {program_id}")
            raise KeyError(f"Program not found: {program_id}")
        
        logger.info(f"Program retrieved - ID: {program_id}")
        return self.programs_memory[program_id]
    
    async def analyze_plan(self, request: PlanAnalysisRequest, mcp_client=None) -> PlanAnalysisResponse:
        try:
            logger.info(f"Analyzing plan progress for program {request.program_id}")
            
            recent_runs = await self._get_recent_runs_summary(request.days_back, mcp_client)
            
            current_plan = self._get_plan_by_id(request.program_id)
            
            result = await self.llm_service.analyze_plan_with_data(recent_runs, current_plan, request.current_date)
            
            logger.info(f"Plan analysis completed - Status: {result.plan_status}")
            return result
            
        except Exception as e:
            logger.error(f"{LOG_ERROR_OCCURRED}: {str(e)}")
            raise Exception(f"Plan analysis failed: {str(e)}")
    
    async def _get_recent_runs_summary(self, days_back: int = 30, mcp_client=None) -> List:
        try:
            from settings import settings
            from schemas import RunData
            
            # Check if MCP client is provided
            if not mcp_client:
                logger.warning("MCP client not available")
                return []
            
            # Call MCP tool directly
            async with mcp_client:
                result = await mcp_client.call_tool(
                    "get_weekly_running_summaries",
                    arguments={
                        "username": settings.garmin_username,
                        "password": settings.garmin_password,
                        "days_back": days_back,
                        "save_raw_to_file": False,
                        "save_summary_to_file": False
                    }
                )
            
            # Extract the content from the MCP response
            raw_runs = [content.data for content in result.content] if isinstance(result, ToolResult) else result
            return raw_runs
            
        except Exception as e:
            logger.warning(f"Failed to fetch runs from Garmin: {e}")
            return []
    
    def _get_plan_by_id(self, program_id: str) -> Optional[Dict]:
        """Get a specific program from memory by ID."""
        if program_id not in self.programs_memory:
            return None
        
        program = self.programs_memory[program_id]
        
        return {
            "weeks": program.time_weeks,
            "target_distances": [week.total_distance_km for week in program.weekly_plans],
            "workouts_per_day": [week.runs_per_week for week in program.weekly_plans]
        }
    
    def clear_memory(self) -> None:
        count = len(self.programs_memory)
        self.programs_memory.clear()
        logger.info(f"Memory cleared - {count} programs removed")


running_coach = RunningCoachLogic()
