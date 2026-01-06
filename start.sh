#!/bin/bash
# Start script for Render deployment

# Get port from environment variable (Render provides this)
PORT=${PORT:-8000}

# Start the application
python main.py

