# Run Agent

A collection of running-related tools and APIs for fitness tracking and coaching.

## Projects

### 🏃‍♂️ Running Coach API
A FastAPI-based running coach that generates personalized training programs.

**Location**: `running-coach/`

**Features**:
- Generate weekly training plans based on distance goals and time frames
- AI-powered running recommendations
- Program history and management
- RESTful API with comprehensive documentation

**Quick Start**:
```bash
cd running-coach
pip install -r requirements.txt
python main.py
```

**API Documentation**: http://127.0.0.1:8000/docs

### 📊 Garmin MCP Server
A Model Context Protocol (MCP) server for Garmin Connect integration.

**Location**: `garmin-mcp/`

**Features**:
- Fetch running activities from Garmin Connect
- Summarize run data with metrics and insights
- Export data to JSON files
- Clean, modular code with proper logging

**Quick Start**:
```bash
cd garmin-mcp
pip install -r requirements.txt
python server.py
```

**Server**: http://127.0.0.1:3000

## Project Structure

```
run-agent/
├── README.md                 # This file
├── main.py                   # Main entry point
├── garmin-mcp/              # Garmin Connect MCP server
│   ├── server.py            # MCP server implementation
│   └── requirements.txt     # Dependencies
└── running-coach/           # FastAPI running coach
    ├── main.py              # FastAPI application
    ├── constants.py         # Configuration constants
    ├── schemas.py           # Pydantic models
    ├── logic.py             # Business logic
    ├── requirements.txt     # Dependencies
    └── README.md            # Detailed documentation
```

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd run-agent
```

2. Install dependencies for each project:
```bash
# For Running Coach
cd running-coach
pip install -r requirements.txt

# For Garmin MCP
cd ../garmin-mcp
pip install -r requirements.txt
```

### Running the Applications

#### Running Coach API
```bash
cd running-coach
python main.py
```
- API: http://127.0.0.1:8000
- Docs: http://127.0.0.1:8000/docs

#### Garmin MCP Server
```bash
cd garmin-mcp
python server.py
```
- Server: http://127.0.0.1:3000

## Features Overview

### Running Coach API
- **Program Generation**: Create personalized training plans
- **Goal Setting**: Set distance goals and time frames
- **Weekly Plans**: Detailed weekly training schedules
- **Recommendations**: AI-powered running advice
- **History Management**: Save and retrieve programs
- **RESTful API**: Clean, documented endpoints

### Garmin MCP Server
- **Activity Fetching**: Retrieve running activities from Garmin Connect
- **Data Summarization**: Process and summarize run metrics
- **Export Capabilities**: Save data to JSON files
- **MCP Integration**: Model Context Protocol server
- **Clean Architecture**: Modular, well-structured code