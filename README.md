# Realtor Agent Validation API

FastAPI application for scraping and validating realtor agent information from onereal.com and other sources.

## Features

- Scrape agent information from onereal.com
- Verify agent details against websites
- Playwright MCP support for browser automation
- RESTful API endpoints

## API Endpoints

- `GET /health` - Health check
- `GET /scrape-agents` - Scrape all agents (basic info)
- `GET /scrape-profile/{profile_id}` - Get detailed agent profile
- `GET /scrape-agents-full` - Scrape all agents with full details (Playwright)
- `GET /scrape-agents-full-mcp` - Scrape all agents with full details (Playwright MCP)
- `GET /scrape-local-agents` - Scrape agents from local HTML page
- `POST /verify-agent` - Verify agent details (Playwright)
- `POST /verify-agent-mcp` - Verify agent details (Playwright MCP)
- `GET /docs` - API documentation (Swagger UI)

## Local Development

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Run Locally

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## Deployment on Render

### Automatic Deployment

1. Connect your GitHub repository to Render
2. Render will automatically detect `render.yaml` and deploy
3. The build process will:
   - Install Python dependencies
   - Install Playwright Chromium browser
   - Start the FastAPI application

### Manual Configuration

If not using `render.yaml`, configure:

- **Build Command:** `pip install -r requirements.txt && playwright install chromium`
- **Start Command:** `python main.py`
- **Environment:** Python 3
- **Port:** Auto-detected from `PORT` environment variable

### Environment Variables

- `PORT` - Server port (automatically set by Render)
- `HOST` - Server host (default: 0.0.0.0)

## Project Structure

```
.
├── main.py                 # FastAPI application
├── scraper.py              # Playwright-based scraper
├── scraper_mcp.py          # Playwright MCP-based scraper
├── playwright_mcp_client.py # Playwright MCP client
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
└── README.md              # This file
```

## Requirements

- Python 3.11+
- Playwright (with Chromium browser)
- FastAPI
- Uvicorn

## License

MIT
