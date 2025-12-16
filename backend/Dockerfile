FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire app directory maintaining structure
COPY app/ ./app/

# Expose port (documentation only)
EXPOSE 8080

# Use exec form and ensure PORT is read correctly
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1