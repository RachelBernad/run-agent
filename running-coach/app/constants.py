"""Constants for the NiceGUI frontend application."""

import os

# API Configuration
BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
API_TIMEOUT = 30

# Route Paths
ROUTE_PROGRAMS = "/programs"
ROUTE_HISTORY = "/history"
ROUTE_HEALTH = "/health"

# UI Strings
UI_TITLE = "Running Coach"
UI_SUBTITLE = "AI-Powered Training Program Generator"
UI_GOAL_LABEL = "Goal Distance (km)"
UI_TIME_LABEL = "Time Frame (weeks)"
UI_SUBMIT_BUTTON = "Generate Program"
UI_HISTORY_TAB = "History"
UI_PROGRAM_TAB = "New Program"
UI_LOADING_MESSAGE = "Generating your personalized program..."
UI_SUCCESS_MESSAGE = "Program generated successfully!"
UI_ERROR_MESSAGE = "Failed to generate program. Please try again."
UI_HISTORY_EMPTY = "No programs found. Create your first program!"
UI_HISTORY_ERROR = "Failed to load history. Please try again."

# Form Validation
MIN_GOAL_KM = 1.0
MAX_GOAL_KM = 1000.0
MIN_TIME_WEEKS = 1
MAX_TIME_WEEKS = 52
DEFAULT_GOAL_KM = 5.0
DEFAULT_TIME_WEEKS = 8

# HTTP Client Settings
MAX_RETRIES = 3
RETRY_DELAY = 1.0
BACKOFF_FACTOR = 2.0

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
