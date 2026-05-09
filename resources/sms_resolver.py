from flask_restful import Resource

from .sms_service import SMSService


class SMSResolver:

    @staticmethod
    def init(flask_api, mikrotik_connection):
        SMSService.init(mikrotik_connection)
        flask_api.add_resource(SMSSend,    '/api/v1/sms/send')
        flask_api.add_resource(SMSGeneric, '/api/v1/sms')
        flask_api.add_resource(SMSWebhook, '/api/v1/sms/webhook')
        flask_api.add_resource(Health,     '/health')


# ---------------------------------------------------------------------------
# PRIMARY endpoint
# ---------------------------------------------------------------------------

class SMSSend(Resource):
    def post(self):
        """
        Send an SMS (primary endpoint)
        ---
        tags:
          - SMS
        security:
          - BearerAuth: []
        consumes:
          - application/json
        parameters:
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - phone
                - message
              properties:
                phone:
                  type: string
                  example: "+491631272782"
                  description: E.164 phone number
                message:
                  type: string
                  example: "Checkmk: host DOWN"
                  description: SMS text (max configured MAX_MESSAGE_LENGTH chars)
                source:
                  type: string
                  example: "checkmk"
                  description: Caller identifier for logging
        responses:
          200:
            description: SMS sent successfully
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "sent"
                phone:
                  type: string
                  example: "+491631272782"
                message_id:
                  type: string
                  example: "550e8400-e29b-41d4-a716-446655440000"
                timestamp:
                  type: string
                  example: "2026-04-30T12:00:00+00:00"
          400:
            description: Bad request (missing/invalid fields)
          401:
            description: Unauthorized — missing or invalid Bearer token
          403:
            description: Country code not in allowlist
          429:
            description: Rate limit exceeded
          500:
            description: SMS delivery failed (modem error)
          503:
            description: Mikrotik device unreachable
        """
        return SMSService.send_sms()


# ---------------------------------------------------------------------------
# LEGACY endpoints (deprecated, kept for backward compatibility)
# ---------------------------------------------------------------------------

class SMSGeneric(Resource):
    def post(self):
        """
        Send an SMS via query parameters (deprecated — use /api/v1/sms/send)
        ---
        tags:
          - SMS (legacy)
        deprecated: true
        parameters:
          - name: number
            in: query
            type: string
            required: true
            description: E.164 phone number
          - name: body
            in: query
            type: string
            required: true
            description: SMS message content
          - name: secret
            in: query
            type: string
            required: true
            description: Auth secret (legacy — prefer Authorization Bearer header)
        responses:
          200:
            description: Sent
          400:
            description: Invalid phone or missing parameter
          401:
            description: Unauthorized
          429:
            description: Rate limit exceeded
          500:
            description: Delivery failed
        """
        return SMSService.post_sms()

    def get(self):
        """
        List SMS inbox
        ---
        tags:
          - SMS (legacy)
        parameters:
          - name: number
            in: query
            type: string
            required: false
            description: Filter by phone number (E.164)
        responses:
          200:
            description: List of SMS messages
            schema:
              type: array
              items:
                type: object
                properties:
                  number:
                    type: string
                  timestamp:
                    type: string
                  message:
                    type: string
        """
        return SMSService.get_sms()


class SMSWebhook(Resource):
    def post(self):
        """
        Send SMS via webhook (Uptime Kuma / generic)
        ---
        tags:
          - Webhook
        security:
          - BearerAuth: []
        consumes:
          - application/json
        parameters:
          - name: phone
            in: header
            type: string
            required: true
            description: E.164 phone number
          - name: Authorization
            in: header
            type: string
            required: false
            description: "Bearer <token>"
          - name: body
            in: body
            required: true
            schema:
              type: object
              required:
                - msg
              properties:
                msg:
                  type: string
                  description: SMS message text
                secret:
                  type: string
                  description: Legacy auth secret (deprecated)
        responses:
          200:
            description: SMS sent
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "sent"
          400:
            description: Bad request
          401:
            description: Unauthorized
          429:
            description: Rate limit exceeded
          500:
            description: Delivery failed
        """
        return SMSService.webhook_sms()


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class Health(Resource):
    def get(self):
        """
        Health check
        ---
        tags:
          - System
        responses:
          200:
            description: Service is healthy
            schema:
              type: object
              properties:
                status:
                  type: string
                  example: "ok"
        """
        return {'status': 'ok'}, 200
