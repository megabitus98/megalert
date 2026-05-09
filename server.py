import logging
import sys

from flask import Flask
from flask_restful import Api
from flasgger import Swagger
from routeros_api import RouterOsApiPool

from helpers.environment import (
    MEGALERT_HOST,
    MEGALERT_PORT,
    MEGALERT_DEBUG,
    MIKROTIK_HOST,
    MIKROTIK_PORT,
    MIKROTIK_USER,
    MIKROTIK_PASS,
)
from resources.sms_resolver import SMSResolver

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG if MEGALERT_DEBUG else logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mikrotik connection pool
# ---------------------------------------------------------------------------
mikrotik_connection = RouterOsApiPool(
    MIKROTIK_HOST,
    username=MIKROTIK_USER,
    password=MIKROTIK_PASS,
    port=MIKROTIK_PORT,
    plaintext_login=True,
)

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------
flask = Flask(__name__)

swagger_config = {
    'headers': [],
    'specs': [
        {
            'endpoint': 'apispec',
            'route': '/apispec.json',
            'rule_filter': lambda rule: True,
            'model_filter': lambda tag: True,
        }
    ],
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs_route': '/apidocs',
}

swagger_template = {
    'info': {
        'title': 'Megalert — MikroTik SMS Gateway',
        'description': (
            'Universal SMS gateway powered by a MikroTik LTE router. '
            'Supports Checkmk, Home Assistant, Uptime Kuma, and any HTTP client.'
        ),
        'version': '2.0.0',
        'contact': {'name': 'megalert'},
    },
    'securityDefinitions': {
        'BearerAuth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Enter: Bearer <your-api-token>',
        }
    },
    'host': f'{MEGALERT_HOST}:{MEGALERT_PORT}',
    'basePath': '/',
}

api = Api(flask)
Swagger(flask, config=swagger_config, template=swagger_template)

SMSResolver.init(api, mikrotik_connection)

log.info("Megalert SMS Gateway starting on %s:%s", MEGALERT_HOST, MEGALERT_PORT)

if __name__ == '__main__':
    flask.run(debug=MEGALERT_DEBUG, port=MEGALERT_PORT, host=MEGALERT_HOST)
