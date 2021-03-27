# global dependencies
from flask                  import Flask
from routeros_api           import RouterOsApiPool
from os                     import getenv
from os.path                import join, dirname
from dotenv                 import load_dotenv
from flask_restful          import Api, Resource, reqparse

# loads environment variables from .env file
dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

# mikrotik configuration
HOST = getenv("HOST")
USERNAME = getenv("USERNAME")
PASSWORD = getenv("PASSWORD")
PORT = int(getenv("PORT"))

# authentification secret
SECRET = getenv("SECRET")

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

class GenericSMS(Resource):

    @staticmethod
    def post():

        # initialize argument parser
        parser = reqparse.RequestParser()
        parser.add_argument('number', type=str, help='Phone number to send sms to')
        parser.add_argument('body', type=str, help='The content for the sms')
        parser.add_argument('secret', type=str, help='Autentification secret')
        args = parser.parse_args()

        SMS_NUMBER = ('+' + args['number']).encode() if args['number'][0] != '+' else args['number'].encode()
        SMS_MESSAGE = args['body'].encode()

        # if secret is wrong
        if args['secret'] != SECRET:
            return False, 401 # Unauthorized

        # initialize mikrotik api
        mikrotik_api = mk_connection.get_api()
        send_sms = mikrotik_api.get_binary_resource('/tool/sms')

        # send sms
        send_sms.call('send', { 'message': SMS_MESSAGE,  'phone-number': SMS_NUMBER})

        # discconect from mikrotik
        mk_connection.disconnect()

        return True, 200 # OK

    @staticmethod
    def get():

        # initialize argument parser
        parser = reqparse.RequestParser()
        parser.add_argument('phone', type=str, help='Phone number to lookup', required=False)
        args = parser.parse_args()

        # adds + sign to the phone number
        phone = (args['phone'].replace(' ', '+') if (args['phone'][0] == ' ' and args['phone'][1].isdigit()) else args['phone']) if args['phone'] != None else None

        # initialize mikrotik api
        mikrotik_api = mk_connection.get_api()
        sms_inbox = mikrotik_api.get_resource('/tool/sms/inbox').get()

        # prepare sms array
        sms_array = list()

        # append sms to array
        for item in sms_inbox:
            if phone == None or (phone != None and phone in item['phone']):
                # sms metadata
                sms = {
                    'phone': item['phone'],
                    'timestamp': item['timestamp'],
                    'message': item['message']
                }

                # append sms metadata to array
                sms_array.append(sms)

        # discconect from mikrotik
        mk_connection.disconnect()

        return sms_array, 200 # OK


# initialize route handler
flask_api.add_resource(GenericSMS, '/api/v1/sms')


# run app in debug mode on port 5000
if __name__ == '__main__':
    flask_app.run(debug=True, port=5000, host='0.0.0.0')