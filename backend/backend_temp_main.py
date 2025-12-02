from fastapi import FastAPI
import os

app = FastAPI(title="FraudForge AI - TEMP LIVE CHECK")

@app.get("/")
def root():
    return {"status": "FraudForge AI is ALIVE", "port": os.getenv("PORT", "8080")}

@app.get("/api/health")
def health():
    return {"status": "healthy"}

print("Temporary server starting on port", os.getenv("PORT", "8080"))
