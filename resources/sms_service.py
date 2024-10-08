# global dependencies
from flask_restful                      import reqparse
from time                               import sleep
from math                               import ceil
from flask                              import request
from phonenumbers                       import carrier
from phonenumbers                       import parse
from phonenumbers.phonenumberutil       import number_type

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

# splits a message, and returns a list of strings with a maximum of 160 characters
def split_message_sms_friendly(message):
    splited_message_array = []
    index = 1
    total_messages = ceil(len(message)/145)
    combined_message = f"{index}/{total_messages} "
    for word in message.split():
        if len(combined_message) + len(word) < 150:
            combined_message += f'{word} '
        else:
            index += 1
            splited_message_array.append(combined_message)
            combined_message = f"{index}/{total_messages} {word} "
    splited_message_array.append(combined_message)

    return splited_message_array

def valid_phone_number(phone_number):
    valid = False
    try:
        valid = carrier._is_mobile(number_type(parse(phone_number)))
    except:
        valid = False
    
    return valid

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
            help = 'Phone number to send the SMS message to',
            required = True,
            location = 'args'
        )
        parser.add_argument(
            'body', type = str, 
            help = 'Content of the SMS message',
            required = True,
            location = 'args'
        )
        parser.add_argument(
            'secret', type=str, 
            help = 'Authentication secret',
            required = True,
            location = 'args'
        )
        args = parser.parse_args()

        print(args)

        sms_number = args['number']
        
        if args['number'][0] != '+':
            sms_number = '+' + sms_number
        
        # if phone number is invalid
        if not valid_phone_number(sms_number):
            return {'message': 'Invalid phone number format'}, 400 
        
        sms_number = sms_number.encode()
        sms_message = args['body']

        # if authentication secret is wrong
        if args['secret'] != AUTH_SECRET:
            return False, 401 # Unauthorized

        # initialize Mikrotik API
        mikrotik_api = SMSService.mikrotik_connection.get_api()
        sms_resource = mikrotik_api.get_binary_resource('/tool/sms')

        # parse the list of messages
        for sms in split_message_sms_friendly(sms_message):
            # active lte logging
            set_lte_logging(mikrotik_api, True)

            print(f"Body: {sms} | Phone: {sms_number}")

            # send sms
            sms_resource.call('send', { 'message': sms.encode(),  'phone-number': sms_number})

            # wait 2 seconds for logs
            sleep(2)

            # deactive lte logging
            set_lte_logging(mikrotik_api, False)

            # if sms was not delivered
            if not is_sms_delivered(mikrotik_api):
                # discconect from mikrotik
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
            help = 'Phone number to look up',
            location = 'args'
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
    
    @staticmethod
    def webhook_sms():
        # Get the JSON payload from the request
        data = request.get_json()
    
        if data is None:
            return {'message': 'Invalid JSON data'}, 400  # Bad Request
    
        # Extract the SMS message content from the 'msg' field
        sms_message = data.get('msg', '').strip()
    
        if not sms_message:
            return {'message': 'No message to send'}, 400  # Bad Request
    
        # Get the phone number from the headers
        sms_number = request.headers.get('phone')
    
        if not sms_number:
            return {'message': 'Phone number header is missing'}, 400  # Bad Request
    
        # Ensure the phone number starts with '+'
        if not sms_number.startswith('+'):
            sms_number = '+' + sms_number

        # Get the authorization value from headers or JSON
        auth_value = request.headers.get('Authorization')
        if not auth_value:
            # Try to get 'secret' from JSON payload
            auth_value = data.get('secret')

        if auth_value != AUTH_SECRET:
            return {'message': 'Unauthorized'}, 401  # Unauthorized
    
        # Initialize Mikrotik API
        mikrotik_api = SMSService.mikrotik_connection.get_api()
        sms_resource = mikrotik_api.get_binary_resource('/tool/sms')
    
        # Split message if necessary
        messages = split_message_sms_friendly(sms_message)
    
        for message in messages:
            # Activate LTE logging
            set_lte_logging(mikrotik_api, True)
    
            # Send SMS
            sms_resource.call('send', {
                'message': message.encode(),
                'phone-number': sms_number.encode()
            })
    
            # Wait for logs
            sleep(2)
    
            # Deactivate LTE logging
            set_lte_logging(mikrotik_api, False)
    
            # Check if SMS was delivered
            if not is_sms_delivered(mikrotik_api):
                # Disconnect from Mikrotik
                SMSService.mikrotik_connection.disconnect()
                return {'message': 'Failed to send SMS'}, 500  # Internal Server Error
    
        # Disconnect from Mikrotik device
        SMSService.mikrotik_connection.disconnect()
    
        return {'message': 'SMS sent successfully'}, 200  # OK