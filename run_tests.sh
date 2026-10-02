#!/bin/bash
set -e

source venv/bin/activate
python -m pytest tests/ -v --tb=short
