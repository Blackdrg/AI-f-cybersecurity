import grpc
from concurrent import futures
import asyncio
from .face_recognition_pb2_grpc import FaceRecognitionServiceServicer, add_FaceRecognitionServiceServicer_to_server
from .face_recognition_pb2 import *
from ..db.db_client import get_db
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..security import require_auth_grpc
import json
import cv2
import numpy as np
import time
import tempfile
import os


class FaceRecognitionServicer(FaceRecognitionServiceServicer):
    def __init__(self):
        self.detector = FaceDetector()
        self.embedder = FaceEmbedder()

    @require_auth_grpc
    async def Enroll(self, request, context):
        # Convert request to dict for processing
        enroll_data = {
            'name': request.name,
            'images': [img for img in request.images],
            'consent': request.consent,
            'camera_id': request.camera_id,
            'voice_files': [vf for vf in request.voice_files],
            'gait_video': request.gait_video,
            'physiological_data': request.physiological_data,
            'metadata': request.metadata
        }

        # Process images
        embeddings = []
        for img_data in request.images:
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            faces = self.detector.detect_faces(
                img, check_spoof=False, reconstruct=True)
            if faces:
                face = faces[0]
                aligned = self.detector.align_face(img, face['landmarks'])
                emb = self.embedder.get_embedding(aligned)
                embeddings.append(emb)

        if not embeddings:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("No valid faces found")
            return EnrollResponse()

        person_id = str(uuid.uuid4())
        consent_record = {
            'consent_record_id': str(uuid.uuid4()),
            'client_id': context.user.get('user_id'),
            'consent_text_version': 'v1',
            'captured_ip': context.client_host,
            'signed_token': None
        }

        db = await get_db()
        await db.enroll_person(person_id, request.name, embeddings, consent_record, request.camera_id)

        return EnrollResponse(person_id=person_id, num_embeddings=len(embeddings), message="Enrollment successful")

    @require_auth_grpc
    async def Recognize(self, request, context):
        nparr = np.frombuffer(request.image, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        faces = self.detector.detect_faces(
            img, check_spoof=request.enable_spoof_check, reconstruct=True)
        detected_faces = []

        db = await get_db()

        for face in faces:
            if request.enable_spoof_check and face['spoof_score'] > 0.5:
                continue

            aligned = self.detector.align_face(img, face['landmarks'])
            query_emb = self.embedder.get_embedding(aligned)

            matches = await db.recognize_faces(query_emb, top_k=request.top_k, threshold=request.threshold, camera_id=request.camera_id)

            face_matches = [
                FaceMatch(person_id=m['person_id'], name=m['name'],
                          score=m['score'], distance=m['distance'])
                for m in matches
            ]

            is_unknown = len(face_matches) == 0

            detected_faces.append(DetectedFace(
                face_box=face['bbox'],
                matches=face_matches,
                inference_ms=0.0,  # Placeholder
                is_unknown=is_unknown,
                spoof_score=face['spoof_score'] if request.enable_spoof_check else None
            ))

        return RecognizeResponse(faces=detected_faces)

    @require_auth_grpc
    async def GetPerson(self, request, context):
        db = await get_db()
        person = await db.get_person(request.person_id)
        if not person:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Person not found")
            return PersonResponse()

        consent_record = ConsentRecord(
            consent_record_id=person['consent_record']['consent_record_id'],
            timestamp=person['consent_record']['timestamp'],
            client_id=person['consent_record']['client_id'],
            consent_text_version=person['consent_record']['consent_text_version'],
            captured_ip=person['consent_record']['captured_ip'],
            signed_token=person['consent_record']['signed_token']
        )

        return PersonResponse(
            person_id=person['person_id'],
            name=person['name'],
            embeddings=person['embeddings'],
            consent_record=consent_record
        )

    @require_auth_grpc
    async def DeletePerson(self, request, context):
        db = await get_db()
        deleted = await db.delete_person(request.person_id)
        if not deleted:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Person not found")
            return DeleteResponse(deleted=False, message="Person not found")

        return DeleteResponse(deleted=True, message="Person deleted")

    @require_auth_grpc
    async def GetAuditLogs(self, request, context):
        db = await get_db()
        # Placeholder: implement audit log retrieval
        logs = []  # Fetch from DB
        audit_logs = [AuditLogEntry(id=log['id'], action=log['action'], person_id=log['person_id'],
                                    timestamp=log['timestamp'], details=log['details']) for log in logs]
        return AuditLogsResponse(logs=audit_logs)


async def serve_grpc():
    server = grpc.aio.server()
    add_FaceRecognitionServiceServicer_to_server(
        FaceRecognitionServicer(), server)
    server.add_insecure_port('[::]:50051')
    await server.start()
    print("gRPC server started on port 50051")
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve_grpc())
