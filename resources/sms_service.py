# global dependencies
from flask_restful          import reqparse
from time                   import sleep

# in-project dependencies
from helpers.environment    import AUTH_SECRET

# returns the ID for the LTE topic
def get_lte_id(logging_resource):
    for logs in logging_resource.get():
        if 'lte' in logs['topics']:
            return logs['id']
    return None

# set Mikrotik device logging for LTE topic
def set_lte_logging(mikrotik_api, status):
    # converts bool to Mikrotik device specific input (yes/no)
    disabled_status = 'no' if status is True else 'yes'

    logging_resource = mikrotik_api.get_resource('/system/logging')
    logging_resource.set(
        id = get_lte_id(logging_resource), 
        disabled = disabled_status
    )

# get if SMS delivery was successful
def is_sms_delivered(mikrotik_api):
    logs = mikrotik_api.get_resource('/log').get()
    
    for log in logs[-6:]:
        if 'rcvd +CMS ERROR' in log['message']:
            return False
    return True

class SMSService():
    mikrotik_connection = None

    @staticmethod
    def init(mikrotik_connection):
        SMSService.mikrotik_connection = mikrotik_connection
    
    @staticmethod
    def post_sms():
        # initialize argument parser
        parser = reqparse.RequestParser()
        parser.add_argument(
            'number', type = str, 
            help = 'Phone number to send the SMS message to'
        )
        parser.add_argument(
            'body', type = str, 
            help = 'Content of the SMS message'
        )
        parser.add_argument(
            'secret', type=str, 
            help = 'Authentication secret'
        )
        args = parser.parse_args()

        sms_number = args['number']
        
        if args['number'][0] != '+':
            sms_number = '+' + sms_number
        
        sms_number = sms_number.encode()
        sms_message = args['body'].encode()

        # if authentication secret is wrong
        if args['secret'] != AUTH_SECRET:
            return False, 401 # Unauthorized

        # initialize Mikrotik API
        mikrotik_api = SMSService.mikrotik_connection.get_api()
        sms_resource = mikrotik_api.get_binary_resource('/tool/sms')

        # activate LTE logging
        set_lte_logging(mikrotik_api, True)

        # send SMS message
        sms_resource.call('send', { 
            'message': sms_message,
            'phone-number': sms_number
        })

        # wait 2 seconds for logs
        sleep(2)

        # deactivate LTE logging
        set_lte_logging(mikrotik_api, False)

        # if SMS message was not delivered
        if not is_sms_delivered(mikrotik_api):
            SMSService.mikrotik_connection.disconnect()
            return False, 500 # Internal Server Error

        # disconnect from Mikrotik device
        SMSService.mikrotik_connection.disconnect()

        return True, 200 # OK

    @staticmethod
    def get_sms():
        # initialize argument parser
        parser = reqparse.RequestParser()
        parser.add_argument(
            'number', type = str, required = False,
            help = 'Phone number to look up'
        )
        args = parser.parse_args()

        # adds + sign to the phone number
        number = args['number']
        if number != None and number[0] == ' ' and number[1].isdigit():
            number.replace(' ', '+')
            
        # initialize Mikrotik API
        mikrotik_api = SMSService.mikrotik_connection.get_api()
        sms_inbox_resource = mikrotik_api.get_resource('/tool/sms/inbox').get()

        # prepare SMS array
        sms_array = list()

        # append SMS to array
        for item in sms_inbox_resource:
            if number == None or (number != None and number in item['phone']):
                # SMS metadata
                sms = {
                    'number': item['phone'],
                    'timestamp': item['timestamp'],
                    'message': item['message']
                }

                # append SMS metadata to array
                sms_array.append(sms)

        # disconnect from Mikrotik device
        SMSService.mikrotik_connection.disconnect()

        return sms_array, 200 # OK