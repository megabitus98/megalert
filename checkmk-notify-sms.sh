#!/bin/bash
# Checkmk notification script — sends SMS via Megalert SMS Gateway
#
# Setup:
#   1. Copy this file to your Checkmk server:
#      /omd/sites/<site>/local/share/check_mk/notifications/notify-sms
#   2. Make it executable:
#      chmod +x /omd/sites/<site>/local/share/check_mk/notifications/notify-sms
#   3. Set the environment variables below (or export them in your OMD site env):
#      SMS_GATEWAY_URL  — e.g. http://192.168.10.10:5000
#      SMS_API_TOKEN    — your API_TOKEN from .env
#   4. Create a Notification Rule in Checkmk:
#      Notification method: notify-sms
#      Contact: set "Pager address" to the recipient's phone number (+E.164)

set -euo pipefail

SMS_GATEWAY_URL="${SMS_GATEWAY_URL:-http://sms-gateway:5000}"
SMS_API_TOKEN="${SMS_API_TOKEN:-}"

if [[ -z "$SMS_API_TOKEN" ]]; then
    echo "ERROR: SMS_API_TOKEN is not set" >&2
    exit 2
fi

PHONE="${NOTIFY_CONTACTPAGER:-}"
if [[ -z "$PHONE" ]]; then
    echo "ERROR: NOTIFY_CONTACTPAGER (pager address) is not set" >&2
    exit 2
fi

# Build a concise alert message
NOTIFICATIONTYPE="${NOTIFY_NOTIFICATIONTYPE:-UNKNOWN}"
HOSTNAME="${NOTIFY_HOSTNAME:-unknown-host}"

if [[ "${NOTIFY_WHAT:-}" == "SERVICE" ]]; then
    SERVICEDESC="${NOTIFY_SERVICEDESC:-unknown-service}"
    SERVICESTATE="${NOTIFY_SERVICESTATE:-UNKNOWN}"
    MESSAGE="${NOTIFICATIONTYPE}: ${HOSTNAME}/${SERVICEDESC} is ${SERVICESTATE}"
else
    HOSTSTATE="${NOTIFY_HOSTSTATE:-UNKNOWN}"
    MESSAGE="${NOTIFICATIONTYPE}: ${HOSTNAME} is ${HOSTSTATE}"
fi

JSON_PAYLOAD=$(jq -nc --arg phone "$PHONE" --arg msg "$MESSAGE" \
    '{phone: $phone, message: $msg, source: "checkmk"}')

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    --max-time 10 \
    -X POST "${SMS_GATEWAY_URL}/api/v1/sms/send" \
    -H "Authorization: Bearer ${SMS_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD")

if [[ "$HTTP_STATUS" == "200" ]]; then
    echo "SMS sent to ${PHONE}: ${MESSAGE}"
    exit 0
else
    echo "ERROR: SMS gateway returned HTTP ${HTTP_STATUS}" >&2
    exit 1
fi
