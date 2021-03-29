# global dependencies
from flask_restful          import reqparse
from time                   import sleep

# local helpers
from helpers.environment    import SECRET

# returns the id for the lte topic
def get_lte_id(logging):
    for logs in logging.get():
        if 'lte' in logs['topics']:
            return logs['id']

# set mkrotik logging for lte topic
def set_lte_logging(mikrotik_api, status):

    # changes bool to mikrotik specific input no / yes
    status = 'no' if status is True else 'yes'

    logging = mikrotik_api.get_resource('/system/logging')
    logging.set(id=get_lte_id(logging), disabled=status)

# get if sms delivery was sucessful
def sms_delivered(mikrotik_api):
    logs = mikrotik_api.get_resource('/log').get()
    for log in logs[-6:]:
        if 'rcvd +CMS ERROR' in log['message']:
            return False
    return True

class SMSService():
    mk_connection = None

    @staticmethod
    def init(mk_connection):
        SMSService.mk_connection = mk_connection
    
    @staticmethod
    def post_sms():
        # initialize argument parser
        parser = reqparse.RequestParser()
        parser.add_argument('number', 
                            type=str, 
                            help='Phone number to send sms to')
        parser.add_argument('body', 
                            type=str, 
                            help='The content for the sms')
        parser.add_argument('secret', 
                            type=str, 
                            help='Autentification secret')
        args = parser.parse_args()

        SMS_NUMBER = ('+' + args['number']).encode() if args['number'][0] != '+' else args['number'].encode()
        SMS_MESSAGE = args['body'].encode()

        # if secret is wrong
        if args['secret'] != SECRET:
            return False, 401 # Unauthorized

        # initialize mikrotik api
        mikrotik_api = SMSService.mk_connection.get_api()
        send_sms = mikrotik_api.get_binary_resource('/tool/sms')

        # active lte logging
        set_lte_logging(mikrotik_api, True)

        # send sms
        send_sms.call('send', { 'message': SMS_MESSAGE,  'phone-number': SMS_NUMBER})

        # wait 2 seconds for logs
        sleep(2)

        # deactive lte logging
        set_lte_logging(mikrotik_api, False)

        # if sms was not delivered
        if not sms_delivered(mikrotik_api):
            # discconect from mikrotik
            SMSService.mk_connection.disconnect()

            return False, 500 # Internal Server Error

        # discconect from mikrotik
        SMSService.mk_connection.disconnect()

        return True, 200 # OK

    @staticmethod
    def get_sms():

        # initialize argument parser
        parser = reqparse.RequestParser()
        parser.add_argument('phone', type=str, help='Phone number to lookup', required=False)
        args = parser.parse_args()

        # adds + sign to the phone number
        phone = (args['phone'].replace(' ', '+') if (args['phone'][0] == ' ' and args['phone'][1].isdigit()) else args['phone']) if args['phone'] != None else None

        # initialize mikrotik api
        mikrotik_api = SMSService.mk_connection.get_api()
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
        SMSService.mk_connection.disconnect()

        return sms_array, 200 # OK