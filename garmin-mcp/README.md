# Garmin MCP Server

A Model Context Protocol (MCP) server for fetching and summarizing Garmin Connect running data.

## Features

- Fetch recent running activities from Garmin Connect
- Summarize run data with key metrics
- Calculate derived fields like pace and moving ratio
- Extract split data for detailed analysis
- Save raw and summarized data to JSON files

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables for Garmin Connect credentials:

**Option 1: Using environment variables**
```bash
export GARMIN_USERNAME='your_username'
export GARMIN_PASSWORD='your_password'
```

**Option 2: Using .env file (recommended)**
```bash
# Copy the example file
cp env.example .env

# Edit .env with your credentials
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password
```

## Usage

### Test the MCP Functionality

Run the test script to verify the MCP server works with your credentials:

```bash
python test_simple.py
```

This will test fetching running data for different time periods (7, 30, and 90 days).

### Run the MCP Server


The server will be available at `http://127.0.0.1:3000`.

### Direct Server Execution

You can also run the server directly:

```bash
python server.py
```

## Testing

The project includes comprehensive unit tests using pytest:

### Mock-based Tests (Recommended)

Run the mock-based tests that don't require API calls:

```bash
python -m pytest test_mcp_mock.py -v
```

**Test Coverage:**
- Date range calculations
- Pace and moving ratio calculations
- Split data extraction
- Run summarization with various data scenarios
- End-to-end workflow testing with mocked dependencies

### Direct Function Tests

Run tests that make actual API calls (may be rate limited):

```bash
python -m pytest test_mcp_simple.py -v
```

**Test Coverage:**
- Garmin authentication
- Activity fetching for different time periods
- Real treadmill run data validation
- Error handling for invalid credentials

### HTTP Server Tests

Run tests that test the MCP server via HTTP calls:

```bash
python -m pytest test_mcp_server.py -v
```

**Test Coverage:**
- Server health endpoints
- Tools endpoint functionality
- Tool call validation
- Error handling for invalid requests

### Test Results

All mock-based tests pass consistently:
```
============================== 11 passed in 0.30s ==============================
```

The direct function tests may fail due to Garmin API rate limiting (429 errors) but validate the core functionality when API calls succeed.

## MCP Tool: get_recent_running_summaries

### Parameters

- `username` (str): Garmin Connect username
- `password` (str): Garmin Connect password  
- `days_back` (int, optional): Number of days back to look for runs (default: 30)
- `save_raw_to_file` (bool, optional): Save raw activity data to file (default: True)
- `save_summary_to_file` (bool, optional): Save summarized data to file (default: True)

### Returns

List of summarized run data dictionaries containing:

- `activity_id`: Unique activity identifier
- `start_time_local`: Local start time of the run
- `distance_m`: Distance in meters
- `duration_sec`: Total duration in seconds
- `moving_duration_sec`: Moving time in seconds
- `average_speed_m_s`: Average speed in meters per second
- `max_speed_m_s`: Maximum speed in meters per second
- `average_hr`: Average heart rate
- `max_hr`: Maximum heart rate
- `avg_cadence`: Average running cadence
- `max_cadence`: Maximum running cadence
- `steps`: Total steps
- `calories`: Estimated calories burned
- `water_estimated_ml`: Estimated water loss
- `pace_min_per_km`: Calculated pace in minutes per kilometer
- `moving_ratio`: Ratio of moving time to total time
- `splits`: List of split data for the run

## Example Output

```json
[
  {
    "activity_id": 123456789,
    "start_time_local": "2024-01-15T08:30:00",
    "distance_m": 5000,
    "duration_sec": 1800,
    "moving_duration_sec": 1750,
    "average_speed_m_s": 2.78,
    "max_speed_m_s": 4.17,
    "average_hr": 150,
    "max_hr": 165,
    "avg_cadence": 180,
    "max_cadence": 190,
    "steps": 4500,
    "calories": 350,
    "water_estimated_ml": 500,
    "pace_min_per_km": 6.0,
    "moving_ratio": 0.97,
    "splits": [...]
  }
]
```

## Files Generated

- `garmin_raw_activities.json`: Raw activity data from Garmin Connect
- `garmin_summarized_runs.json`: Processed and summarized run data

## Error Handling

The server includes comprehensive error handling for:
- Authentication failures
- Network connectivity issues
- Data parsing errors
- File I/O operations

## Logging

All operations are logged with timestamps and relevant context information for debugging and monitoring.

## Test Files

- `test_mcp_mock.py` - Mock-based unit tests (recommended for CI/CD)
- `test_mcp_simple.py` - Direct function tests with real API calls
- `test_mcp_server.py` - HTTP-based server tests
- `test_simple.py` - Simple functional test script
- `run_server.py` - Server runner for testing

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
python -m pytest -v

# Run specific test file
python -m pytest test_mcp_mock.py -v

# Run with coverage
python -m pytest --cov=server test_mcp_mock.py
```

### Test Structure

The tests are organized into three categories:

1. **Unit Tests** - Test individual functions with mocked dependencies
2. **Integration Tests** - Test the full workflow with real API calls
3. **HTTP Tests** - Test the MCP server endpoints via HTTP requests

This structure ensures comprehensive coverage while handling external API limitations.
