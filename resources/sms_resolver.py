# global dependencies
from flask_restful  import Resource

# in-project dependencies
from .sms_service   import SMSService

# used for route handling in server.py
class SMSResolver():

    @staticmethod
    def init(flask_api, mikrotik_connection):
        SMSService.init(mikrotik_connection)
        flask_api.add_resource(SMSGeneric, '/api/v1/sms')

# handles requests regarding SMS messages
class SMSGeneric(Resource):
    def post(self):
        return SMSService.post_sms()

    def get(self):
        return SMSService.get_sms()