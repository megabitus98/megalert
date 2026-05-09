# Megalert — MikroTik SMS Gateway

A production-ready SMS gateway that sends alerts via a MikroTik LTE router.  
Supports **Checkmk**, **Home Assistant**, **Uptime Kuma**, and any HTTP client.

---

## Quick Start

### Docker (recommended)

```bash
docker run -d -p 5000:5000 \
  -e MIKROTIK_HOST=192.168.10.2 \
  -e MIKROTIK_USER=<routeros-username> \
  -e MIKROTIK_PASS=<routeros-password> \
  -e API_TOKEN=<generate-with-openssl-rand-hex-32> \
  megabitus/megalert
```

### Docker Compose

```bash
cp .env.sample .env
# edit .env with your values
docker compose up -d
```

### Local

```bash
cp .env.sample .env
# edit .env with your values
pip3 install -r requirements.txt
python3 server.py
```

---

## Environment Variables

The gateway exits at startup if `MIKROTIK_HOST`, `MIKROTIK_USER`, `MIKROTIK_PASS`, or `API_TOKEN` are unset.

| Variable | Required | Default | Description |
|---|---|---|---|
| `MIKROTIK_HOST` | ✅ | — | IP address of the MikroTik router |
| `MIKROTIK_USER` | ✅ | — | RouterOS username |
| `MIKROTIK_PASS` | ✅ | — | RouterOS password |
| `API_TOKEN` | ✅ | — | Bearer token for the API (`Authorization: Bearer <token>`) |
| `MIKROTIK_PORT` | | `8728` | RouterOS API port |
| `MIKROTIK_SMS_PORT` | | *(MikroTik default)* | LTE interface for outgoing SMS (e.g. `lte1`). Leave empty to let MikroTik pick its default interface. |
| `MEGALERT_HOST` | | `0.0.0.0` | API bind address |
| `MEGALERT_PORT` | | `5000` | API port |
| `MEGALERT_DEBUG` | | `false` | Enable debug logging |
| `ALLOWED_COUNTRY_CODES` | | *(all)* | Allowed country calling codes, comma-separated (e.g. `49,43`) |
| `MAX_MESSAGE_LENGTH` | | `480` | Maximum message length in characters |
| `RATE_LIMIT_PER_MINUTE` | | `10` | Maximum SMS per minute (per Gunicorn worker) |

---

## API

Swagger UI: **http://localhost:5000/apidocs**

### Authentication

All endpoints (except `/health`) require a Bearer token in the header:

```
Authorization: Bearer <API_TOKEN>
```

### Endpoints

#### `POST /api/v1/sms/send` — Send SMS *(primary endpoint)*

```bash
curl -X POST http://localhost:5000/api/v1/sms/send \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+491631272782", "message": "Host DOWN!", "source": "checkmk"}'
```

**Request body:**

| Field | Required | Description |
|---|---|---|
| `phone` | ✅ | Phone number in E.164 format (e.g. `+491631272782`) |
| `message` | ✅ | Message text |
| `source` | | Sender label for logging (e.g. `checkmk`) |

**Response `200`:**
```json
{
  "status": "sent",
  "phone": "+491631272782",
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-04-30T12:00:00+00:00"
}
```

**Error codes:**

| Code | Meaning |
|---|---|
| `400` | Missing or invalid fields |
| `401` | Missing or invalid Bearer token |
| `403` | Country code not allowed |
| `429` | Rate limit exceeded |
| `500` | SMS delivery failed (modem error) |
| `503` | MikroTik unreachable |

---

#### `GET /health` — Health Check

```bash
curl http://localhost:5000/health
# {"status": "ok"}
```

---

#### `POST /api/v1/sms/webhook` — Webhook (Uptime Kuma, generic)

```bash
curl -X POST http://localhost:5000/api/v1/sms/webhook \
  -H "Authorization: Bearer <your-token>" \
  -H "phone: +491631272782" \
  -H "Content-Type: application/json" \
  -d '{"msg": "Service DOWN"}'
```

---

#### `POST /api/v1/sms` *(deprecated)* / `GET /api/v1/sms`

Legacy endpoints that still work but are no longer recommended.  
`GET /api/v1/sms` reads the MikroTik SMS inbox (must be enabled in RouterOS: `/tool sms set receive-enabled=yes`).

---

## Checkmk Integration

The notification script is at [checkmk-notify-sms.sh](checkmk-notify-sms.sh).

**Setup:**

```bash
cp checkmk-notify-sms.sh /omd/sites/<site>/local/share/check_mk/notifications/notify-sms
chmod +x /omd/sites/<site>/local/share/check_mk/notifications/notify-sms
```

**Set environment variables on the Checkmk server:**

```bash
export SMS_GATEWAY_URL=http://192.168.10.10:5000
export SMS_API_TOKEN=<your-api-token>
```

**Checkmk Notification Rule:**
- Notification method: `notify-sms`
- Contact → Pager address: phone number in E.164 format (e.g. `+491631272782`)

---

## Home Assistant Integration

```yaml
# configuration.yaml
rest_command:
  send_sms:
    url: "http://192.168.10.10:5000/api/v1/sms/send"
    method: POST
    headers:
      Authorization: "Bearer <your-token>"
      Content-Type: application/json
    payload: '{"phone": "{{ phone }}", "message": "{{ message }}", "source": "home-assistant"}'
```

**Automation example:**

```yaml
action:
  - service: rest_command.send_sms
    data:
      phone: "+491631272782"
      message: "Doorbell pressed!"
```

---

## Security Notes

- Never commit `API_TOKEN` to version control — `.env` is in `.gitignore`
- Create a MikroTik user with minimal permissions (only `/tool/sms` and `/log`)
- Set `ALLOWED_COUNTRY_CODES` to block unintended recipients
- `RATE_LIMIT_PER_MINUTE` protects against alert storms (note: applies per Gunicorn worker)

---

## Disclaimer

_Megalert comes with ABSOLUTELY NO WARRANTY, to the extent permitted by applicable law._

## License

Distributed under the [MIT License](LICENSE).
