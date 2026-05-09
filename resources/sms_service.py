import logging
import uuid
from datetime import datetime, timezone
from math import ceil
from time import sleep

from flask import request
from flask_restful import reqparse
from phonenumbers import PhoneNumberType, parse
from phonenumbers.phonenumberutil import number_type

from helpers.auth import is_authorized
from helpers.environment import (
    ALLOWED_COUNTRY_CODES,
    MAX_MESSAGE_LENGTH,
    MIKROTIK_SMS_PORT,
)
from helpers.rate_limiter import check_rate_limit

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mikrotik helpers
# ---------------------------------------------------------------------------

def _get_lte_id(logging_resource):
    for entry in logging_resource.get():
        if 'lte' in entry.get('topics', ''):
            return entry['id']
    return None


def _set_lte_logging(mikrotik_api, enabled: bool):
    disabled = 'no' if enabled else 'yes'
    res = mikrotik_api.get_resource('/system/logging')
    lte_id = _get_lte_id(res)
    if lte_id:
        res.set(id=lte_id, disabled=disabled)


def _is_sms_delivered(mikrotik_api) -> bool:
    logs = mikrotik_api.get_resource('/log').get()
    return not any('rcvd +CMS ERROR' in e.get('message', '') for e in logs[-6:])


def _split_message(message: str) -> "list[str]":
    """Split a long message into SMS parts. Prefix X/Y only when more than one part."""
    if len(message) <= 160:
        return [message]

    total = ceil(len(message) / 145)
    parts, idx, current = [], 1, f"1/{total} "
    for word in message.split():
        if len(current) + len(word) < 150:
            current += f'{word} '
        else:
            parts.append(current)
            idx += 1
            current = f'{idx}/{total} {word} '
    parts.append(current)
    return parts


def _mask_phone(phone: str) -> str:
    return phone[:-3].replace(phone[3:-3], '***') if len(phone) > 6 else '***'


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def valid_phone_number(phone: str) -> bool:
    try:
        nt = number_type(parse(phone))
        return nt in (PhoneNumberType.MOBILE, PhoneNumberType.FIXED_LINE_OR_MOBILE)
    except Exception as exc:
        log.debug("phone validation failed for %r: %s", phone, exc)
        return False


def _allowed_country(phone: str) -> bool:
    if not ALLOWED_COUNTRY_CODES:
        return True
    return any(phone.startswith(f'+{cc}') for cc in ALLOWED_COUNTRY_CODES)


def _validate_phone(phone: str):
    """Return (normalized_phone, error_response) tuple. error_response is None on success."""
    if not phone:
        return None, ({'error': 'phone is required'}, 400)
    if not phone.startswith('+'):
        phone = '+' + phone
    if not valid_phone_number(phone):
        return None, ({'error': 'Invalid phone number format, use E.164 (e.g. +491631272782)'}, 400)
    if not _allowed_country(phone):
        return None, ({'error': f'Country code not allowed'}, 403)
    return phone, None


def _validate_message(message: str):
    if not message or not message.strip():
        return None, ({'error': 'message is required'}, 400)
    if len(message) > MAX_MESSAGE_LENGTH:
        return None, ({'error': f'Message exceeds maximum length of {MAX_MESSAGE_LENGTH} characters'}, 400)
    return message.strip(), None


# ---------------------------------------------------------------------------
# Core SMS send logic
# ---------------------------------------------------------------------------

def _send_via_mikrotik(mikrotik_connection, phone: str, message: str) -> bool:
    """Send one or more SMS parts via Mikrotik. Returns True on success."""
    mikrotik_api = mikrotik_connection.get_api()
    sms_resource = mikrotik_api.get_binary_resource('/tool/sms')
    parts = _split_message(message)

    try:
        for part in parts:
            _set_lte_logging(mikrotik_api, True)
            params = {
                'message': part.encode(),
                'phone-number': phone.encode(),
            }
            if MIKROTIK_SMS_PORT:
                params['port'] = MIKROTIK_SMS_PORT.encode()
            sms_resource.call('send', params)
            sleep(2)
            _set_lte_logging(mikrotik_api, False)

            if not _is_sms_delivered(mikrotik_api):
                return False

        return True
    finally:
        mikrotik_connection.disconnect()


# ---------------------------------------------------------------------------
# SMSService
# ---------------------------------------------------------------------------

class SMSService:
    mikrotik_connection = None

    @staticmethod
    def init(mikrotik_connection):
        SMSService.mikrotik_connection = mikrotik_connection

    # ------------------------------------------------------------------
    # POST /api/v1/sms/send  (new primary endpoint)
    # ------------------------------------------------------------------
    @staticmethod
    def send_sms():
        if not is_authorized():
            log.warning("send_sms | unauthorized request from %s", request.remote_addr)
            return {'error': 'Unauthorized — provide Authorization: Bearer <token>'}, 401

        if not check_rate_limit():
            log.warning("send_sms | rate limit exceeded")
            return {'error': 'Rate limit exceeded, try again later'}, 429

        data = request.get_json(silent=True)
        if not data:
            return {'error': 'Expected JSON body'}, 400

        phone, err = _validate_phone(data.get('phone', ''))
        if err:
            return err

        message, err = _validate_message(data.get('message', ''))
        if err:
            return err

        source = data.get('source', 'unknown')
        log.info("send_sms | phone=%s source=%s", _mask_phone(phone), source)

        try:
            ok = _send_via_mikrotik(SMSService.mikrotik_connection, phone, message)
        except Exception as exc:
            log.error("send_sms | mikrotik error: %s", exc)
            return {'error': 'Failed to reach Mikrotik device', 'detail': str(exc)}, 503

        if not ok:
            log.error("send_sms | delivery failed for %s", _mask_phone(phone))
            return {'error': 'SMS delivery failed (CMS error from modem)'}, 500

        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        log.info("send_sms | sent OK | phone=%s id=%s", _mask_phone(phone), message_id)

        return {
            'status': 'sent',
            'phone': phone,
            'message_id': message_id,
            'timestamp': timestamp,
        }, 200

    # ------------------------------------------------------------------
    # POST /api/v1/sms  (legacy — query params, deprecated)
    # ------------------------------------------------------------------
    @staticmethod
    def post_sms():
        parser = reqparse.RequestParser()
        parser.add_argument('number', type=str, required=True, location='args')
        parser.add_argument('body', type=str, required=True, location='args')
        parser.add_argument('secret', type=str, required=True, location='args')
        args = parser.parse_args()

        if not is_authorized(legacy_secret=args['secret']):
            return {'error': 'Unauthorized'}, 401

        phone, err = _validate_phone(args['number'])
        if err:
            return err

        message, err = _validate_message(args['body'])
        if err:
            return err

        if not check_rate_limit():
            return {'error': 'Rate limit exceeded'}, 429

        log.info("post_sms (legacy) | phone=%s", _mask_phone(phone))

        try:
            ok = _send_via_mikrotik(SMSService.mikrotik_connection, phone, message)
        except Exception as exc:
            log.error("post_sms | mikrotik error: %s", exc)
            return {'error': str(exc)}, 503

        return ({'status': 'sent'}, 200) if ok else ({'error': 'SMS delivery failed'}, 500)

    # ------------------------------------------------------------------
    # GET /api/v1/sms  (read inbox, legacy)
    # ------------------------------------------------------------------
    @staticmethod
    def get_sms():
        if not is_authorized():
            log.warning("get_sms | unauthorized request from %s", request.remote_addr)
            return {'error': 'Unauthorized'}, 401

        parser = reqparse.RequestParser()
        parser.add_argument('number', type=str, required=False, location='args')
        args = parser.parse_args()

        number = args.get('number')
        if number and not number.startswith('+'):
            number = '+' + number

        mikrotik_api = SMSService.mikrotik_connection.get_api()
        inbox = mikrotik_api.get_resource('/tool/sms/inbox').get()
        SMSService.mikrotik_connection.disconnect()

        result = [
            {'number': item['phone'], 'timestamp': item['timestamp'], 'message': item['message']}
            for item in inbox
            if number is None or number in item['phone']
        ]
        return result, 200

    # ------------------------------------------------------------------
    # POST /api/v1/sms/webhook  (Uptime Kuma webhook, legacy)
    # ------------------------------------------------------------------
    @staticmethod
    def webhook_sms():
        data = request.get_json(silent=True)
        if not data:
            return {'error': 'Invalid JSON'}, 400

        legacy_secret = data.get('secret')
        if not is_authorized(legacy_secret=legacy_secret):
            return {'error': 'Unauthorized'}, 401

        message, err = _validate_message(data.get('msg', ''))
        if err:
            return err

        phone, err = _validate_phone(request.headers.get('phone', ''))
        if err:
            return err

        if not check_rate_limit():
            return {'error': 'Rate limit exceeded'}, 429

        log.info("webhook_sms | phone=%s", _mask_phone(phone))

        try:
            ok = _send_via_mikrotik(SMSService.mikrotik_connection, phone, message)
        except Exception as exc:
            log.error("webhook_sms | mikrotik error: %s", exc)
            return {'error': str(exc)}, 503

        if not ok:
            return {'error': 'SMS delivery failed'}, 500

        return {'status': 'sent'}, 200
