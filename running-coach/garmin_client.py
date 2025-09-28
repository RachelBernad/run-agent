"""Garmin MCP client for fetching running data."""

import asyncio
import json
import logging
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class GarminMCPClient:
    """Client for interacting with Garmin MCP server."""
    
    def __init__(self, mcp_server_url: str = "http://127.0.0.1:3000"):
        self.mcp_server_url = mcp_server_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def call_mcp_tool(self, client: httpx.AsyncClient, tool_name: str, params: dict):
        """Calls an MCP tool via an existing HTTP client."""
        try:
            # Use the correct MCP JSON-RPC format
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": params
                }
            }
            
            response = await client.post(
                f"{self.mcp_server_url}/mcp",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Request error", exc_info=True)
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error", exc_info=e)
            return None

    async def get_runs_from_mcp(self, username: str, password: str, days_back: int = 30):
        """Calls the running summaries tool using a managed client."""
        async with httpx.AsyncClient() as client:
            params = {
                "username": username,
                "password": password,
                "days_back": days_back,
                "save_raw_to_file": False,
                "save_summary_to_file": False
            }

            result = await self.call_mcp_tool(client, "get_recent_running_summaries", params)
            if result and "result" in result:
                # Extract the content from the MCP response
                return result["result"].get("content", [])
            else:
                logger.warning("Failed to get runs from MCP or no data returned.")
                return []
