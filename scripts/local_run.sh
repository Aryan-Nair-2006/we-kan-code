#!/bin/bash
echo "Starting local environment..."

# Start FastAPI in the background
uvicorn backend.app.main:app --reload --port 8000 &
FASTAPI_PID=$!

# Start Streamlit
streamlit run frontend/app.py

# When Streamlit is killed, kill FastAPI as well
kill $FASTAPI_PID
