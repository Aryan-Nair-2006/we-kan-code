#!/bin/bash
echo "Setting up Team Knowledge Finder local environment..."
python -m venv .venv
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
echo "Setup complete. To run tests: pytest"
