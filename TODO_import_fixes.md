# Import Error Fixes TODO

- [x] 1. Edit backend/conftest.py: Add `import asyncio`; change `from backend.app.main import app` to `from app.main import app`
- [x] 2. Edit backend/app/main.py: Comment out unused/non-existing imports (v1 routers, models like ethical_governor if missing)
- [ ] 3. Edit backend/scripts/export_onnx_fixed.py: Wrap insightface/speechbrain in try/except Skip (skipped - exact match fail)
- [ ] 4. Verify with python -c exec each file
- [ ] 5. pip install -r backend/requirements.txt & pytest backend/
- [ ] 6. Update this TODO with ✓ completed
