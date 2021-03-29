# global dependencies
from flask_restful import Resource

# local dependencies
from .sms_service   import SMSService

# used for route handeling in server.py
class SMSResolver():

    @staticmethod
    def init(flask_api, mk_connection):
        SMSService.init(mk_connection)
        flask_api.add_resource(SMSGeneric, '/api/v1/sms')

# handles requests regarding sms
class SMSGeneric(Resource):
    def post(self):
        return SMSService.post_sms()

    def get(self):
        return SMSService.get_sms()