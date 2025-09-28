"""Caching system for running programs."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

from schemas import ProgramResponse

logger = logging.getLogger(__name__)


class ProgramCache:
    """Caching system for running programs with memory and file system support."""
    
    def __init__(self, cache_dir: str = "cache", max_memory_items: int = 50):
        """
        Initialize the cache system.
        
        Args:
            cache_dir: Directory for file-based caching
            max_memory_items: Maximum number of items to keep in memory
        """
        self.memory_cache: Dict[str, ProgramResponse] = {}
        self.cache_dir = Path(cache_dir)
        self.max_memory_items = max_memory_items
        
        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"Program cache initialized - cache_dir: {cache_dir}, max_memory: {max_memory_items}")
    
    def get_program(self, program_id: str) -> Optional[ProgramResponse]:
        """
        Get a program from cache.
        
        Args:
            program_id: Unique program identifier
            
        Returns:
            ProgramResponse if found, None otherwise
        """
        # Try memory cache first
        if program_id in self.memory_cache:
            logger.debug(f"Program {program_id} found in memory cache")
            return self.memory_cache[program_id]
        
        # Try file cache
        program = self._load_from_file(program_id)
        if program:
            # Add to memory cache for faster access
            self._add_to_memory_cache(program_id, program)
            logger.debug(f"Program {program_id} loaded from file cache")
            return program
        
        logger.debug(f"Program {program_id} not found in cache")
        return None
    
    def cache_program(self, program: ProgramResponse) -> None:
        """
        Cache a program.
        
        Args:
            program: ProgramResponse to cache
        """
        program_id = program.program_id
        
        # Add to memory cache
        self._add_to_memory_cache(program_id, program)
        
        # Save to file cache
        self._save_to_file(program)
        
        logger.info(f"Program {program_id} cached successfully")
    
    def invalidate_program(self, program_id: str) -> bool:
        """
        Remove a program from cache.
        
        Args:
            program_id: Unique program identifier
            
        Returns:
            True if program was found and removed, False otherwise
        """
        removed = False
        
        # Remove from memory cache
        if program_id in self.memory_cache:
            del self.memory_cache[program_id]
            removed = True
        
        # Remove from file cache
        cache_file = self.cache_dir / f"{program_id}.json"
        if cache_file.exists():
            cache_file.unlink()
            removed = True
        
        if removed:
            logger.info(f"Program {program_id} invalidated from cache")
        
        return removed
    
    def get_similar_program(self, goal_km: float, weeks: int, tolerance: float = 0.1) -> Optional[ProgramResponse]:
        """
        Find a cached program with similar parameters.
        
        Args:
            goal_km: Target distance
            weeks: Number of weeks
            tolerance: Tolerance for similarity (0.1 = 10%)
            
        Returns:
            Similar program if found, None otherwise
        """
        for program in self.memory_cache.values():
            goal_diff = abs(program.goal_km - goal_km) / goal_km
            weeks_diff = abs(program.time_weeks - weeks)
            
            if goal_diff <= tolerance and weeks_diff <= 1:
                logger.info(f"Found similar program {program.program_id} for {goal_km}km/{weeks}w")
                return program
        
        # Check file cache if memory cache doesn't have a match
        return self._find_similar_in_file_cache(goal_km, weeks, tolerance)
    
    def clear_cache(self) -> None:
        """Clear all cached programs."""
        # Clear memory cache
        memory_count = len(self.memory_cache)
        self.memory_cache.clear()
        
        # Clear file cache
        file_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
            file_count += 1
        
        logger.info(f"Cache cleared - {memory_count} memory items, {file_count} file items")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        file_count = len(list(self.cache_dir.glob("*.json")))
        
        return {
            "memory_items": len(self.memory_cache),
            "file_items": file_count,
            "total_items": len(self.memory_cache) + file_count,
            "max_memory_items": self.max_memory_items,
            "cache_dir": str(self.cache_dir)
        }
    
    def _add_to_memory_cache(self, program_id: str, program: ProgramResponse) -> None:
        """Add program to memory cache with LRU eviction."""
        # If at capacity, remove oldest item
        if len(self.memory_cache) >= self.max_memory_items:
            oldest_id = min(self.memory_cache.keys(), 
                          key=lambda k: self.memory_cache[k].created_at)
            del self.memory_cache[oldest_id]
        
        self.memory_cache[program_id] = program
    
    def _save_to_file(self, program: ProgramResponse) -> None:
        """Save program to file cache."""
        cache_file = self.cache_dir / f"{program.program_id}.json"
        
        try:
            # Convert to dict and add metadata
            program_data = {
                "program": program.model_dump(),
                "cached_at": datetime.now().isoformat(),
                "cache_version": "1.0"
            }
            
            with open(cache_file, 'w') as f:
                json.dump(program_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save program {program.program_id} to file cache: {e}")
    
    def _load_from_file(self, program_id: str) -> Optional[ProgramResponse]:
        """Load program from file cache."""
        cache_file = self.cache_dir / f"{program_id}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate cache version and age
            cache_version = cache_data.get("cache_version", "1.0")
            cached_at = cache_data.get("cached_at")
            
            if cached_at:
                cache_time = datetime.fromisoformat(cached_at)
                # Remove files older than 30 days
                if datetime.now() - cache_time > timedelta(days=30):
                    cache_file.unlink()
                    return None
            
            # Load program data
            program_data = cache_data["program"]
            return ProgramResponse(**program_data)
            
        except Exception as e:
            logger.error(f"Failed to load program {program_id} from file cache: {e}")
            # Remove corrupted cache file
            if cache_file.exists():
                cache_file.unlink()
            return None
    
    def _find_similar_in_file_cache(self, goal_km: float, weeks: int, tolerance: float) -> Optional[ProgramResponse]:
        """Find similar program in file cache."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                program_data = cache_data["program"]
                cached_goal = program_data["goal_km"]
                cached_weeks = program_data["time_weeks"]
                
                goal_diff = abs(cached_goal - goal_km) / goal_km
                weeks_diff = abs(cached_weeks - weeks)
                
                if goal_diff <= tolerance and weeks_diff <= 1:
                    program = ProgramResponse(**program_data)
                    # Add to memory cache for faster access
                    self._add_to_memory_cache(program.program_id, program)
                    return program
                    
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
                continue
        
        return None


# Global cache instance
program_cache = ProgramCache()
