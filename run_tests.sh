#!/bin/bash
# Simple test runner - or just use: make test
set -e
echo "🧪 Running tests..."
pip install -r requirements-test.txt
pytest tests/ -v --cov=custom_components.bedrock_conversation --cov-report=term-missing --cov-report=html
echo "✅ Tests complete!"
echo "📊 Coverage report: htmlcov/index.html"
