from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends
from typing import List
import cv2
import numpy as np
import uuid
import base64
import tempfile
import os
import json
import time
import logging
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.voice_embedder import VoiceEmbedder
from ..models.gait_analyzer import GaitAnalyzer
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.privacy_engine import dp_engine
from ..db.db_client import get_db
from ..schemas import StandardResponse
from ..security import require_auth
from ..metrics import enroll_count, enroll_latency
from ..middleware.policy_enforcement import require_enroll_policy

logger = logging.getLogger(__name__)
router = APIRouter()

detector = FaceDetector()
embedder = FaceEmbedder()
voice_embedder = VoiceEmbedder()
gait_analyzer = GaitAnalyzer()
age_gender_estimator = AgeGenderEstimator()


@router.post("/identities/merge")
async def merge_identities(source_id: str, target_id: str, user: dict = Depends(require_auth)):
    """Merge source person into target person, moving all embeddings and events."""
    db = await get_db()
    
    # 1. Update embeddings
    await db.pool.execute("UPDATE embeddings SET person_id = $1 WHERE person_id = $2", target_id, source_id)
    
    # 2. Update recognition events
    await db.pool.execute("UPDATE recognition_events SET person_id = $1 WHERE person_id = $2", target_id, source_id)
    
    # 3. Delete source person
    await db.delete_person(source_id)
    
    return {"success": True, "message": f"Merged {source_id} into {target_id}"}


@router.post("/identities/split")
async def split_identity(person_id: str, embedding_ids: List[str], new_name: str, user: dict = Depends(require_auth)):
    """Split specific embeddings into a new identity."""
    db = await get_db()
    new_person_id = str(uuid.uuid4())
    
    # 1. Create new person
    await db.pool.execute("""
        INSERT INTO persons (person_id, name, created_at)
        VALUES ($1, $2, NOW())
    """, new_person_id, new_name)
    
    # 2. Move specified embeddings
    for emb_id in embedding_ids:
        await db.pool.execute("UPDATE embeddings SET person_id = $1 WHERE embedding_id = $2", new_person_id, emb_id)
        
    return {"success": True, "new_person_id": new_person_id}
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
    user: dict = Depends(require_auth),
    _policy_ok: bool = Depends(require_enroll_policy)
):
    try:
        start_time = time.time()

        if not consent:
            return StandardResponse(success=False, error="Consent required for enrollment")

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

            if img is None:
                continue

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
            return StandardResponse(success=False, error="No valid faces found in images")

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
            # Write to a temporary file for cv2.VideoCapture
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                tmp.write(contents)
                tmp_path = tmp.name
            try:
                cap = cv2.VideoCapture(tmp_path)
                frames = []
                while cap.isOpened() and len(frames) < 30:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    frames.append(frame)
                cap.release()
                if frames:
                    gait_embedding = gait_analyzer.extract_gait_features(frames)
            finally:
                os.unlink(tmp_path)

        # Apply differential privacy noise to embeddings before storage
        embeddings = [dp_engine.add_noise(emb) for emb in embeddings]
        if voice_embeddings:
            voice_embeddings = [dp_engine.add_noise(v) for v in voice_embeddings]
        if gait_embedding is not None:
            gait_embedding = dp_engine.add_noise(gait_embedding)

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

        return StandardResponse(
            success=True,
            data={
                "person_id": person_id,
                "num_embeddings": len(embeddings),
                "message": f"Successfully enrolled {name or 'unknown person'}"
            },
            error=None
        )
    except Exception as e:
        logger.error(f"Enrollment error: {e}", exc_info=True)
        return StandardResponse(success=False, error=str(e))
