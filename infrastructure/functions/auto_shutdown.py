"""
Auto-shutdown Cloud Function
Triggered by budget alerts to control cloud costs
"""
import base64
import json
import os
from google.cloud import run_v2
from google.api_core import exceptions

def shutdown_services(event, context):
    """
    Cloud Function triggered by Pub/Sub when budget threshold is exceeded.
    Scales Cloud Run services to zero to prevent further costs.
    """
    project_id = os.environ.get('PROJECT_ID')
    backend_service = os.environ.get('BACKEND_SERVICE')
    region = os.environ.get('REGION')
    
    # Decode Pub/Sub message
    if 'data' in event:
        message_data = base64.b64decode(event['data']).decode('utf-8')
        budget_notification = json.loads(message_data)
        
        # Check if budget exceeded
        cost_amount = budget_notification.get('costAmount', 0)
        budget_amount = budget_notification.get('budgetAmount', 0)
        
        print(f"Budget Alert: Cost ${cost_amount} / Budget ${budget_amount}")
        
        # Only shutdown if budget significantly exceeded (>80%)
        if cost_amount > (budget_amount * 0.8):
            print(f"Budget exceeded 80% threshold, initiating shutdown...")
            
            try:
                # Initialize Cloud Run client
                client = run_v2.ServicesClient()
                
                # Service path
                service_path = f"projects/{project_id}/locations/{region}/services/{backend_service}"
                
                # Get current service
                service = client.get_service(name=service_path)
                
                # Update to min instances = 0, max instances = 0 (effectively shutdown)
                service.template.scaling.min_instance_count = 0
                service.template.scaling.max_instance_count = 0
                
                # Update service
                operation = client.update_service(service=service)
                print(f"Shutdown initiated for {backend_service}")
                
                # Wait for operation to complete
                response = operation.result()
                print(f"Service {backend_service} scaled to zero successfully")
                
                return {
                    'status': 'success',
                    'message': f'Services shutdown to prevent cost overrun',
                    'cost': cost_amount,
                    'budget': budget_amount
                }
                
            except exceptions.GoogleAPIError as e:
                print(f"Error shutting down service: {e}")
                return {
                    'status': 'error',
                    'message': str(e)
                }
        else:
            print(f"Cost ${cost_amount} is within acceptable range, no action taken")
            return {
                'status': 'no_action',
                'message': 'Cost within acceptable limits',
                'cost': cost_amount
            }
    
    return {
        'status': 'error',
        'message': 'Invalid event data'
    }

