#!/bin/bash
set -e

echo "Starting Quality Assurance Test Suite..."
echo "=========================================="
./venv/bin/python manage.py test
echo "=========================================="
echo "✅ All tests passed successfully!"
