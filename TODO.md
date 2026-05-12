# TODO (blackboxai)

- [x] Patch `backend/app/models/voice_embedder.py` to monkeypatch `torchaudio.set_audio_backend` before importing SpeechBrain.

- [ ] Restart backend (uvicorn) and verify `/api/health` works without VoiceEmbedder crash.

