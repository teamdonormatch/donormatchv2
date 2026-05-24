import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_to_n8n(payload):
    url = getattr(settings, 'N8N_WEBHOOK_URL', '').strip()
    if not url:
        logger.error('N8N_WEBHOOK_URL is not set')
        return {'success': False, 'error': 'N8N_WEBHOOK_URL not configured'}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if resp.status_code in (200, 201, 202):
            logger.info(f'N8N success: {resp.status_code}')
            try:
                return {'success': True, 'data': resp.json()}
            except:
                return {'success': True, 'data': resp.text}
        else:
            logger.error(f'N8N failed: {resp.status_code} {resp.text}')
            return {'success': False, 'error': f'N8N returned {resp.status_code}: {resp.text}'}
    except requests.exceptions.ConnectionError as e:
        logger.error(f'N8N connection error: {e}')
        return {'success': False, 'error': 'Could not connect to N8N. Check N8N_WEBHOOK_URL.'}
    except requests.exceptions.Timeout:
        return {'success': False, 'error': 'N8N did not respond within 15 seconds'}
    except Exception as e:
        logger.error(f'N8N unexpected error: {e}')
        return {'success': False, 'error': str(e)}
