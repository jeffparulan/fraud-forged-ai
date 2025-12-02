#!/bin/bash
set -x  # Enable debug mode — prints every command executed

echo "=== FRAUDFORGE AI ENTRYPOINT DEBUG (PID 1) ==="
echo "Shell: $BASH_VERSION"
echo "PORT env: '$PORT'"
echo "PWD: $(pwd)"
echo "LS /app: $(ls -la /app)"
echo "LS /app/app: $(ls -la /app/app || echo 'NO /app/app')"
echo "Python version: $(python --version)"
echo "Pip list: $(pip list | head -10)"
echo "Starting uvicorn..."

# Test Python imports
echo "Testing imports..."
python -c "import uvicorn; print('Uvicorn OK')"
python -c "import fastapi; print('FastAPI OK')"
python -c "from app.main import app; print('Main import OK')"
python -c "print('All imports OK')"

# Start uvicorn
exec python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --log-level debug