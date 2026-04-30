# AI-f Sovereign OS - API Reference (v2.0.0)

## 1. Authentication
### `POST /api/auth/login`
Authenticates a user and returns a JWT access token.
- **Parameters**: `email`, `password` (Query or Form)
- **Returns**: `{ access_token, token_type, user }`

### `POST /api/auth/mfa/verify`
Verifies a TOTP/SMS MFA code.
- **Header**: `Authorization: Bearer <token>`
- **Parameters**: `code`

## 2. Biometrics & Identity

> **⚠️ IMPORTANT:** All biometric endpoints (`/api/enroll`, `/api/recognize`) now require authentication.
> This change was made to prevent biometric inference attacks. 
> Include `Authorization: Bearer <token>` header in all requests to these endpoints.

### `POST /api/enroll` (Authentication Required)
Enrolls a new multi-modal identity.
- **Authentication**: Required (JWT Bearer token)
- **Body**: `multipart/form-data` (image, audio, metadata)
- **Permissions**: `enroll_identity`
- **Error if unauthenticated**: 401 Unauthorized

### `POST /api/recognize` (Authentication Required)
Recognizes an identity from an image.
- **Authentication**: Required (JWT Bearer token)
- **Body**: `multipart/form-data` (image, options)
- **Permissions**: `view_recognitions`
- **Error if unauthenticated**: 401 Unauthorized

### `GET /api/v2/recognize/stream` (WebSocket)
Real-time biometric streaming.
- **Protocol**: `ws://`
- **Query**: `token=<jwt>`

## 3. Administration & Compliance
### `GET /api/admin/logs`
Retrieves hash-chained audit logs.
- **Permissions**: `view_audit_logs`

### `POST /api/compliance/erasure`
Executes a GDPR-compliant "Right to be Forgotten" request.
- **Permissions**: `delete_data`

## 4. Webhooks (Inbound)
### `POST /api/webhooks/stripe`
Handles billing events.
- **Verification**: `X-Stripe-Signature` (HMAC-SHA256)

### `POST /api/webhooks/biometric-event`
Outbound event notification schema reference.
- **Verification**: `X-AIF-Signature`

## 5. System Health
### `GET /api/health`
Detailed system and model health status.
- **Public**: Yes
- **Returns**: `{ status, model_loaded, db_connected }`
