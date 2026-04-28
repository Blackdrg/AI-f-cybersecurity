## 📡 API Reference

### Base URL
```
Production: https://api.example.com/api
Staging:    https://staging.example.com/api
Local:      http://localhost:8000/api
```

### Authentication
All endpoints except `POST /enroll`, `POST /recognize` require JWT:
```
Authorization: Bearer <jwt_token>
```

### Complete Endpoint List (30+ endpoints)

**Core Recognition:**
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/enroll` | Optional | Multi-modal identity enrollment |
| POST | `/api/recognize` | None | Face recognition (public) |
| GET | `/api/persons` | Required | List identities (paginated) |
| GET | `/api/persons/{person_id}` | Required | Get identity details |
| PUT | `/api/persons/{person_id}` | Required | Update identity |
| DELETE | `/api/persons/{person_id}` | Required | Delete + GDPR erasure |
| POST | `/api/identities/merge` | Required | Merge duplicate identities |

**Real-Time & Video:**
| Method | Endpoint | Protocol | Description |
|--------|----------|----------|-------------|
| WS | `/ws/recognize_stream` | WebSocket | Live camera stream recognition |
| POST | `/api/video_recognize` | HTTP | Batch video file processing |

**SaaS Platform:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users` | Self-registration |
| GET | `/api/users/me` | Current user profile |
| PUT | `/api/users/me` | Update profile |
| DELETE | `/api/users/me` | GDPR deletion |
| POST | `/api/auth/login` | JWT login |
| POST | `/api/auth/refresh` | Refresh token |
| GET | `/api/plans` | Subscription plans |
| POST | `/api/subscriptions` | Create subscription |
| GET | `/api/subscriptions/me` | Current subscription |
| POST | `/api/payments/create-session` | Stripe checkout |
| POST | `/api/payments/webhook` | Stripe webhook |
| GET | `/api/usage/current` | Monthly usage |
| GET | `/api/organizations` | List organizations |
| POST | `/api/organizations` | Create organization |
| GET | `/api/orgs/{org_id}/members` | List members |
| POST | `/api/orgs/{org_id}/members` | Add member |

**Cameras & Devices:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orgs/{org_id}/cameras` | List cameras |
| POST | `/api/orgs/{org_id}/cameras` | Register RTSP camera |
| PUT | `/api/orgs/{org_id}/cameras/{camera_id}` | Update config |
| DELETE | `/api/orgs/{org_id}/cameras/{camera_id}` | Delete camera |
| POST | `/api/orgs/{org_id}/cameras/test-connection` | Test RTSP URL |

**Admin & Operations:**
| Method | Endpoint | RBAC | Description |
|--------|----------|------|-------------|
| GET | `/api/admin/metrics` | `VIEW_METRICS` | System metrics |
| GET | `/api/admin/logs` | `VIEW_AUDIT_LOGS` | Audit log query |
| POST | `/api/admin/index/rebuild` | `MANAGE_INDEX` | Rebuild vector index |

**Compliance & Consent:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/compliance/export/{person_id}` | GDPR data export |
| DELETE | `/api/compliance/delete/{person_id}` | GDPR erasure |
| GET | `/api/compliance/status` | Compliance status |
| GET | `/api/audit/verify` | Verify audit chain |
| POST | `/api/consent/enroll` | Record biometric consent |
| GET | `/api/consent/verify` | Verify consent token |
| POST | `/api/consent/revoke` | Revoke consent |
| GET | `/api/consent/history` | Consent history |

**Analytics & AI:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics` | Dashboard metrics |
| GET | `/api/analytics/bias-trends` | Fairness trends |
| POST | `/api/ai/assistant` | Query LLM assistant |
| GET | `/api/explanations/{id}` | XAI breakdown |

**Federated Learning & OTA:**
| Method | Endpoint | Security | Description |
|--------|----------|----------|-------------|
| POST | `/api/federated/update` | Service token | Gradient upload |
| GET | `/api/models/download` | API key | OTA model download |

**System & Health:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/api/health` | Detailed health |
| GET | `/api/version` | Version + features |
| GET | `/metrics` | Prometheus metrics |