import hmac

from flask import request
from helpers.environment import API_TOKEN, AUTH_SECRET


def is_authorized(legacy_secret=None):
    """Check Authorization: Bearer <token> header, fall back to legacy secret."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return hmac.compare_digest(auth_header[7:], API_TOKEN or "")
    if legacy_secret:
        return hmac.compare_digest(legacy_secret, AUTH_SECRET or "")
    return False
