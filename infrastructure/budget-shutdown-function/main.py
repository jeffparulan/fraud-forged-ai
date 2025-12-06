import base64
import json
import os
import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ID = os.environ.get('PROJECT_ID')
REGION = os.environ.get('REGION')
BACKEND_SERVICE = os.environ.get('BACKEND_SERVICE')

def process_budget_alert(data, context):
    """Triggered by Pub/Sub when budget alert fires."""
    try:
        if 'data' in data:
            pubsub_message = base64.b64decode(data['data']).decode('utf-8')
        else:
            logger.error("No data in Pub/Sub message")
            return
        
        budget_data = json.loads(pubsub_message)
        logger.info(f"Budget alert received: {json.dumps(budget_data, indent=2)}")
        
        cost_amount = float(budget_data.get('costAmount', 0))
        budget_amount = float(budget_data.get('budgetAmount', 0))
        threshold_percent = float(budget_data.get('alertThresholdExceeded', 0))
        
        logger.info(f"Cost: ${cost_amount}, Budget: ${budget_amount}, Threshold: {threshold_percent}")
        
        if threshold_percent >= 1.0:
            logger.warning(f"🚨 BUDGET LIMIT REACHED! Initiating shutdown...")
            shutdown_backend_service()
            logger.info("✅ Backend service shutdown complete")
        elif threshold_percent >= 0.9:
            logger.warning(f"⚠️ Budget at 90% - approaching shutdown threshold")
        else:
            logger.info(f"📊 Budget update: {threshold_percent * 100}% used")
            
    except Exception as e:
        logger.error(f"Error processing budget alert: {str(e)}", exc_info=True)

def shutdown_backend_service():
    """Delete the backend service using REST API."""
    try:
        # Use Application Default Credentials
        import google.auth
        
        credentials, project = google.auth.default()
        credentials.refresh(Request())
        access_token = credentials.token
        
        # REST API endpoint
        url = f"https://{REGION}-run.googleapis.com/v2/projects/{PROJECT_ID}/locations/{REGION}/services/{BACKEND_SERVICE}"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Deleting service via REST API: {url}")
        
        response = requests.delete(url, headers=headers, timeout=30)
        
        if response.status_code in [200, 202, 204]:
            logger.info(f"✅ Service deletion initiated successfully")
            logger.info(f"Response: {response.status_code}")
            send_shutdown_notification()
        else:
            logger.error(f"❌ Failed to delete service: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Failed to shutdown service: {str(e)}", exc_info=True)

def send_shutdown_notification():
    """Log critical shutdown notification."""
    logger.info("=" * 60)
    logger.info("🚨 CRITICAL ALERT: BUDGET LIMIT REACHED")
    logger.info(f"📉 Backend service '{BACKEND_SERVICE}' has been DELETED")
    logger.info("💰 This will stop all costs immediately")
    logger.info("=" * 60)
    logger.info("To restore service:")
    logger.info(f"  cd infrastructure && terraform apply")
    logger.info("=" * 60)