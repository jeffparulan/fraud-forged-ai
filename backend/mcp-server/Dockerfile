FROM python:3.11-slim

WORKDIR /app

COPY requirements-mcp.txt .
RUN pip install --no-cache-dir -r requirements-mcp.txt

COPY mcp_server.py .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8080"]

