from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from typing import List
import cv2
import numpy as np
import uuid
import base64
import tempfile
import os
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.voice_embedder import VoiceEmbedder
from ..models.gait_analyzer import GaitAnalyzer
from ..models.age_gender_estimator import AgeGenderEstimator
from ..db.db_client import get_db
from ..schemas import EnrollRequest, EnrollResponse
from ..security import require_auth
from ..metrics import enroll_count, enroll_latency
import json
import time

router = APIRouter()

detector = FaceDetector()
embedder = FaceEmbedder()
voice_embedder = VoiceEmbedder()
gait_analyzer = GaitAnalyzer()
age_gender_estimator = AgeGenderEstimator()


@router.post("/enroll", response_model=EnrollResponse)
async def enroll_person(
    request: Request,
    images: List[UploadFile] = File(...),
    name: str = Form(None),
    metadata: str = Form("{}"),
    consent: bool = Form(...),
    camera_id: str = Form(None),
    voice_files: List[UploadFile] = File(None),
    gait_video: UploadFile = File(None),
    physiological_data: str = Form("{}"),
    user: dict = Depends(require_auth)
):
    start_time = time.time()

    if not consent:
        raise HTTPException(
            status_code=400, detail="Consent required for enrollment")

    try:
        metadata_dict = json.loads(metadata)
        physio_dict = json.loads(physiological_data)
    except:
        metadata_dict = {}
        physio_dict = {}

    embeddings = []
    voice_embeddings = []
    age = None
    gender = None

    for img_file in images:
        contents = await img_file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Skip spoof check for enrollment
        faces = detector.detect_faces(img, check_spoof=False, reconstruct=True)
        if not faces:
            continue

        # Use first face
        face = faces[0]
        aligned = detector.align_face(img, face['landmarks'])
        emb = embedder.get_embedding(aligned)
        embeddings.append(emb)

        # Estimate age/gender from first image
        if age is None:
            age_gender = age_gender_estimator.estimate_age_gender(
                img, face['bbox'])
            age = age_gender['age']
            gender = age_gender['gender']

    if not embeddings:
        raise HTTPException(
            status_code=400, detail="No valid faces found in images")

    # Process voice files
    if voice_files:
        for voice_file in voice_files:
            contents = await voice_file.read()
            # Save to temp file for librosa
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            try:
                voice_emb = voice_embedder.get_embedding(tmp_path)
                voice_embeddings.append(voice_emb)
            finally:
                os.unlink(tmp_path)

    # Process gait video
    gait_embedding = None
    if gait_video:
        contents = await gait_video.read()
        nparr = np.frombuffer(contents, np.uint8)
        cap = cv2.VideoCapture()
        cap.open(nparr)
        frames = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            if len(frames) >= 30:  # Limit frames
                break
        cap.release()
        if frames:
            gait_embedding = gait_analyzer.extract_gait_features(frames)

    person_id = str(uuid.uuid4())

    consent_record = {
        'consent_record_id': str(uuid.uuid4()),
        'client_id': user.get('user_id'),
        'consent_text_version': 'v1',
        'captured_ip': request.client.host,
        'signed_token': None
    }

    db = await get_db()
    await db.enroll_person(person_id, name, embeddings, consent_record, camera_id, voice_embeddings, gait_embedding, age, gender)

    enroll_count.inc()
    enroll_latency.observe(time.time() - start_time)

    return EnrollResponse(
        person_id=person_id,
        num_embeddings=len(embeddings),
        example_embedding_id=str(uuid.uuid4()),
        message="Enrollment successful"
    )
