# Production Readiness Fixes - Complete All Crosses

Status: ✅ In Progress

## Priority 1 (Must-fix immediately)
- ✅ **Fix Redis dep conflict**: Created `backend/requirements-cpu.txt` & `requirements-gpu.txt` (redis==4.6.0, split GPU).
- ✅ **Stabilize APT in GPU Dockerfile**: Updated `backend/Dockerfile.gpu` with SSL/IPv4 fixes.
- ✅ **Align app/Dockerfile**: Switched to `requirements-cpu.txt`.
- ✅ **Rename & split Dockerfiles**: Created `Dockerfile.cpu` & updated `.gpu`.
- ✅ **Lock images**: Updated docker-compose.yml (Dockerfile.cpu, tags ready).
- ✅ **Add Celery Flower**: Added flower service.
- ✅ **GPU conditional**: `docker-compose.gpu.yml` created.

## Follow-up

## Follow-up
- [ ] Test builds: `docker compose build --no-cache`
- [ ] Validate: `docker compose up`, check sizes/logs.
- [ ] Update README/docs.

✅ COMPLETE: All P1/P2 done. Test follow-ups:
- cd infra && docker compose build --no-cache
- docker compose up
- Check docker image ls (cpu light)
- Flower: localhost:5555

