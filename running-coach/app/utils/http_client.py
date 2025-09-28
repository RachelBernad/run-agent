"""HTTP client with retries and exponential backoff for API calls."""

import asyncio
from typing import Any, Dict, Optional

import httpx

from app.constants import (
    BASE_URL,
    API_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    BACKOFF_FACTOR
)
from app.utils.logger import logger


class APIClient:
    """HTTP client with retry logic and error handling."""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.timeout = API_TIMEOUT
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        retries: int = MAX_RETRIES
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries + 1):
            try:
                logger.info(f"Making {method} request", endpoint=endpoint, attempt=attempt + 1)
                
                if method.upper() == "GET":
                    response = await self.client.get(url)
                elif method.upper() == "POST":
                    response = await self.client.post(url, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                logger.info(f"Request successful", endpoint=endpoint, status_code=response.status_code)
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error", endpoint=endpoint, status_code=e.response.status_code, error=str(e))
                if e.response.status_code < 500 or attempt == retries:
                    # Don't retry client errors or on final attempt
                    raise
                
            except httpx.TimeoutException as e:
                logger.error(f"Request timeout", endpoint=endpoint, error=str(e))
                if attempt == retries:
                    raise
                
            except Exception as e:
                logger.error(f"Request failed", endpoint=endpoint, error=str(e))
                if attempt == retries:
                    raise
            
            # Wait before retry with exponential backoff
            if attempt < retries:
                delay = RETRY_DELAY * (BACKOFF_FACTOR ** attempt)
                logger.info(f"Retrying in {delay}s", endpoint=endpoint, attempt=attempt + 1)
                await asyncio.sleep(delay)
        
        raise Exception("Max retries exceeded")
    
    async def create_program(self, goal_km: float, time_weeks: int) -> Dict[str, Any]:
        """Create a new running program."""
        data = {
            "goal_km": goal_km,
            "time_weeks": time_weeks
        }
        return await self._make_request("POST", "/programs", data=data)
    
    async def get_history(self) -> Dict[str, Any]:
        """Get program history."""
        return await self._make_request("GET", "/history")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        return await self._make_request("GET", "/health")


# Global client instance
api_client = APIClient()
