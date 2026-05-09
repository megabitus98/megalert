"""Unit tests for phone validation, auth, and rate limiting."""
import sys
import types
import unittest
from flask import Flask as _Flask


# ---------------------------------------------------------------------------
# Minimal stubs so we can import sms_service without real env / routeros_api
# ---------------------------------------------------------------------------

def _stub_env(**kwargs):
    """Patch helpers.environment with controllable values."""
    mod = types.ModuleType('helpers.environment')
    mod.API_TOKEN = kwargs.get('API_TOKEN', 'test-token')
    mod.AUTH_SECRET = kwargs.get('AUTH_SECRET', 'test-token')
    mod.MIKROTIK_SMS_PORT = kwargs.get('MIKROTIK_SMS_PORT', 'lte1')
    mod.ALLOWED_COUNTRY_CODES = kwargs.get('ALLOWED_COUNTRY_CODES', [])
    mod.MAX_MESSAGE_LENGTH = kwargs.get('MAX_MESSAGE_LENGTH', 480)
    mod.RATE_LIMIT_PER_MINUTE = kwargs.get('RATE_LIMIT_PER_MINUTE', 10)
    sys.modules['helpers.environment'] = mod
    return mod


# ---------------------------------------------------------------------------
# Phone number validation
# ---------------------------------------------------------------------------

class TestPhoneValidation(unittest.TestCase):

    def setUp(self):
        _stub_env()
        # force reimport so patched env is used
        for m in list(sys.modules):
            if 'sms_service' in m or 'helpers.auth' in m or 'helpers.rate' in m:
                del sys.modules[m]
        from resources.sms_service import valid_phone_number, _validate_phone, _allowed_country
        self.valid_phone_number = valid_phone_number
        self.validate_phone = _validate_phone
        self.allowed_country = _allowed_country

    def test_valid_german_mobile(self):
        self.assertTrue(self.valid_phone_number('+491631272782'))

    def test_invalid_landline(self):
        # German landline — not a mobile number
        self.assertFalse(self.valid_phone_number('+493012345678'))

    def test_invalid_garbage(self):
        self.assertFalse(self.valid_phone_number('not-a-number'))

    def test_validate_phone_adds_plus(self):
        phone, err = self.validate_phone('491631272782')
        self.assertIsNone(err)
        self.assertTrue(phone.startswith('+'))

    def test_validate_phone_empty(self):
        phone, err = self.validate_phone('')
        self.assertIsNone(phone)
        self.assertIsNotNone(err)
        self.assertEqual(err[1], 400)

    def test_country_code_allowed_empty_list(self):
        # empty ALLOWED_COUNTRY_CODES → everything allowed
        self.assertTrue(self.allowed_country('+491631272782'))

    def test_country_code_blocked(self):
        _stub_env(ALLOWED_COUNTRY_CODES=['49'])
        for m in list(sys.modules):
            if 'sms_service' in m:
                del sys.modules[m]
        from resources.sms_service import _allowed_country
        self.assertFalse(_allowed_country('+33123456789'))  # French number

    def test_country_code_passes(self):
        _stub_env(ALLOWED_COUNTRY_CODES=['49'])
        for m in list(sys.modules):
            if 'sms_service' in m:
                del sys.modules[m]
        from resources.sms_service import _allowed_country
        self.assertTrue(_allowed_country('+491631272782'))


# ---------------------------------------------------------------------------
# Message validation
# ---------------------------------------------------------------------------

class TestMessageValidation(unittest.TestCase):

    def setUp(self):
        _stub_env(MAX_MESSAGE_LENGTH=50)
        for m in list(sys.modules):
            if 'sms_service' in m or 'helpers.auth' in m or 'helpers.rate' in m:
                del sys.modules[m]
        from resources.sms_service import _validate_message
        self.validate = _validate_message

    def test_valid_message(self):
        msg, err = self.validate('Hello!')
        self.assertIsNone(err)
        self.assertEqual(msg, 'Hello!')

    def test_empty_message(self):
        _, err = self.validate('')
        self.assertEqual(err[1], 400)

    def test_too_long_message(self):
        _, err = self.validate('x' * 51)
        self.assertEqual(err[1], 400)

    def test_strips_whitespace(self):
        msg, _ = self.validate('  hello  ')
        self.assertEqual(msg, 'hello')


# ---------------------------------------------------------------------------
# Bearer token auth
# ---------------------------------------------------------------------------

class TestBearerAuth(unittest.TestCase):

    def setUp(self):
        _stub_env(API_TOKEN='super-secret', AUTH_SECRET='super-secret')
        for m in list(sys.modules):
            if 'helpers.auth' in m:
                del sys.modules[m]
        self._app = _Flask(__name__)

    def _auth(self, header='', legacy_secret=None):
        from helpers.auth import is_authorized
        headers = {'Authorization': header} if header else {}
        with self._app.test_request_context('/', headers=headers):
            return is_authorized(legacy_secret=legacy_secret)

    def test_valid_bearer(self):
        self.assertTrue(self._auth('Bearer super-secret'))

    def test_invalid_bearer(self):
        self.assertFalse(self._auth('Bearer wrong-token'))

    def test_no_header_no_secret(self):
        self.assertFalse(self._auth(''))

    def test_legacy_secret_fallback(self):
        self.assertTrue(self._auth('', legacy_secret='super-secret'))

    def test_legacy_secret_wrong(self):
        self.assertFalse(self._auth('', legacy_secret='bad'))


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class TestRateLimiter(unittest.TestCase):

    def setUp(self):
        _stub_env(RATE_LIMIT_PER_MINUTE=3)
        for m in list(sys.modules):
            if 'helpers.rate' in m:
                del sys.modules[m]

    def test_within_limit(self):
        from helpers.rate_limiter import check_rate_limit, _timestamps
        _timestamps.clear()
        self.assertTrue(check_rate_limit())
        self.assertTrue(check_rate_limit())
        self.assertTrue(check_rate_limit())

    def test_exceeds_limit(self):
        from helpers.rate_limiter import check_rate_limit, _timestamps
        _timestamps.clear()
        check_rate_limit()
        check_rate_limit()
        check_rate_limit()
        self.assertFalse(check_rate_limit())  # 4th request should be blocked

    def test_old_timestamps_expire(self):
        from helpers.rate_limiter import check_rate_limit, _timestamps
        from time import time
        _timestamps.clear()
        # Add 3 timestamps older than 60 seconds
        old = time() - 61
        _timestamps.extend([old, old, old])
        # Should allow new request since old ones expired
        self.assertTrue(check_rate_limit())


# ---------------------------------------------------------------------------
# Message splitting
# ---------------------------------------------------------------------------

class TestMessageSplit(unittest.TestCase):

    def setUp(self):
        _stub_env()
        for m in list(sys.modules):
            if 'sms_service' in m:
                del sys.modules[m]

    def test_short_message_not_split(self):
        from resources.sms_service import _split_message
        parts = _split_message('Hello World')
        self.assertEqual(len(parts), 1)

    def test_long_message_splits(self):
        from resources.sms_service import _split_message
        long_msg = 'word ' * 60  # ~300 chars
        parts = _split_message(long_msg)
        self.assertGreater(len(parts), 1)
        # Each part must be <= 160 chars
        for part in parts:
            self.assertLessEqual(len(part), 160)


if __name__ == '__main__':
    unittest.main()
