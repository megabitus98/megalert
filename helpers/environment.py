from os import getenv
from os.path import join, dirname
from dotenv import load_dotenv
import logging
import sys

dotenv_path = join(dirname(dirname(__file__)), '.env')
load_dotenv(dotenv_path=dotenv_path)

log = logging.getLogger(__name__)


def _require(name):
    value = getenv(name)
    if not value:
        logging.critical("Required environment variable '%s' is not set. Exiting.", name)
        sys.exit(1)
    return value


# API configuration
MEGALERT_HOST = getenv("MEGALERT_HOST", "0.0.0.0")
MEGALERT_PORT = int(getenv("MEGALERT_PORT", "5000"))
MEGALERT_DEBUG = getenv("MEGALERT_DEBUG", "false").lower() == "true"

# Mikrotik device configuration
MIKROTIK_HOST = _require("MIKROTIK_HOST")
MIKROTIK_PORT = int(getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_USER = _require("MIKROTIK_USER")
MIKROTIK_PASS = _require("MIKROTIK_PASS")
# Leave empty to let MikroTik pick its default LTE interface (pre-v1.0 behavior).
MIKROTIK_SMS_PORT = getenv("MIKROTIK_SMS_PORT", "")

# Authentication
# API_TOKEN is the primary Bearer token. Falls back to AUTH_SECRET for existing
# installs that have not yet renamed the variable.
_api_token = getenv("API_TOKEN")
_auth_secret = getenv("AUTH_SECRET")

if not _api_token and not _auth_secret:
    logging.critical(
        "Either API_TOKEN (preferred) or AUTH_SECRET (legacy) must be set. Exiting."
    )
    sys.exit(1)

if not _api_token and _auth_secret:
    log.warning(
        "AUTH_SECRET is set but API_TOKEN is not. Using AUTH_SECRET as the Bearer token "
        "for backwards compatibility. Rename AUTH_SECRET to API_TOKEN before the next release."
    )
    _api_token = _auth_secret

API_TOKEN = _api_token
AUTH_SECRET = _auth_secret or _api_token  # legacy body-param fallback

# Validation
_raw_cc = getenv("ALLOWED_COUNTRY_CODES", "")
ALLOWED_COUNTRY_CODES = [c.strip() for c in _raw_cc.split(",") if c.strip()]
MAX_MESSAGE_LENGTH = int(getenv("MAX_MESSAGE_LENGTH", "480"))

# Rate limiting
RATE_LIMIT_PER_MINUTE = int(getenv("RATE_LIMIT_PER_MINUTE", "10"))
