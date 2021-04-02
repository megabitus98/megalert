# global dependencies
from os                     import getenv
from os.path                import join, dirname
from dotenv                 import load_dotenv

# loads environment variables from .env file
dotenv_path = join(dirname(dirname(__file__)), '.env')
load_dotenv(dotenv_path = dotenv_path)

# API configuration
MEGALERT_HOST = getenv("MEGALERT_HOST") if getenv("MEGALERT_HOST") else "0.0.0.0"
MEGALERT_PORT = int(getenv("MEGALERT_PORT")) if getenv("MEGALERT_PORT") else "5000"
MEGALERT_DEBUG = bool(getenv("MEGALERT_DEBUG")) if getenv("MEGALERT_DEBUG") else True

# Mikrotik device configuration
MIKROTIK_HOST = str(getenv("MIKROTIK_HOST"))
MIKROTIK_PORT = int(getenv("MIKROTIK_PORT"))
MIKROTIK_USER = str(getenv("MIKROTIK_USER"))
MIKROTIK_PASS = str(getenv("MIKROTIK_PASS"))

# authentication secret
AUTH_SECRET = str(getenv("AUTH_SECRET"))