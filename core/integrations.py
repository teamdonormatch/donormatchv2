# ============================================================
# DonorMatch — Multi-Source Integration Client
# ============================================================
# All external sources are configured via environment variables.
# Add as many sources as you want. Each source is independent.
# The app fans out to ALL enabled sources simultaneously.
#
# ENV VARIABLES PER SOURCE (replace N with 1, 2, 3 ...):
#
#   SOURCE_N_NAME         = "My N8N Prod"
#   SOURCE_N_TYPE         = n8n | webhook | rest_api | custom
#   SOURCE_N_BASE_URL     = https://donormatch.app.n8n.cloud/webhook-test
#   SOURCE_N_API_KEY      = (optional Bearer token or API key)
#   SOURCE_N_BLOOD_REQUEST_PATH   = emergency-blood-request
#   SOURCE_N_AVAILABILITY_PATH    = check-donor-availability
#   SOURCE_N_NOTIFY_PATH          = notify-donor
#   SOURCE_N_ENABLED      = true | false
#
# You can also configure individual full URLs per action:
#   SOURCE_N_BLOOD_REQUEST_URL    = https://full-override-url.com/path
#   SOURCE_N_AVAILABILITY_URL     = https://...
#   SOURCE_N_NOTIFY_URL           = https://...
#
# EXAMPLE — two sources in .env:
#
#   SOURCE_1_NAME=N8N Production
#   SOURCE_1_BASE_URL=https://donormatch.app.n8n.cloud/webhook-test
#   SOURCE_1_BLOOD_REQUEST_PATH=emergency-blood-request
#   SOURCE_1_AVAILABILITY_PATH=check-donor-availability
#   SOURCE_1_NOTIFY_PATH=notify-donor
#   SOURCE_1_ENABLED=true
#
#   SOURCE_2_NAME=Backup Webhook
#   SOURCE_2_BASE_URL=https://my-other-service.com/hooks
#   SOURCE_2_BLOOD_REQUEST_PATH=blood
#   SOURCE_2_AVAILABILITY_PATH=check
#   SOURCE_2_NOTIFY_PATH=notify
#   SOURCE_2_API_KEY=secret-key-here
#   SOURCE_2_ENABLED=true
# ============================================================

import os
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_SOURCES = 10   # scan SOURCE_1 through SOURCE_10
TIMEOUT     = 10   # seconds per outbound request


class ExternalSource:
    """Represents one configured external source."""

    def __init__(self, index):
        prefix = f'SOURCE_{index}_'

        self.index    = index
        self.name     = os.environ.get(f'{prefix}NAME', f'Source {index}')
        self.type     = os.environ.get(f'{prefix}TYPE', 'webhook').lower()
        self.base_url = os.environ.get(f'{prefix}BASE_URL', '').rstrip('/')
        self.api_key  = os.environ.get(f'{prefix}API_KEY', '')
        self.enabled  = os.environ.get(f'{prefix}ENABLED', 'false').lower() in ('true', '1', 'yes')

        # Per-action path (appended to base_url)
        self.blood_request_path  = os.environ.get(f'{prefix}BLOOD_REQUEST_PATH',  'emergency-blood-request')
        self.availability_path   = os.environ.get(f'{prefix}AVAILABILITY_PATH',   'check-donor-availability')
        self.notify_path         = os.environ.get(f'{prefix}NOTIFY_PATH',         'notify-donor')

        # Full URL overrides (skip base_url entirely if set)
        self.blood_request_url   = os.environ.get(f'{prefix}BLOOD_REQUEST_URL',   '')
        self.availability_url    = os.environ.get(f'{prefix}AVAILABILITY_URL',    '')
        self.notify_url          = os.environ.get(f'{prefix}NOTIFY_URL',          '')

    def _url(self, override_url, path):
        if override_url:
            return override_url
        if not self.base_url:
            return None
        return f'{self.base_url}/{path.lstrip("/")}'

    def _headers(self):
        h = {'Content-Type': 'application/json'}
        if self.api_key:
            h['Authorization'] = f'Bearer {self.api_key}'
            h['X-API-Key']     = self.api_key
        return h

    def post(self, url, payload):
        if not url:
            logger.warning(f'[{self.name}] No URL configured — skipping')
            return False
        try:
            resp = requests.post(url, json=payload, headers=self._headers(), timeout=TIMEOUT)
            logger.info(f'[{self.name}] POST {url} → {resp.status_code}')
            return resp.status_code in (200, 201, 202)
        except requests.exceptions.ConnectionError:
            logger.warning(f'[{self.name}] Not reachable: {url}')
            return False
        except Exception as e:
            logger.error(f'[{self.name}] Error: {e}')
            return False

    def send_blood_request(self, payload):
        url = self._url(self.blood_request_url, self.blood_request_path)
        return self.post(url, payload)

    def send_availability_check(self, payload):
        url = self._url(self.availability_url, self.availability_path)
        return self.post(url, payload)

    def send_notify_donor(self, payload):
        url = self._url(self.notify_url, self.notify_path)
        return self.post(url, payload)

    def __repr__(self):
        return f'<Source {self.index}: {self.name} enabled={self.enabled}>'


class IntegrationRouter:
    """
    Loads all configured sources from environment variables.
    Fans out every action to all enabled sources in parallel.
    Falls back gracefully if a source is unreachable.
    """

    def __init__(self):
        self.app_url = getattr(settings, 'BASE_URL', 'http://localhost:8000').rstrip('/')
        self._sources = None   # lazy-loaded

    @property
    def sources(self):
        if self._sources is None:
            self._sources = self._load_sources()
        return self._sources

    def _load_sources(self):
        found = []
        for i in range(1, MAX_SOURCES + 1):
            base = os.environ.get(f'SOURCE_{i}_BASE_URL', '')
            if not base:
                continue
            s = ExternalSource(i)
            if s.enabled:
                found.append(s)
                logger.info(f'Integration source loaded: {s}')
        if not found:
            logger.warning('No integration sources configured. Check SOURCE_N_* env vars.')
        return found

    def reload(self):
        """Force reload sources — useful after env changes without restart."""
        self._sources = None
        return self.sources

    def _fan_out(self, method_name, payload):
        """Call method_name on all enabled sources in parallel."""
        if not self.sources:
            logger.warning(f'fan_out({method_name}): no sources enabled')
            return {}

        results = {}
        with ThreadPoolExecutor(max_workers=len(self.sources)) as pool:
            futures = {
                pool.submit(getattr(s, method_name), payload): s
                for s in self.sources
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results[source.name] = future.result()
                except Exception as e:
                    logger.error(f'[{source.name}] fan_out error: {e}')
                    results[source.name] = False

        succeeded = sum(1 for v in results.values() if v)
        logger.info(f'{method_name}: {succeeded}/{len(results)} sources responded OK')
        return results

    # ── Public actions ───────────────────────────────────────

    def send_blood_request(self, blood_request, hospital):
        """
        Fires to ALL enabled sources in parallel.
        Every source receives a callback_url pointing back to this app.
        """
        payload = {
            'request_id':        blood_request.id,
            'blood_group':       blood_request.blood_group,
            'units_needed':      blood_request.units_needed,
            'urgency':           blood_request.urgency,
            'hospital_name':     hospital.name,
            'hospital_city':     hospital.city,
            'hospital_state':    hospital.state,
            'hospital_phone':    hospital.phone,
            'patient_condition': blood_request.patient_condition,
            'callback_url':      f'{self.app_url}/webhook/inbound/donors-found/',
        }
        return self._fan_out('send_blood_request', payload)

    def request_availability_check(self, match):
        donor = match.donor
        payload = {
            'match_id':     match.id,
            'donor_id':     donor.id,
            'donor_phone':  donor.phone,
            'donor_name':   f'{donor.first_name} {donor.last_name}',
            'blood_group':  donor.blood_group,
            'callback_url': f'{self.app_url}/webhook/inbound/availability-result/',
        }
        return self._fan_out('send_availability_check', payload)

    def notify_selected_donor(self, donor, hospital, amount, reference):
        payload = {
            'donor_name':        f'{donor.first_name} {donor.last_name}',
            'donor_phone':       donor.phone,
            'hospital_name':     hospital.name,
            'hospital_address':  hospital.address,
            'payment_amount':    str(amount),
            'payment_reference': reference,
        }
        return self._fan_out('send_notify_donor', payload)

    def status(self):
        """Returns a summary of all configured sources — for the admin UI."""
        return [
            {
                'index':   s.index,
                'name':    s.name,
                'type':    s.type,
                'base_url': s.base_url,
                'enabled': s.enabled,
                'paths': {
                    'blood_request':  s.blood_request_url or f'{s.base_url}/{s.blood_request_path}',
                    'availability':   s.availability_url  or f'{s.base_url}/{s.availability_path}',
                    'notify':         s.notify_url        or f'{s.base_url}/{s.notify_path}',
                }
            }
            for s in self._load_sources()
        ]


# Singleton
router = IntegrationRouter()