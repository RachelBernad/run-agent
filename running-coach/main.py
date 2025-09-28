"""FastAPI application for the running coach."""

import logging
import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.ui_nicegui import mount_ui

# Initialize LangSmith tracing
from langsmith import Client

from settings import (
    API_TAGS_METADATA,
    LOG_REQUEST_RECEIVED,
    LOG_PROGRAM_SAVED,
    LOG_HISTORY_REQUESTED,
    LOG_ERROR_OCCURRED,
    MSG_SERVER_ERROR,
    MSG_PROGRAM_NOT_FOUND
)
from settings import settings
from logic import running_coach
from schemas import (
    ProgramRequest,
    ProgramResponse,
    HistoryResponse,
    PlanAnalysisRequest,
    PlanAnalysisResponse
)
from llm_service import RunningCoachLLM

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


# Create FastAPI app
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    openapi_tags=API_TAGS_METADATA,
    debug=settings.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers
)

mount_ui(app)

llm_service = RunningCoachLLM()

langsmith_client = Client(api_key=settings.langchain_api_key)
@app.on_event("startup")
async def startup_connect_mcp() -> None:
    """Connect to MCP server on startup and cache tool definitions."""
    # Initialize LangSmith tracing if API key is provided
    mcp_url = os.getenv("MCP_URL", "http://127.0.0.1:3000/mcp").strip()
    try:
        from fastmcp.client import Client
        from fastmcp.client.transports import StreamableHttpTransport
        transport = StreamableHttpTransport(url=mcp_url)
        client = Client(transport)
        # Use setattr to avoid linter warnings about app.state
        setattr(app.state, 'mcp_client', client)
        setattr(app.state, 'mcp_tools', [])
        # establish connection and prefetch tools
        async with client:
            try:
                mcp_tools = await client.list_tools()
                # Convert MCP tools to OpenAI format
                tools_list = []
                for tool in mcp_tools:
                    if hasattr(tool, 'name') and hasattr(tool, 'description'):
                        openai_tool = {
                            "type": "function",
                            "function": {
                                "name": tool.name,
                                "description": tool.description,
                                "parameters": getattr(tool, 'inputSchema', {})
                            }
                        }
                        tools_list.append(openai_tool)
                setattr(app.state, 'mcp_tools', tools_list)
                logger.debug(f"MCP tool list: {tools_list}")
            except Exception as e:
                logger.warning(f"Could not fetch MCP tools during startup: {e}")
                setattr(app.state, 'mcp_tools', [])
    except Exception as e:
        # leave state unset if connection fails; background task will fallback
        setattr(app.state, 'mcp_client', None)
        setattr(app.state, 'mcp_tools', [])
        logger.error("failed to connect to MCP server", e)


@app.on_event("shutdown")
async def shutdown_disconnect_mcp() -> None:
    client = getattr(app.state, "mcp_client", None)
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "message": settings.app_title,
        "version": settings.app_version,
        "description": settings.app_description,
        "endpoints": {
            "create_program": "/programs",
            "get_history": "/history",
            "get_program": "/programs/{program_id}",
            "analyze_plan": "/analyze-plan",
            "docs": "/docs"
        }
    }


@app.post(
    "/programs",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["programs"],
    summary="Create a new running program",
    description="Generate a personalized running program based on goal distance and time frame"
)
async def create_program(request: ProgramRequest, use_optimized: bool = True) -> ProgramResponse:
    """
    Create a new running program.
    
    Args:
        request: Program request with goal distance and time frame
        
    Returns:
        Generated running program
        
    Raises:
        HTTPException: If program generation fails
    """
    try:
        logger.info(LOG_REQUEST_RECEIVED, extra={"goal_km": request.goal_km, "time": request.time_weeks})
        
        # Generate program using business logic
        mcp_client = getattr(app.state, 'mcp_client', None)
        program = await running_coach.generate_program(request, mcp_client, use_optimized)
        
        logger.info(LOG_PROGRAM_SAVED, extra={"program_id": program.program_id})
        
        return program
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"{LOG_ERROR_OCCURRED}: {str(e)}", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MSG_SERVER_ERROR
        )


@app.get(
    "/programs/{program_id}",
    response_model=ProgramResponse,
    tags=["programs"],
    summary="Get a specific program",
    description="Retrieve a previously generated program by its ID"
)
async def get_program(program_id: str) -> ProgramResponse:
    """
    Get a specific program by ID.
    
    Args:
        program_id: Unique program identifier
        
    Returns:
        Program data
        
    Raises:
        HTTPException: If program not found
    """
    try:
        logger.info(f"Retrieving program - ID: {program_id}")
        
        program = running_coach.get_program_by_id(program_id)
        
        return program
        
    except KeyError as e:
        logger.warning(f"Program not found - ID: {program_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_PROGRAM_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"{LOG_ERROR_OCCURRED}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MSG_SERVER_ERROR
        )


@app.get(
    "/history",
    response_model=HistoryResponse,
    tags=["history"],
    summary="Get program history",
    description="Retrieve all previously generated programs"
)
async def get_history() -> HistoryResponse:
    """
    Get all previously generated programs.
    
    Returns:
        List of all programs with metadata
        
    Raises:
        HTTPException: If history retrieval fails
    """
    try:
        logger.info(LOG_HISTORY_REQUESTED)
        
        programs = running_coach.get_program_history()
        
        response = HistoryResponse(
            total_programs=len(programs),
            programs=programs
        )
        
        logger.info(f"History retrieved - {len(programs)} programs found")
        
        return response
        
    except Exception as e:
        logger.error(f"{LOG_ERROR_OCCURRED}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MSG_SERVER_ERROR
        )


@app.delete(
    "/programs/{program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["programs"],
    summary="Delete a program",
    description="Remove a program from memory"
)
async def delete_program(program_id: str):
    """
    Delete a program by ID.
    
    Args:
        program_id: Unique program identifier
        
    Raises:
        HTTPException: If program not found
    """
    try:
        logger.info(f"Deleting program - ID: {program_id}")
        
        # Check if program exists
        running_coach.get_program_by_id(program_id)
        
        # Remove from memory
        del running_coach.programs_memory[program_id]
        
        logger.info(f"Program deleted - ID: {program_id}")
        
    except KeyError as e:
        logger.warning(f"Program not found for deletion - ID: {program_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=MSG_PROGRAM_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"{LOG_ERROR_OCCURRED}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MSG_SERVER_ERROR
        )


@app.post(
    "/analyze-plan",
    response_model=PlanAnalysisResponse,
    tags=["analysis"],
    summary="Analyze running plan progress",
    description="Evaluate runner's progress against their current plan"
)
async def analyze_plan(request: PlanAnalysisRequest) -> PlanAnalysisResponse:
    """Analyze running plan progress."""
    try:
        logger.info(f"Analyzing plan - Program ID: {request.program_id}, Days back: {request.days_back}")
        
        mcp_client = getattr(app.state, 'mcp_client', None)
        result = await running_coach.analyze_plan(request, mcp_client)
        
        logger.info(f"Plan analysis completed - Status: {result.plan_status}")
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error in plan analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Plan analysis error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Plan analysis failed"
        )


@app.post(
    "/programs/fast",
    response_model=ProgramResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["programs"],
    summary="Create a running program (fast mode)",
    description="Generate a personalized running program using optimized template-based approach"
)
async def create_program_fast(request: ProgramRequest) -> ProgramResponse:
    """Create a new running program using fast template-based generation."""
    try:
        logger.info(f"Fast program generation requested - {request.goal_km}km in {request.time_weeks} weeks")
        
        mcp_client = getattr(app.state, 'mcp_client', None)
        recent_runs = await running_coach._get_recent_runs_summary(mcp_client=mcp_client)
        
        program = await running_coach.optimized_llm_service.generate_program_fast(request, recent_runs)
        
        logger.info(f"Fast program generated - ID: {program.program_id}")
        return program
        
    except Exception as e:
        logger.error(f"Fast program generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fast program generation failed"
        )


@app.get(
    "/cache/stats",
    response_model=dict,
    tags=["cache"],
    summary="Get cache statistics",
    description="Retrieve cache statistics and performance metrics"
)
async def get_cache_stats():
    """Get cache statistics."""
    try:
        stats = running_coach.optimized_llm_service.get_cache_stats()
        return {
            "cache_stats": stats,
            "memory_programs": len(running_coach.programs_memory)
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@app.delete(
    "/cache",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["cache"],
    summary="Clear cache",
    description="Clear all cached programs"
)
async def clear_cache():
    """Clear all cached programs."""
    try:
        running_coach.optimized_llm_service.clear_cache()
        running_coach.clear_memory()
        logger.info("Cache cleared successfully")
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@app.get(
    "/health",
    response_model=dict,
    tags=["health"],
    summary="Health check",
    description="Check if the API is running"
)
async def health_check():
    """Health check endpoint."""
    cache_stats = running_coach.optimized_llm_service.get_cache_stats()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "programs_in_memory": len(running_coach.programs_memory),
        "cache_stats": cache_stats
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower()
    )
