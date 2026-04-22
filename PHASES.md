# PHASES ROADMAP - FULL PRODUCT DEVELOPMENT

## ✅ PHASE 1 COMPLETE (Core Hardening)
- RTSP multi-cam (5 cams, reconnect, buffer)
- Offline SQLite sync/logging
- Celery/Redis <300ms queue  
- FAR<1%/FRR<3% tuning (threshold=0.6)
- Jetson/edge adapter
- Load test (locust 100users)

## 📋 PHASE 2: SECURITY & ACCESS CONTROL (Next)

### Access Control (`app/access_control.py`)
```
class AccessRule:
    role: str = "staff"
    time_window: Tuple[time, time] = (9:00, 18:00)
    blacklisted: bool = False
```

### Alerts (`app/alerts.py`)
```
await send_email("unauthorized@company.com", "Unknown face detected")
await send_whatsapp("+91...", "Alert: Blacklisted person")
```

### Audit Logs (`db_client.py` expanded)
```
CSV export / PDF / search API / hash chain
```

### TODO.md for Phase 2
```
1. Create app/access_control.py
2. Edit db_client.py (+access_logs table)
3. Add alerts email/whatsapp
4. UI endpoints /reports/audit
```

## 🎯 PHASE 3: FRONTEND DASHBOARD (React/Next.js)
```
ui/react-app/src/
├── Dashboard.jsx (live cams + alerts)
├── UserManagement.jsx (CRUD + bulk CSV)
├── Reports.jsx (PDF/CSV download)
```

## 🛒 PHASE 4: RETAIL ANALYTICS (Post MVP)
```
footfall API / repeat customer / dwell time
```

## 💼 PHASE 5: BILLING (Stripe live)
```
usage tracking → invoice → limits
```

## 🚀 PHASE 6: SALES READY
```
demo.docker / installer.sh / brochure.pdf
```

**Run Phase 2?** `y` to start security features.

