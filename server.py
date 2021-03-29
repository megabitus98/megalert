# global dependencies
from flask                      import Flask
from routeros_api               import RouterOsApiPool
from flask_restful              import Api

# local helpers
from helpers.environment        import HOST, USERNAME, PASSWORD, PORT

# local route handlers
from resources.sms_resolver     import SMSResolver

# handles mikrotik connection
mk_connection = RouterOsApiPool(
    HOST,
    username = USERNAME,
    password = PASSWORD,
    port = PORT,
    plaintext_login = True
)

# initialize Flask and Flask-RESTful
flask_app = Flask(__name__)
flask_api = Api(flask_app)

# initialize route handler
SMSResolver.init(flask_api, mk_connection)

# run app in debug mode on port 5000
if __name__ == '__main__':
    flask_app.run(debug=True, port=5000, host='0.0.0.0')