# Running Coach - NiceGUI Frontend

A clean, minimal Python-only frontend using NiceGUI that integrates with the existing FastAPI backend.

## Features

- **Simple Form Interface**: Input goal distance (km) and time frame (weeks)
- **Real-time Program Generation**: Submit form to generate personalized training programs
- **Program History**: View previously generated programs
- **Loading States**: Clear feedback during API calls
- **Error Handling**: User-friendly error messages with retry logic
- **Responsive Design**: Clean, accessible UI with semantic HTML

## Setup

### Prerequisites

- Python 3.8+
- Running FastAPI backend (see main project README)

### Installation

1. Install additional dependencies for the frontend:
```bash
pip install nicegui httpx
```

2. Add NiceGUI to your existing requirements:
```bash
echo "nicegui>=1.4.0" >> requirements.txt
echo "httpx>=0.24.0" >> requirements.txt
```

### Environment Variables

Set the backend URL (optional, defaults to localhost):
```bash
export BACKEND_URL="http://127.0.0.1:8000"
```

## Usage

### Mounting to Existing FastAPI App

To integrate the NiceGUI frontend with your existing FastAPI backend:

1. **Import and mount in your main FastAPI app** (`main.py`):
```python
from fastapi import FastAPI
from app.ui_nicegui import mount_ui

# Your existing FastAPI app
app = FastAPI(title="Running Coach API", ...)

# Mount the NiceGUI UI
mount_ui(app)
```

2. **Run the combined application**:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

3. **Access the application**:
- **Backend API**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Frontend UI**: http://127.0.0.1:8000/ui

### Standalone Mode (Development)

For development/testing, you can run the UI standalone:

```python
# In a separate terminal
python -c "from app.ui_nicegui import RunningCoachUI; ui = RunningCoachUI(); ui.create_ui(); ui.run()"
```

## API Integration

The frontend integrates with these backend endpoints:

- **POST /programs**: Create new running program
  - Input: `{ "goal_km": float, "time_weeks": int }`
  - Output: `{ "program_id": str, "weekly_plans": [...], "recommendations": [...] }`

- **GET /history**: Retrieve program history
  - Output: `{ "total_programs": int, "programs": [...] }`

## Project Structure

```
app/
├── ui_nicegui.py          # Main NiceGUI interface
├── constants.py           # UI strings and configuration
└── utils/
    ├── logger.py          # Structured logging
    └── http_client.py     # HTTP client with retries
```

## Features Implementation

### Form Validation
- Client-side validation for goal distance (1-1000 km)
- Time frame validation (1-52 weeks)
- Real-time feedback on invalid inputs

### Loading States
- Button loading indicator during API calls
- Spinner animation with loading message
- Disabled form during processing

### Error Handling
- HTTP client with exponential backoff retry logic
- User-friendly error messages
- Comprehensive logging for debugging

### History Management
- Tab-based interface for program history
- Compact program previews with key metrics
- Automatic refresh on history tab access

### Local Storage (TODO)
- "Save locally" toggle for browser storage
- Currently logs action (localStorage implementation pending)

## Development

### Logging
The application uses structured logging with timestamps and metadata:
```python
from app.utils.logger import logger

logger.info("User action", action="form_submit", goal_km=5.0)
logger.error("API error", endpoint="/programs", status_code=500)
```

### HTTP Client
Robust HTTP client with:
- Automatic retries with exponential backoff
- Timeout handling
- Status code validation
- Comprehensive error logging

### Constants
All UI strings and configuration in `app/constants.py`:
- Route paths
- UI labels and messages
- Validation limits
- HTTP client settings

## Troubleshooting

### Common Issues

1. **Backend not responding**: Check `BACKEND_URL` environment variable
2. **Port conflicts**: NiceGUI uses port 8080 by default when mounted
3. **Import errors**: Ensure all dependencies are installed (`nicegui`, `httpx`)

### Debug Mode
Enable debug logging:
```python
import logging
logging.getLogger("running_coach_ui").setLevel(logging.DEBUG)
```

## Next Steps

- [ ] Implement localStorage saving for offline access
- [ ] Add program export functionality
- [ ] Enhance mobile responsiveness
- [ ] Add program sharing features