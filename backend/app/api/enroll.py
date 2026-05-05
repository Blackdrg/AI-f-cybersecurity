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
import socket
import struct
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.voice_embedder import VoiceEmbedder
from ..models.gait_analyzer import GaitAnalyzer
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.privacy_engine import dp_engine
from ..models.ethical_governor import ethical_governor
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


def recvall(conn, n):
    """Helper function to receive n bytes or return None if EOF is reached."""
    data = b''
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def send_request_to_enclave(request_dict):
    """Send encrypted request to enclave via VSOCK with attestation.
    
    Encrypts embedding field, sends via VSOCK, decrypts response.
    """
    from ..security.encryption_utils import encrypt_request, decrypt_response
    
    # Encrypt embedding before transmission
    encrypted_req = encrypt_request(request_dict)
    
    try:
        sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((3, 5000))

        request_json = json.dumps(encrypted_req)
        request_bytes = request_json.encode('utf-8')
        sock.sendall(struct.pack('>I', len(request_bytes)))
        sock.sendall(request_bytes)

        raw_msglen = recvall(sock, 4)
        if not raw_msglen:
            return {"success": False, "error": "No response"}
        msglen = struct.unpack('>I', raw_msglen)[0]
        response_bytes = recvall(sock, msglen)
        sock.close()
        
        response = json.loads(response_bytes.decode('utf-8'))
        # Decrypt response if encrypted
        decrypted = decrypt_response(response)
        return decrypted
    except Exception as e:
        logger.error(f"Enclave error: {e}")
        return {"success": False, "error": str(e)}


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


@router.post('/v1/enroll')
@router.post('/enroll')
async def enroll_person(
    request: Request,
    images: List[UploadFile] = File(...),
    name: str = Form(None),
    metadata: str = Form("{}"),
    consent: str = Form(...),
    camera_id: str = Form(None),
    voice_files: List[UploadFile] = File(None),
    gait_video: UploadFile = File(None),
    physiological_data: str = Form("{}"),
    user: dict = Depends(require_auth),
    _policy_ok: bool = Depends(require_enroll_policy)
):
    # Parse consent (FastAPI form bool conversion is unreliable for "true"/"false" strings)
    consent_bool = consent.lower() in ("true", "1", "yes", "y")
    if not consent_bool:
        raise HTTPException(status_code=400, detail="Consent required for enrollment")

    try:
        start_time = time.time()

        try:
            metadata_dict = json.loads(metadata)
            physio_dict = json.loads(physiological_data)
        except:
            metadata_dict = {}
            physio_dict = {}

        embeddings = []
        voice_embeddings = []
        person_id = str(uuid.uuid4())
        consent_record = {"consent_record_id": str(uuid.uuid4()), "consent": consent_bool, "timestamp": time.time()}
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

        # Ethical Governor check: age and consent validation
        # Estimate jurisdiction from user or default
        user_metadata = user.get("metadata", {})
        jurisdiction = user_metadata.get("jurisdiction", "DEFAULT")
        
        ethical_decision = ethical_governor.check_request(
            request_data={
                "age": age,
                "consent": consent_bool,
                "person_id": None,  # Not yet created
                "user_id": user.get("user_id") or user.get("sub"),
                "jurisdiction": jurisdiction,
                "purpose": "enrollment"
            },
            user_role=user.get("role", "viewer"),
            jurisdiction=jurisdiction
        )
        
        if not ethical_decision.approved:
            return StandardResponse(
                success=False,
                error=f"Ethical compliance check failed: {ethical_decision.explanation}"
            )

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

        # Store embeddings securely in the enclave
        stored_embeddings = []  # for DB storage as fallback

        # Store face embeddings in the enclave
        for i, emb in enumerate(embeddings):   # embeddings is the list of face embeddings (after noise)
            enclave_request = {
                "id": str(uuid.uuid4()),
                "operation": "add_known_face_embedding",
                "embedding": emb.flatten().tolist(),
                "label": f"{name or 'unknown'}_face_{i}"
            }
            enclave_response = send_request_to_enclave(enclave_request)
            if not enclave_response.get("success", False):
                logger.warning(f"Failed to store face embedding {i} in enclave: {enclave_response.get('error')}")
                # Fallback to storing in database
                stored_embeddings.append(emb)
            else:
                logger.info(f"Stored face embedding {i} in enclave: {enclave_response.get('result')}")
                stored_embeddings.append(emb)

        # Store voice embeddings in the enclave
        for i, emb in enumerate(voice_embeddings):   # voice_embeddings is the list of voice embeddings (after noise)
            enclave_request = {
                "id": str(uuid.uuid4()),
                "operation": "add_known_voice_embedding",
                "embedding": emb.flatten().tolist(),
                "label": f"{name or 'unknown'}_voice_{i}"
            }
            enclave_response = send_request_to_enclave(enclave_request)
            if not enclave_response.get("success", False):
                logger.warning(f"Failed to store voice embedding {i} in enclave: {enclave_response.get('error')}")
                # Fallback to storing in database
                stored_embeddings.append(emb)
            else:
                logger.info(f"Stored voice embedding {i} in enclave: {enclave_response.get('result')}")
                stored_embeddings.append(emb)

        # Note: We are not storing gait in the enclave because we don't have the operation yet.
        # But we still want to store gait in the DB, so we add gait_embedding to stored_embeddings if present.
        if gait_embedding is not None:
            stored_embeddings.append(gait_embedding)

        db = await get_db()
        await db.enroll_person(person_id, name, stored_embeddings, consent_record, camera_id, voice_embeddings, gait_embedding, age, gender)

        enroll_count.inc()
        enroll_latency.observe(time.time() - start_time)

        return StandardResponse(
            success=True,
            data={
                "person_id": person_id,
                "num_embeddings": len(stored_embeddings),
                "message": f"Successfully enrolled {name or 'unknown person'}"
            },
            error=None
        )
    except Exception as e:
        logger.error(f"Enrollment error: {e}", exc_info=True)
        return StandardResponse(success=False, error=str(e))