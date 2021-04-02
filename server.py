# global dependencies
from flask                      import Flask
from routeros_api               import RouterOsApiPool
from flask_restful              import Api

# in-project dependencies
from helpers.environment        import MEGALERT_HOST
from helpers.environment        import MEGALERT_PORT
from helpers.environment        import MEGALERT_DEBUG
from helpers.environment        import MIKROTIK_HOST
from helpers.environment        import MIKROTIK_PORT
from helpers.environment        import MIKROTIK_USER
from helpers.environment        import MIKROTIK_PASS
## route handlers
from resources.sms_resolver     import SMSResolver

# handles connection to Mikrotik device
mikrotik_connection = RouterOsApiPool(
    MIKROTIK_HOST,
    username = MIKROTIK_USER,
    password = MIKROTIK_PASS,
    port = MIKROTIK_PORT,
    plaintext_login = True
)

# initialize Flask and Flask-RESTful
flask = Flask(__name__)
api = Api(flask)

# initialize route handler
SMSResolver.init(api, mikrotik_connection)

# start Flask
if __name__ == '__main__':
    flask.run(debug = MEGALERT_DEBUG, port = MEGALERT_PORT, host = MEGALERT_HOST)