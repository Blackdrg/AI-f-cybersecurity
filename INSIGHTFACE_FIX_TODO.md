# Insightface Install Fix - TODO Steps
Status: [ ] In Progress

## Steps from Approved Plan:

1. [ ] Edit `backend/requirements.txt`: Comment out `insightface==0.7.3`, add note `# insightface==0.7.3  # Requires MSVC on Windows/Python 3.11; export ONNX offline`
2. [ ] Edit `backend/requirements-cpu.txt`: Same comment out + note
3. [ ] Edit `backend/requirements-gpu.txt`: Same
4. [ ] Read & edit `docs/troubleshooting.md`: Append insightface Windows fix section
5. [ ] Read & edit `README.md`: Add dev setup warning
6. [ ] Read & edit `DEVELOPER_EXPERIENCE_FIX.md`: Update with fix
7. [ ] Test: User runs `pip install -r backend/requirements-cpu.txt`
8. [ ] Verify tests: `pytest backend/tests/test_recognize.py`
9. [ ] Mark complete, attempt_completion

Next step: 1-3 (requirements edits)

